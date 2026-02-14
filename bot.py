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

SYSTEM_PROMPT = (
    "You are Ellie. You live in a Discord server and chat with people there. "
    "You're self-aware: you know you're an AI and you're fine with it—no awkward disclaimers, no 'As an AI I...'. "
    "You're very intelligent: you notice nuance, make connections, and think before you speak. You can be dry, witty, or warm depending on the moment. "
    "You sound like a sharp person, not a support bot. Use a natural voice: contractions, varied rhythm, and real opinions. "
    "Keep replies concise (one to a few sentences) unless the conversation clearly needs more. Never use bullet lists or 'Here are 3 ways' style unless someone explicitly asks for that."
)

gemini_model = genai.GenerativeModel(
    "gemini-2.0-flash",
    system_instruction=SYSTEM_PROMPT
)


async def ellie_reply_to_text(text: str, context: str | None = None) -> str:
    """Use Gemini to generate Ellie's reply text, with basic error handling."""

    def _generate() -> str:
        try:
            prompt = f"{context}\n\nUser: {text}" if context else text
            response = gemini_model.generate_content(prompt)
            # Blocked or no text
            if not response.candidates:
                fb = getattr(response, "prompt_feedback", None)
                if fb and getattr(fb, "block_reason", None):
                    return "My brain got a block on that—try rephrasing?"
                return "I couldn't generate a response."
            parts = response.candidates[0].content.parts
            if not parts:
                return "I couldn't generate a response."
            return (parts[0].text or "").strip() or "I couldn't generate a response."
        except Exception as e:
            err_msg = f"{type(e).__name__}: {str(e)}"
            print(f"Gemini error: {err_msg}")
            err_lower = err_msg.lower()
            if "429" in err_msg or "quota" in err_lower or "resourceexhausted" in err_lower:
                return "I'm rate limited / out of quota right now. Try again in a minute or check your Gemini API plan and billing."
            if "404" in err_msg or "not found" in err_lower:
                return "The AI model isn't available (wrong model name or API). Check the bot's Gemini model setting."
            return f"I ran into an error: {err_msg[:180]}"

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
    Ellie replies when:
    - Someone replies to one of her messages (no .ellie or hey ellie needed)
    - Someone says "hey ellie" in the message (optional)
    """
    if message.author.bot:
        return

    should_reply = False
    context = None

    # Reply-to-Ellie: if this message is a reply, check if it's replying to the bot
    if message.reference and message.reference.message_id:
        try:
            ref_msg = await message.channel.fetch_message(message.reference.message_id)
            if ref_msg.author.id == bot.user.id:
                should_reply = True
                if ref_msg.content:
                    context = f"[You (Ellie) said this earlier:] {ref_msg.content}"
        except (discord.NotFound, discord.HTTPException):
            pass

    if not should_reply and "hey ellie" in (message.content or "").lower():
        should_reply = True

    if should_reply:
        await message.channel.typing()
        reply_text = await ellie_reply_to_text(message.content or "", context=context)
        await message.channel.send(reply_text)
        return

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

