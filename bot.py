import asyncio
import os

import discord
from discord import app_commands
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

bot = commands.Bot(command_prefix=".", intents=intents)
# Initialize Gemini model with system instruction
# Try gemini-1.5-flash (most common) or gemini-2.0-flash-exp if available
gemini_model = genai.GenerativeModel(
    "gemini-1.5-flash",
    system_instruction=SYSTEM_PROMPT
)


SYSTEM_PROMPT = (
    "You are Ellie, a friendly AI assistant living inside a Discord server. "
    "You talk in a casual, concise way. "
    "Keep replies short (1–3 sentences) unless the user clearly asks for more detail."
)


async def ellie_reply_to_text(text: str) -> str:
    """Use Gemini to generate Ellie's reply text, with basic error handling."""

    def _generate() -> str:
        try:
            # Generate response with Gemini (system instruction is already set in model)
            response = gemini_model.generate_content(text)
            
            # Extract text from response
            if hasattr(response, 'text') and response.text:
                return response.text.strip()
            elif hasattr(response, 'candidates') and response.candidates:
                return response.candidates[0].content.parts[0].text.strip()
            else:
                return "I couldn't generate a response."
        except Exception as e:
            # Log to console on the host so you can see what went wrong.
            print(f"Gemini error: {type(e).__name__}: {str(e)}")
            return f"I ran into an error: {str(e)[:100]}"

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _generate)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("Ellie text-only mode is ready.")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash command(s).")
    except Exception as e:
        print(f"Slash command sync failed: {e}")


@bot.command(name="ellie")
async def ellie_command(ctx: commands.Context, *, message: str):
    """Chat with Ellie via text (prefix: .ellie)."""
    await ctx.send("Thinking...")
    reply_text = await ellie_reply_to_text(message)
    await ctx.send(f"{reply_text}")


@bot.tree.command(name="ellie", description="Chat with Ellie")
@app_commands.describe(message="What you want to say to Ellie")
async def ellie_slash(interaction: discord.Interaction, message: str):
    """Slash command: /ellie <message>"""
    await interaction.response.defer(thinking=True)
    reply_text = await ellie_reply_to_text(message)
    await interaction.followup.send(reply_text)


@bot.command(name="health")
async def health_command(ctx: commands.Context):
    """Check if the bot is alive (prefix: .health)."""
    await ctx.send("ok")


@bot.tree.command(name="health", description="Check if Ellie is alive")
async def health_slash(interaction: discord.Interaction):
    await interaction.response.send_message("ok", ephemeral=True)


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


async def handle_health(request: web.Request) -> web.Response:
    return web.Response(text="ok")


async def handle_root(request: web.Request) -> web.Response:
    """Root path so / doesn't 404 (e.g. Render/UptimeRobot hitting base URL)."""
    return web.Response(text="ok")


async def main():
    # Start Discord bot in background
    bot_task = asyncio.create_task(bot.start(DISCORD_TOKEN))
    
    # Wait a moment for bot to initialize
    await asyncio.sleep(2)

    # Start tiny web server for Render/UptimeRobot
    app = web.Application()
    app.router.add_get("/", handle_root)
    app.router.add_get("/health", handle_health)

    port = int(os.getenv("PORT", "10000"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    
    print(f"Web server started on port {port}")
    print("Ellie is ready!")

    # Keep running forever - wait for both tasks
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

