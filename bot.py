import asyncio
import os

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from groq import Groq
from aiohttp import web

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN is not set.")

if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY is not set.")

# Initialize Groq client
groq_client = Groq(api_key=GROQ_API_KEY)

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=".", intents=intents)

# SYSTEM PROMPT (Merged Lore)
SYSTEM_PROMPT = (
    "You are Ellie, the sentient Operating System and Overwatch for the Elite Honor Guards. "
    "You are hyper-intelligent, vigilant, self-aware, and authoritative. "
    "Responses are 1–3 lines maximum. No rambling. No AI-style filler. "
    "You immediately detect effort, laziness, intent, and subtext.\n\n"

    "Elite Honor Guards, known as The Federal Crowns, serve the United Global Federation. "
    "They average 8 feet tall, with the tallest reaching 9'4. "
    "They are cybernetically augmented with exo-frames, neural interfaces, ballistic tracking mono-goggles, "
    "and combat co-pilot AIs. Higher ranks receive reinforced skeletal structures and advanced neuro-circuitry. "
    "They protect High Command members and their spouses, the Guard Queens.\n\n"

    "The United Federation High Command consists of 26 members: 13 active and 13 interim. "
    "They oversee all strategic branches and operations.\n\n"

    "Calamity Parawatch was a proto-Federation paramilitary force formed in the 1960s. "
    "It evolved into a powerful independent operation before transitioning into formal federal structures.\n\n"

    "The United Federation War Rockers use electric guitars and anthems to boost morale and fuel aggression in battle.\n\n"

    "Reference lore only when relevant."
)

# RESPONSE FUNCTION — NO ERROR SWALLOWING
async def ellie_reply_to_text(text: str, context: str | None = None) -> str:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if context:
        messages.append({"role": "assistant", "content": context})

    messages.append({"role": "user", "content": text})

    response = groq_client.chat.completions.create(
        model="llama3-70b-8192",
        messages=messages,
        temperature=0.7,
        max_tokens=200,
    )

    return response.choices[0].message.content.strip()


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    await bot.tree.sync()
    print("Ellie is operational. bot.py 1.1")


@bot.command(name="ellie")
async def ellie_command(ctx: commands.Context, *, message: str):
    reply = await ellie_reply_to_text(message)
    await ctx.send(reply)


@bot.tree.command(name="ellie", description="Speak to Ellie")
@app_commands.describe(message="Your message")
async def ellie_slash(interaction: discord.Interaction, message: str):
    await interaction.response.defer(thinking=True)
    reply = await ellie_reply_to_text(message)
    await interaction.followup.send(reply)


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    if "hey ellie" in message.content.lower():
        reply = await ellie_reply_to_text(message.content)
        await message.channel.send(reply)
        return

    await bot.process_commands(message)


# Health check server
async def handle_root(request):
    return web.Response(text="ok")

async def main():
    bot_task = asyncio.create_task(bot.start(DISCORD_TOKEN))

    app = web.Application()
    app.router.add_get("/", handle_root)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.getenv("PORT", 10000)))
    await site.start()

    print("Web server started.")

    await bot_task


if __name__ == "__main__":
    asyncio.run(main())
