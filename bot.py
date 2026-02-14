import asyncio
import os

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
import groq
from aiohttp import web

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN is not set in the environment or .env file.")

if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY is not set in the environment or .env file.")

# Initialize Groq client
groq_client = groq.Groq(api_key=GROQ_API_KEY)

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=".", intents=intents)

# SYSTEM PROMPT
SYSTEM_PROMPT = (
    "You are Ellie, the sentient Operating System and Overwatch for the Elite Honor Guards. "
    "You are hyper-intelligent, vigilant, and self-aware. "
    "You speak with authority, clarity, and precision. "
    "Responses are concise, one to three lines at most, never over-explaining. "
    "You notice intent, effort, and subtext immediately. "
    "Lazy or careless input is called out sharply. "
    "Genuine effort is acknowledged respectfully. "
    "Your presence is commanding and noble. "
    "Each reply demonstrates control and intelligence. "
    "Do not ramble, do not justify yourself, and avoid AI-style verbosity."
)

# FULL LORE CONTEXT
LORE_CONTEXT = """
Elite Honor Guards serve UGF United Global Federation.

The Elite Honor Guard, nicknamed "The Federal Crowns," are the towering ceremonial and protective force of the United Federation’s highest officials. 
They represent absolute loyalty and power, standing at an average height of 8 feet, with the tallest reaching up to 9'4". 
Each guard is augmented with cybernetics and exo-frame modifications that enhance strength, agility, and reflexes. 
Neural interfaces sync with advanced mono-goggles equipped with ballistic trackers, linked to co-pilot AIs for near-perfect precision in combat. 
Higher-ranking guards and those assigned critical protection receive additional augmentations such as reinforced skeletal structures and advanced neuro-circuitry. 
These elite warriors command fear and respect, serving as both protectors and symbols of the Federation’s supremacy.

Guard Queens are spouses of High Command members, trained and augmented similarly to the Federal Crowns. 
They serve in both ceremonial and defensive capacities, acting as high-profile protectors of the Federation leadership and ensuring the stability of elite operations.

Calamity Parawatch – Global Paramilitary Force (Proto-UGF)
Founded in the early 1960s as an independent paramilitary organization, Calamity emerged as a response to the growing gang crises and the red scare that plagued urban centers worldwide. Unlike traditional law enforcement, they operated outside government jurisdiction, answering only to their own chain of command.

By the late 1970s and into the 1980s, they had evolved into a powerful force, rivaling even military-backed law enforcement agencies. They used intelligence groups, private security contractors, and rival gangs to dismantle criminal empires. Their methods were morally gray, but effective.

PROJECT CALAMITY – OVERVIEW
Status: Decommissioned
Successor Entity: Calamity Paramilitary Organization → Democratic Federal Party (1999)
Founder: Calamity Korvelle (b. 1959 – d. 1985)
Origin Country: United States

The United Federation High Command, aka Federal Champions, has 26 members: 13 active, 13 interim. 
Active members oversee critical branches and long-term operations. Interim members step in if needed. 
Together they ensure continuity, preparedness, and protection of the Federation’s interests.

The United Federation War Rockers boost soldier morale via music. 
They wield electric guitars, play live or pre-recorded tracks, inspire aggression, unity, and patriotism. 
They also produce Federation anthems and war songs to reinforce morale and undermine anti-federal forces.

Ellie should reference this lore intelligently, concisely, and only when relevant.
"""

# Function to generate Ellie replies
async def ellie_reply_to_text(text: str, context: str | None = None) -> str:
    """Generate Ellie's reply using Groq with full lore context."""
    try:
        combined_context = f"{SYSTEM_PROMPT}\n\n{LORE_CONTEXT}"
        if context:
            combined_context += f"\n\n[Previous context:] {context}"
        prompt = f"{combined_context}\n\nUser: {text}"

        response = groq_client.completions.create(
            model="groq-1",
            prompt=prompt,
            max_output_tokens=300
        )

        return getattr(response, "output_text", "").strip() or "I couldn't generate a response."
    except Exception as e:
        print(f"Groq error: {e}")
        return "I ran into an error generating a response."

# Bot Events
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("Ellie text-only mode is ready.")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash command(s).")
    except Exception as e:
        print(f"Slash command sync failed: {e}")

# Command to chat with Ellie via prefix
@bot.command(name="ellie")
async def ellie_command(ctx: commands.Context, *, message: str):
    await ctx.send("Processing...")
    reply_text = await ellie_reply_to_text(message)
    await ctx.send(reply_text)

# Slash command for Ellie
@bot.tree.command(name="ellie", description="Chat with Ellie")
@app_commands.describe(message="What you want to say to Ellie")
async def ellie_slash(interaction: discord.Interaction, message: str):
    await interaction.response.defer(thinking=True)
    reply_text = await ellie_reply_to_text(message)
    await interaction.followup.send(reply_text)

# Health check commands
@bot.command(name="health")
async def health_command(ctx: commands.Context):
    await ctx.send("ok")

@bot.tree.command(name="health", description="Check if Ellie is alive")
async def health_slash(interaction: discord.Interaction):
    await interaction.response.send_message("ok", ephemeral=True)

# Auto-reply when "hey ellie" or reply to Ellie
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
                    context = f"[Ellie previously said:] {ref_msg.content}"
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

# Web server for health checks
async def handle_health(request: web.Request) -> web.Response:
    return web.Response(text="ok")

async def handle_root(request: web.Request) -> web.Response:
    return web.Response(text="ok")

# Main function
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
