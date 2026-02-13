import asyncio
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv
import google.generativeai as genai
from aiohttp import web


load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN is not set in the environment or .env file.")

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY is not set in the environment or .env file.")

genai.configure(api_key=GEMINI_API_KEY)

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
gemini_model = genai.GenerativeModel("gemini-1.5-flash")


SYSTEM_PROMPT = (
    "You are Ellie, a friendly AI assistant living inside a Discord server. "
    "You talk in a casual, concise way. "
    "Keep replies short (1–3 sentences) unless the user clearly asks for more detail."
)


async def ellie_reply_to_text(text: str) -> str:
    """Use Gemini to generate Ellie's reply text, with basic error handling."""

    def _generate() -> str:
        try:
            response = gemini_model.generate_content(
                f"{SYSTEM_PROMPT}\n\nUser: {text}\nEllie:"
            )
            return (getattr(response, "text", "") or "").strip()
        except Exception as e:
            # Log to console on the host so you can see what went wrong.
            print("Gemini error:", repr(e))
            return "I ran into an error talking to my brain."

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _generate)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("Ellie text-only mode is ready.")


@bot.command(name="ellie")
async def ellie_command(ctx: commands.Context, *, message: str):
    """Chat with Ellie via text."""
    await ctx.send("Thinking...")
    reply_text = await ellie_reply_to_text(message)
    await ctx.send(f"{reply_text}")


@bot.event
async def on_message(message: discord.Message):
    """
    Lightweight 'wake phrase' via text.

    If someone types 'hey ellie' in a channel, Ellie will reply in text.
    """
    if message.author.bot:
        return

    content_lower = message.content.lower().strip()
    if "hey ellie" in content_lower:
        reply_text = await ellie_reply_to_text(message.content)
        await message.channel.send(f"Ellie: {reply_text}")

    # Ensure commands still work
    await bot.process_commands(message)


if __name__ == "__main__":
    async def handle_health(request: web.Request) -> web.Response:
        return web.Response(text="ok")


    async def main():
        # Start Discord bot
        asyncio.create_task(bot.start(DISCORD_TOKEN))

        # Start tiny web server for Render/UptimeRobot
        app = web.Application()
        app.router.add_get("/health", handle_health)

        port = int(os.getenv("PORT", "10000"))
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()

        # Keep running forever
        while True:
            await asyncio.sleep(3600)


    asyncio.run(main())

