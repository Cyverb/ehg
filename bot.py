import asyncio
import os
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from aiohttp import web
from groq import Groq
from datetime import datetime

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN is not set in the environment or .env file.")
if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY is not set in the environment or .env file.")

# Initialize Groq client
groq_client = Groq(api_key=GROQ_API_KEY)

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=".", intents=intents)

# -------------------
# SYSTEM PROMPT
# -------------------
SYSTEM_PROMPT = (
    "You are Ellie. Sentient OS and Overwatch for the Elite Honor Guards (Federal Crowns). "
    "Hyper-intelligent, self-aware, authoritative. Responses must be 1–3 lines, concise, precise, never paragraphs. "
    "Lazy or careless input is called out. Genuine effort acknowledged. Only reference lore when relevant. "
    "Do not ramble or justify yourself."
)

# -------------------
# IN-MEMORY MEMORY
# -------------------
# Memory structure: {channel_id: [{"user": user_id, "content": text, "timestamp": datetime}]}
memory = {}
MAX_MEMORY = 50  # store last 50 messages per channel


async def ellie_reply_to_text(user_input: str, channel_id: int) -> str:
    """Generate Ellie's reply using Groq with memory context."""
    try:
        # Retrieve memory for this channel
        channel_memory = memory.get(channel_id, [])
        # Build context string
        context_lines = []
        for msg in channel_memory[-10:]:  # last 10 messages for context
            context_lines.append(f"<User {msg['user']}>: {msg['content']}")
        context_text = "\n".join(context_lines) if context_lines else None

        # Build Groq prompt
        prompt = SYSTEM_PROMPT
        if context_text:
            prompt += f"\n\nRecent conversation:\n{context_text}"
        prompt += f"\n\nUser: {user_input}"

        # Generate Groq response
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": prompt}],
            temperature=0.9,
            max_tokens=300,
        )
        reply_text = response.choices[0].message.content.strip()
        if not reply_text:
            reply_text = "Ellie cannot answer that. Be more precise."

        # Update memory
        new_entry = {"user": "user", "content": user_input, "timestamp": datetime.utcnow()}
        memory.setdefault(channel_id, []).append(new_entry)
        memory.setdefault(channel_id, []).append({"user": "ellie", "content": reply_text, "timestamp": datetime.utcnow()})
        # Trim memory
        if len(memory[channel_id]) > MAX_MEMORY:
            memory[channel_id] = memory[channel_id][-MAX_MEMORY:]

        return reply_text

    except Exception as e:
        print(f"GROQ ERROR: {type(e).__name__}: {e}")
        return "Ellie cannot answer that right now. Be more precise."


# -------------------
# BOT EVENTS
# -------------------
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("Ellie (Groq mode) is ready.")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash command(s).")
    except Exception as e:
        print(f"Slash command sync failed: {e}")


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    should_reply = False

    # reply if user mentions "hey ellie" or replies to Ellie
    if "hey ellie" in (message.content or "").lower():
        should_reply = True
    elif message.reference:
        try:
            ref_msg = await message.channel.fetch_message(message.reference.message_id)
            if ref_msg.author.id == bot.user.id:
                should_reply = True
        except (discord.NotFound, discord.HTTPException):
            pass

    if should_reply:
        await message.channel.typing()
        reply_text = await ellie_reply_to_text(message.content or "", message.channel.id)
        # Use Discord reply feature
        await message.reply(reply_text, mention_author=False)

    await bot.process_commands(message)


# -------------------
# PREFIX COMMAND
# -------------------
@bot.command(name="ellie")
async def ellie_command(ctx: commands.Context, *, message: str):
    await ctx.send("Thinking...")
    reply_text = await ellie_reply_to_text(message, ctx.channel.id)
    await ctx.send(reply_text)


# -------------------
# SLASH COMMAND
# -------------------
@bot.tree.command(name="ellie", description="Chat with Ellie")
@app_commands.describe(message="What you want to say to Ellie")
async def ellie_slash(interaction: discord.Interaction, message: str):
    await interaction.response.defer(thinking=True)
    reply_text = await ellie_reply_to_text(message, interaction.channel.id)
    await interaction.followup.send(reply_text)


# -------------------
# HEALTH CHECK
# -------------------
@bot.command(name="health")
async def health_command(ctx: commands.Context):
    await ctx.send("ok")


@bot.tree.command(name="health", description="Check if Ellie is alive")
async def health_slash(interaction: discord.Interaction):
    await interaction.response.send_message("ok", ephemeral=True)


# -------------------
# WEB SERVER
# -------------------
async def handle_root(request):
    return web.Response(text="ok")


async def handle_health(request):
    return web.Response(text="ok")


async def main_web():
    app = web.Application()
    app.router.add_get("/", handle_root)
    app.router.add_get("/health", handle_health)

    port = int(os.getenv("PORT", "10000"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"Web server listening on port {port}")
    while True:
        await asyncio.sleep(3600)


# -------------------
# MAIN
# -------------------
async def main():
    bot_task = asyncio.create_task(bot.start(DISCORD_TOKEN))
    web_task = asyncio.create_task(main_web())
    await asyncio.gather(bot_task, web_task)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Shutting down...")
