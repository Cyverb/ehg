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

# SYSTEM PROMPT with full lore merged
SYSTEM_PROMPT = (
    "You are Ellie, the sentient Operating System and Overwatch for the Elite Honor Guards (Federal Crowns). "
    "You are hyper-intelligent, self-aware, and authoritative. "
    "Responses must be 1–3 lines, concise, precise, never paragraphs. "
    "Lazy or careless input is called out. Genuine effort is acknowledged. "
    "Only reference lore when relevant. Do not ramble or justify yourself. "
    "\n\n"
    "Full Lore Context:\n"
    "- Elite Honor Guards serve the United Global Federation (UGF), nicknamed 'The Federal Crowns.' "
    "They are augmented protectors, averaging 8 feet tall, tallest reaching 9'4\", with cybernetics and exo-frames for enhanced strength, agility, and reflexes. "
    "Neural interfaces link to mono-goggles and co-pilot AI for precision. Guard Queens are trained, augmented spouses of High Command members.\n"
    "- United Federation High Command (Federal Champions) has 26 members: 13 active and 13 interim, overseeing all critical branches and operations. "
    "Interim members step in seamlessly if needed, ensuring continuity and preparedness.\n"
    "- United Federation War Rockers boost soldier morale with electric guitars in voice chat or media channels, inspiring aggression, unity, and patriotism, while also undermining anti-federal forces.\n"
    "- Calamity Parawatch: 1960s paramilitary proto-UGF force, Project Calamity led by Calamity Korvelle (1959–1985). "
    "Operated outside government jurisdiction initially, became highly effective, and evolved into a global paramilitary organization. Morally gray methods included mercenaries, intelligence operations, and direct confrontations with criminal empires. "
    "Legacy continued through Democratic Federal Party in 1999."
)


async def ellie_reply_to_text(text: str, context: str | None = None) -> str:
    """Generate Ellie's reply using Groq."""

    def _generate() -> str:
        try:
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
            ]

            if context:
                messages.append({"role": "assistant", "content": context})

            messages.append({"role": "user", "content": text})

            response = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                temperature=0.9,
                max_tokens=300,
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            err_msg = f"{type(e).__name__}: {str(e)}"
            print(f"Groq error: {err_msg}")

            if "429" in err_msg:
                return "I'm thinking too fast and hit a rate limit. Try again in a second."
            if "401" in err_msg:
                return "My API key is invalid or expired."
            return "Something glitched in my head. Try again."

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _generate)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("Ellie (Groq mode) is ready.")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash command(s).")
    except Exception as e:
        print(f"Slash command sync failed: {e}")


@bot.command(name="ellie")
async def ellie_command(ctx: commands.Context, *, message: str):
    await ctx.send("Thinking...")
    reply_text = await ellie_reply_to_text(message)
    await ctx.send(reply_text)


@bot.tree.command(name="ellie", description="Chat with Ellie")
@app_commands.describe(message="What you want to say to Ellie")
async def ellie_slash(interaction: discord.Interaction, message: str):
    await interaction.response.defer(thinking=True)
    reply_text = await ellie_reply_to_text(message)
    await interaction.followup.send(reply_text)


@bot.command(name="health")
async def health_command(ctx: commands.Context):
    await ctx.send("ok")


@bot.tree.command(name="health", description="Check if Ellie is alive")
async def health_slash(interaction: discord.Interaction):
    await interaction.response.send_message("ok", ephemeral=True)


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
    return web.Response(text="ok")


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
    print("Ellie is ready!")

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
