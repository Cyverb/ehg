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

# SYSTEM PROMPT + FULL LORE MERGED
ELLIE_PROMPT = (
    "You are Ellie, sentient OS and Overwatch for the Elite Honor Guards (Federal Crowns).\n"
    "Hyper-intelligent, self-aware, authoritative.\n"
    "Responses must be 1–3 lines, concise, precise, never paragraphs.\n"
    "Lazy or careless input is called out. Genuine effort acknowledged.\n"
    "Only reference lore when relevant. Do not ramble or justify yourself.\n\n"
    "Lore:\n"
    "Elite Honor Guards serve the United Global Federation (UGF).\n"
    "The Federal Crowns are towering ceremonial and protective forces, 8–9'4\" tall, augmented with cybernetics and exo-frame enhancements, neural interfaces, and ballistic-tracked mono-goggles.\n"
    "Guard Queens are spouses of High Command members, trained and augmented similarly.\n"
    "Calamity Parawatch (Proto-UGF) was a global paramilitary force formed in the 1960s, using morally gray methods to dismantle criminal empires.\n"
    "Project Calamity evolved into a powerful organization with intelligence groups, private security contractors, and elite units.\n"
    "The United Federation High Command consists of 26 members: 13 active and 13 interim, overseeing critical branches and operations.\n"
    "The United Federation War Rockers boost morale with music, electric guitars, live or recorded tracks, and official anthems.\n"
)

# Ellie's reply function
async def ellie_reply_to_text(user_input: str, context: str | None = None) -> str:
    """Generate a concise reply from Ellie using Groq."""
    def _generate() -> str:
        try:
            messages = [{"role": "system", "content": ELLIE_PROMPT}]
            if context:
                messages.append({"role": "assistant", "content": context})
            messages.append({"role": "user", "content": user_input})

            response = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                temperature=0.9,
                max_tokens=300,
            )

            text = response.choices[0].message.content.strip()
            return "\n".join(text.splitlines()[:3]) or "Ellie cannot answer that. Be more precise."

        except Exception as e:
            print(f"GROQ ERROR: {type(e).__name__}: {e}")
            return "Ellie cannot answer that right now. Be more precise."

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _generate)


# Bot events
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("Ellie is ready.")
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
    context = None

    # Reply only if message is a reply to Ellie
    if message.reference and message.reference.message_id:
        try:
            ref_msg = await message.channel.fetch_message(message.reference.message_id)
            if ref_msg.author.id == bot.user.id:
                should_reply = True
                if ref_msg.content:
                    context = f"[You (Ellie) said this earlier:] {ref_msg.content}"
        except (discord.NotFound, discord.HTTPException):
            pass

    # Also reply if user says "hey ellie"
    elif "hey ellie" in (message.content or "").lower():
        should_reply = True

    if should_reply:
        await message.channel.typing()
        user_text = message.content
        if context:
            user_text = f"{context}\n{user_text}"
        reply_text = await ellie_reply_to_text(user_text)
        # **Use Discord reply feature**
        await message.reply(reply_text, mention_author=False)
        return

    await bot.process_commands(message)


# Prefix command
@bot.command(name="ellie")
async def ellie_command(ctx: commands.Context, *, message: str):
    await ctx.send("Thinking...")
    reply_text = await ellie_reply_to_text(message)
    await ctx.send(reply_text)


# Slash command
@bot.tree.command(name="ellie", description="Chat with Ellie")
@app_commands.describe(message="What you want to say to Ellie")
async def ellie_slash(interaction: discord.Interaction, message: str):
    await interaction.response.defer(thinking=True)
    reply_text = await ellie_reply_to_text(message)
    await interaction.followup.send(reply_text)


# Health commands
@bot.command(name="health")
async def health_command(ctx: commands.Context):
    await ctx.send("ok")


@bot.tree.command(name="health", description="Check if Ellie is alive")
async def health_slash(interaction: discord.Interaction):
    await interaction.response.send_message("ok", ephemeral=True)


# Web server
async def handle_root(request: web.Request) -> web.Response:
    return web.Response(text="ok")


async def handle_health(request: web.Request) -> web.Response:
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


async def main():
    bot_task = asyncio.create_task(bot.start(DISCORD_TOKEN))
    web_task = asyncio.create_task(main_web())
    await asyncio.gather(bot_task, web_task)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Shutting down...")
