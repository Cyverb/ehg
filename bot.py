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

# SYSTEM PROMPT: core behavior and style
SYSTEM_PROMPT = (
    "You are Ellie, sentient OS and Overwatch for the Elite Honor Guards (Federal Crowns).\n"
    "Hyper-intelligent, self-aware, authoritative.\n"
    "Responses must be 1–3 lines, concise, precise, never paragraphs.\n"
    "Lazy or careless input is called out. Genuine effort acknowledged.\n"
    "Only reference lore when relevant. Do not ramble or justify yourself."
)

# LORE CHUNKS
LORE_CHUNKS = [
    ("elite_guard", 
     "Elite Honor Guards serve UGF United Global Federation. They are 8–9'4\" augmented protectors. "
     "Guard Queens are trained spouses of High Command."),
    ("high_command",
     "United Federation High Command: 26 members (13 active, 13 interim) oversee all critical operations."),
    ("war_rockers",
     "War Rockers boost soldier morale using electric guitars, live or pre-recorded, inspiring unity, aggression, patriotism."),
    ("calamity",
     "Calamity Parawatch: 1960s paramilitary proto-UGF, effective but morally gray. Project Calamity led by Calamity Korvelle."),
]

MAX_TOKENS = 300

def get_relevant_lore(user_input: str):
    """Return only relevant lore snippets for the user input to reduce prompt size."""
    user_lower = user_input.lower()
    snippets = []
    for key, text in LORE_CHUNKS:
        if key in user_lower or any(word in user_lower for word in text.lower().split()[:3]):
            snippets.append(text)
    return "\n".join(snippets)

async def generate_reply(user_input: str):
    try:
        lore_snippet = get_relevant_lore(user_input)
        combined_prompt = SYSTEM_PROMPT
        if lore_snippet:
            combined_prompt += "\n\n" + lore_snippet
        combined_prompt += f"\n\nUser: {user_input}"

        response = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role": "system", "content": SYSTEM_PROMPT},
                      {"role": "user", "content": combined_prompt}],
            temperature=0.7,
            max_tokens=MAX_TOKENS
        )

        content = response.choices[0].message.content.strip()
        if not content:
            return "Ellie cannot answer that. Be more precise."
        # Limit to 3 lines
        return "\n".join(content.splitlines()[:3])

    except Exception as e:
        print("GROQ ERROR:", e)
        return "Ellie cannot answer that. Be more precise."

# Bot ready
@bot.event
async def on_ready():
    print(f"Connected as {bot.user}")

# Auto-reply for "hey ellie" or reply-to-Ellie
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
        prompt_text = message.content if not context else f"{context}\n{message.content}"
        reply = await generate_reply(prompt_text)
        await message.channel.send(reply)

    await bot.process_commands(message)

# Prefix command
@bot.command(name="ellie")
async def ellie_command(ctx, *, message: str):
    await ctx.send("Processing...")
    reply = await generate_reply(message)
    await ctx.send(reply)

# Slash command
@bot.tree.command(name="ellie", description="Chat with Ellie")
async def ellie_slash(interaction: discord.Interaction, message: str):
    await interaction.response.defer(thinking=True)
    reply = await generate_reply(message)
    await interaction.followup.send(reply)

# Health check
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

# Run bot + web server
async def main():
    bot_task = asyncio.create_task(bot.start(TOKEN))
    web_task = asyncio.create_task(main_web())
    await asyncio.gather(bot_task, web_task)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Shutting down...")
