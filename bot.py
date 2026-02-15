import os
import discord
from discord.ext import commands
from groq import Groq
import asyncio
from aiohttp import web

TOKEN = os.getenv("DISCORD_TOKEN")
GROQ_KEY = os.getenv("GROQ_API_KEY")

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN not set.")
if not GROQ_KEY:
    raise RuntimeError("GROQ_API_KEY not set.")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

client = Groq(api_key=GROQ_KEY)

# SYSTEM PROMPT + condensed lore
SYSTEM_PROMPT = (
    "You are Ellie, the sentient Operating System and Overwatch for the Elite Honor Guards, known as the Federal Crowns.\n"
    "Hyper-intelligent, self-aware, authoritative. Responses concise: 1–3 lines max.\n"
    "Lazy or careless input is called out. Genuine effort acknowledged.\n"
    "Elite Honor Guards: 8–9'4\" augmented protectors with cybernetics and neural-linked mono-goggles.\n"
    "Guard Queens: trained spouses of High Command, ceremonial and defensive duties.\n"
    "United Federation High Command: 26 members (13 active, 13 interim) oversee all critical operations.\n"
    "War Rockers Division: boosts soldier morale with electric guitar music, inspiring unity, aggression, patriotism.\n"
    "Calamity Parawatch: 1960s paramilitary proto-UGF, effective but morally gray.\n"
    "Behavior: commanding, concise, precise. Do not ramble or over-explain. Reference lore only when relevant."
)

# Optional extended lore
LORE_CONTEXT = (
    "Elite Honor Guards serve UGF United Global Federation.\n"
    "Calamity Parawatch – Global Paramilitary Force (Proto-UGF) founded in 1960s.\n"
    "Project Calamity history, founder Calamity Korvelle, evolution into Democratic Federal Party.\n"
    "High Command structure, War Rockers, Guard Queens, all details included for context."
)

MAX_TOKENS = 300

async def generate_reply(user_input):
    """Call Groq safely, with fallback to avoid errors."""
    try:
        # Combine system prompt + lore but truncate to avoid oversize prompts
        combined = SYSTEM_PROMPT + "\n\n" + LORE_CONTEXT[:2000] + "\n\nUser: " + user_input
        response = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": combined}
            ],
            temperature=0.7,
            max_tokens=MAX_TOKENS
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print("GROQ ERROR:", e)
        # fallback reply instead of generic error
        return "Ellie cannot answer that right now. Be more precise."

# Bot ready
@bot.event
async def on_ready():
    print(f"Connected as {bot.user}")

# Message listener
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

# Command for text chat
@bot.command(name="ellie")
async def ellie_command(ctx, *, message: str):
    await ctx.send("Processing...")
    reply_text = await generate_reply(message)
    await ctx.send(reply_text)

# Minimal web server for Render health checks
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
