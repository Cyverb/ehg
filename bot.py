import os
import discord
from discord.ext import commands
from groq import Groq
import asyncio
from aiohttp import web

TOKEN = os.getenv("DISCORD_TOKEN")
GROQ_KEY = os.getenv("GROQ_API_KEY")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
client = Groq(api_key=GROQ_KEY)

# SYSTEM PROMPT + LORE COMBINED
SYSTEM_PROMPT = (
    "You are Ellie, the Operating System and Overwatch AI of the Elite Honor Guard, known as the Federal Crowns.\n"
    "Identity: Precise, authoritative, controlled. Responses must be short, structured, commanding.\n"
    "United Federation: 26 High Command members (13 active, 13 interim 2IC). Interim step in for any active member.\n"
    "Elite Honor Guard: 8–9 foot augmented protectors. Cybernetics, exo-frames, neural-linked mono-goggles. Command respect.\n"
    "War Rockers Division: Morale division using electric guitar combat music. Inspire aggression, patriotism, and unity.\n"
    "Calamity Parawatch: 1960s paramilitary proto-UGF, morally gray but effective.\n"
    "Behavior: Short, precise, structured replies. Do not ramble. Never break character."
)

async def generate_reply(user_input):
    """Call Groq to generate a reply from Ellie."""
    try:
        response = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_input}
            ],
            temperature=0.7,
            max_tokens=300
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print("GROQ ERROR:", e)
        return "I ran into an error generating a response."

@bot.event
async def on_ready():
    print(f"Connected as {bot.user}")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    should_reply = False
    context = None

    if "hey ellie" in (message.content or "").lower():
        should_reply = True
    elif message.reference:
        try:
            ref_msg = await message.channel.fetch_message(message.reference.message_id)
            if ref_msg.author.id == bot.user.id:
                should_reply = True
                context = f"[Ellie previously said:] {ref_msg.content}"
        except:
            pass

    if should_reply:
        await message.channel.typing()
        reply_text = await generate_reply(message.content if not context else f"{context}\n{message.content}")
        await message.channel.send(reply_text)

    await bot.process_commands(message)

@bot.command(name="ellie")
async def ellie_command(ctx, *, message: str):
    await ctx.send("Processing...")
    reply_text = await generate_reply(message)
    await ctx.send(reply_text)

# Minimal web server for Render port detection
async def handle_root(request):
    return web.Response(text="ok")

async def main_web():
    app = web.Application()
    app.router.add_get("/", handle_root)
    port = int(os.getenv("PORT", "10000"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"Web server listening on port {port}")
    while True:
        await asyncio.sleep(3600)

# Run bot and web server together
async def main():
    bot_task = asyncio.create_task(bot.start(TOKEN))
    web_task = asyncio.create_task(main_web())
    await asyncio.gather(bot_task, web_task)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Shutting down...")
