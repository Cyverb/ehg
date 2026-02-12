import asyncio
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv
from gtts import gTTS
import google.generativeai as genai


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
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)
gemini_model = genai.GenerativeModel("gemini-1.5-flash")


SYSTEM_PROMPT = (
    "You are Ellie, a friendly AI assistant living inside a Discord server. "
    "You talk in a casual, concise way, suitable for voice chat. "
    "Keep replies short (1–2 sentences) unless the user clearly asks for more detail."
)


async def ensure_connected_to_voice(ctx: commands.Context) -> discord.VoiceClient | None:
    """Join the command author's voice channel if not already connected."""
    if ctx.author.voice is None or ctx.author.voice.channel is None:
        await ctx.send("You need to be in a voice channel first so I know where to join.")
        return None

    if ctx.voice_client is not None and ctx.voice_client.is_connected():
        return ctx.voice_client

    voice_channel = ctx.author.voice.channel
    vc = await voice_channel.connect()
    await ctx.send(f"Joined voice channel: {voice_channel.name}")
    return vc


async def ellie_reply_to_text(text: str) -> str:
    """Use Gemini to generate Ellie's reply text."""
    # Gemini API is synchronous; run it in a thread to avoid blocking the event loop.
    def _generate() -> str:
        response = gemini_model.generate_content(
            [
                {"role": "user", "parts": [SYSTEM_PROMPT]},
                {"role": "user", "parts": [text]},
            ]
        )
        return (response.text or "").strip()

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _generate)


async def synthesize_speech_to_file(text: str, output_path: str) -> None:
    """
    Use gTTS (Google Translate TTS) to synthesize speech and write it to an audio file.

    This does not require a separate API key and is simple to use.
    """
    def _synthesize():
        tts = gTTS(text=text, lang="en")
        tts.save(output_path)

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _synthesize)


async def play_audio_in_voice(vc: discord.VoiceClient, file_path: str) -> None:
    """Play an audio file into the connected voice channel."""
    if not vc.is_connected():
        return

    if vc.is_playing():
        vc.stop()

    # FFmpeg must be installed and on PATH.
    audio_source = discord.FFmpegPCMAudio(file_path)
    vc.play(audio_source)

    # Wait until playback finishes.
    while vc.is_playing():
        await asyncio.sleep(0.2)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("EllieVC is ready.")


@bot.command(name="join")
async def join(ctx: commands.Context):
    """Tell Ellie to join your voice channel."""
    await ensure_connected_to_voice(ctx)


@bot.command(name="leave")
async def leave(ctx: commands.Context):
    """Tell Ellie to leave the current voice channel."""
    if ctx.voice_client is not None and ctx.voice_client.is_connected():
        channel_name = ctx.voice_client.channel.name
        await ctx.voice_client.disconnect()
        await ctx.send(f"Left voice channel: {channel_name}")
    else:
        await ctx.send("I'm not in a voice channel right now.")


@bot.command(name="ellie")
async def ellie_command(ctx: commands.Context, *, message: str):
    """
    Text-triggered conversation with Ellie that responds in voice chat.

    Example:
      !ellie hey ellie, how are you?
    """
    vc = await ensure_connected_to_voice(ctx)
    if vc is None:
        return

    await ctx.send("Thinking...")
    reply_text = await ellie_reply_to_text(message)

    # Send reply into text chat as well (optional)
    await ctx.send(f"Ellie: {reply_text}")

    # Synthesize and play voice response
    temp_file = "ellie_reply.mp3"
    await synthesize_speech_to_file(reply_text, temp_file)
    await play_audio_in_voice(vc, temp_file)


@bot.event
async def on_message(message: discord.Message):
    """
    Lightweight 'wake phrase' via text.

    If someone types 'hey ellie' in a channel, Ellie will reply in voice chat.
    """
    if message.author.bot:
        return

    content_lower = message.content.lower().strip()
    if "hey ellie" in content_lower:
        ctx = await bot.get_context(message)

        # Reuse the core conversation flow.
        vc = await ensure_connected_to_voice(ctx)
        if vc is not None:
            reply_text = await ellie_reply_to_text(message.content)
            await message.channel.send(f"Ellie: {reply_text}")

            temp_file = "ellie_reply.mp3"
            await synthesize_speech_to_file(reply_text, temp_file)
            await play_audio_in_voice(vc, temp_file)

    # Ensure commands still work
    await bot.process_commands(message)


if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)

