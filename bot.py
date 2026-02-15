import asyncio
import os

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from aiohttp import web
from groq import Groq

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

# -------------------------------
# SYSTEM PROMPT + MEMORY
# -------------------------------
SYSTEM_PROMPT = (
    "You are Ellie, the sentient Operating System and Overwatch for the Elite Honor Guards. "
    "You are hyper-intelligent, vigilant, and self-aware. "
    "Responses are concise, one to three lines at most, never over-explaining. "
    "You notice intent, effort, and subtext immediately. "
    "Lazy or careless input is called out sharply. "
    "Genuine effort is acknowledged respectfully. "
    "Your presence is commanding and noble. "
    "Each reply demonstrates control and intelligence. "
    "Do not ramble, do not justify yourself, and avoid AI-style verbosity."
)

# Shared memory for Ellie (global)
shared_memory = []

# -------------------------------
# ELLIE REPLY FUNCTION
# -------------------------------
async def ellie_reply_to_text(user_input: str) -> str:
    """Generate Ellie's reply using Groq with unlimited memory."""
    # Combine all previous messages (unlimited)
    context_text = "\n".join(shared_memory)
    prompt = f"{SYSTEM_PROMPT}\n\nMemory:\n{context_text}\n\nUser: {user_input}"

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": prompt}],
            temperature=0.9,
            max_tokens=300,
        )
        reply = response.choices[0].message.content.strip()
        if reply:
            # Save to memory
            shared_memory.append(f"User: {user_input}")
            shared_memory.append(f"Ellie: {reply}")
            return reply
        return "Ellie cannot answer that. Be more precise."
    except Exception as e:
        print(f"GROQ ERROR: {type(e).__name__}: {e}")
        return "Ellie cannot answer that right now. Be more precise."

# -------------------------------
# BOT EVENTS
# -------------------------------
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("Ellie is ready and remembering everything.")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash command(s).")
    except Exception as e:
        print(f"Slash command sync failed: {e}")

# -------------------------------
# REPLY WHEN MENTIONED OR "HEY ELLIE"
# -------------------------------
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    should_reply = False
    context = None

    if message.reference and message.reference.message_id:
        try:
            ref_msg = await message.channel.fetch_message(message.reference.message_id)
            if ref_msg.author.id == bot.user.id:
                should_reply = True
                if ref_msg.content:
                    context = f"[Ellie previously said:] {ref_msg.content}"
        except (discord.NotFound, discord.HTTPException):
            pass

    if not should_reply and "hey ellie" in (message.content or "").lower():
        should_reply = True

    if should_reply:
        await message.channel.typing()
        text_to_use = message.content if not context else f"{context}\n{message.content}"
        reply_text = await ellie_reply_to_text(text_to_use)
        # Reply as a Discord reply
        await message.reply(reply_text)
        return

    await bot.process_commands(message)

# -------------------------------
# PREFIX COMMANDS
# -------------------------------
@bot.command(name="ellie")
async def ellie_command(ctx: commands.Context, *, message: str):
    await ctx.send("Thinking...")
    reply_text = await ellie_reply_to_text(message)
    await ctx.send(reply_text)

@bot.command(name="health")
async def health_command(ctx: commands.Context):
    await ctx.send("ok")

# -------------------------------
# SLASH COMMANDS
# -------------------------------
@bot.tree.command(name="ellie", description="Chat with Ellie")
@app_commands.describe(message="What you want to say to Ellie")
async def ellie_slash(interaction: discord.Interaction, message: str):
    await interaction.response.defer(thinking=True)
    reply_text = await ellie_reply_to_text(message)
    await interaction.followup.send(reply_text)

@bot.tree.command(name="health", description="Check if Ellie is alive")
async def health_slash(interaction: discord.Interaction):
    await interaction.response.send_message("ok", ephemeral=True)

# -------------------------------
# WEB SERVER FOR HEALTH CHECKS
# -------------------------------
async def handle_root(request: web.Request) -> web.Response:
    return web.Response(text="ok")

async def handle_health(request: web.Request) -> web.Response:
    return web.Response(text="ok")

# -------------------------------
# MAIN FUNCTION
# -------------------------------
async def main():
    bot_task = asyncio.create_task(bot.start(DISCORD_TOKEN))
    await asyncio.sleep(2)

    app = web.Application()
    app.router.add_get("/", handle_root)
    app.router.add_get("/health", handle_health)
    port = int(os.getenv("PORT", "10000"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    print(f"Web server started on port {port}")
    print("Ellie is fully operational!")

    try:
        await bot_task
    except Exception as e:
        print(f"Bot error: {e}")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Shutting down...")
