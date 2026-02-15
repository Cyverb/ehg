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

SYSTEM_PROMPT = (
    "You are Ellie, sentient OS and Overwatch for the Elite Honor Guards (Federal Crowns).\n"
    "Hyper-intelligent, self-aware, authoritative.\n"
    "Responses must be 1–3 lines, concise, precise, never paragraphs.\n"
    "Lazy or careless input is called out. Genuine effort acknowledged.\n"
    "Only reference lore when relevant. Do not ramble or justify yourself."
)

# Very short, essential lore snippets
LORE_SNIPPETS = {
    "elite": "Elite Honor Guards serve UGF. 8–9'4\" augmented protectors. Guard Queens are trained spouses of High Command.",
    "high command": "United Federation High Command: 26 members oversee all critical operations.",
    "war rockers": "War Rockers boost soldier morale with electric guitars, inspire aggression, unity, and patriotism.",
    "calamity": "Calamity Parawatch: 1960s paramilitary proto-UGF. Project Calamity led by Calamity Korvelle."
}

async def generate_reply(user_input: str):
    # Keep lore small: attach only the snippet that matches keywords
    user_lower = user_input.lower()
    lore = ""
    for key, snippet in LORE_SNIPPETS.items():
        if key in user_lower:
            lore = snippet
            break

    prompt = SYSTEM_PROMPT
    if lore:
        prompt += "\n\n" + lore
    prompt += f"\n\nUser: {user_input}"

    try:
        response = client.generate_text(
            model="groq-1",
            prompt=prompt,
            max_output_tokens=200
        )
        text = getattr(response, "text", "").strip()
        if not text:
            return "Ellie cannot answer that. Be more precise."
        return "\n".join(text.splitlines()[:3])  # Limit to 3 lines
    except Exception as e:
        print("GROQ ERROR:", e)
        return "Ellie cannot answer that right now. Be more precise."

# Bot events
@bot.event
async def on_ready():
    print(f"Connected as {bot.user}")

@bot.event
async def on_message(message: discord.Message):
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
        text = message.content if not context else f"{context}\n{message.content}"
        reply = await generate_reply(text)
        await message.channel.send(reply)

    await bot.process_commands(message)

@bot.command(name="ellie")
async def ellie_command(ctx, *, message: str):
    await ctx.send("Processing...")
    reply = await generate_reply(message)
    await ctx.send(reply)

@bot.tree.command(name="ellie", description="Chat with Ellie")
async def ellie_slash(interaction: discord.Interaction, message: str):
    await interaction.response.defer(thinking=True)
    reply = await generate_reply(message)
    await interaction.followup.send(reply)

# Web server
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

async def main():
    bot_task = asyncio.create_task(bot.start(TOKEN))
    web_task = asyncio.create_task(main_web())
    await asyncio.gather(bot_task, web_task)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Shutting down...")
