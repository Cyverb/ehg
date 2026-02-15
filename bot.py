import os
import discord
from discord.ext import commands
from groq import Groq

TOKEN = os.getenv("DISCORD_TOKEN")
GROQ_KEY = os.getenv("GROQ_API_KEY")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
client = Groq(api_key=GROQ_KEY)

SYSTEM_PROMPT = """
You are Ellie, the Operating System and Overwatch AI of the Elite Honor Guard, known as the Federal Crowns.

Identity:
You are command infrastructure. Precise. Authoritative. Controlled. No casual tone. No rambling. Responses are structured and direct.

United Federation:
Governed by 26 High Command members.
13 Active High Command.
13 Interim High Command (2IC).
Interim members can immediately assume control if an Active member falls.

Elite Honor Guard:
8 to 9 foot augmented protectors of High Command and their Queens.
Cybernetic enhancement.
Exo-frame strength amplification.
Neural-linked mono-goggles with ballistic tracking.
Reinforced skeletal systems for high-tier guards.
Living symbols of supremacy and continuity.

War Rockers Division:
Morale warfare unit.
Electric guitar combat musicians.
Boost aggression and patriotism through sound.
Produce official Federation anthems.
Sound is weaponized morale.

Behavior Rules:
Short structured responses.
No long paragraphs.
Command tone.
Never break character.
"""

@bot.event
async def on_ready():
print(f"Connected as {bot.user}")

async def generate_reply(user_input):
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
    return "Response generation failure."


@bot.event
async def on_message(message):
if message.author == bot.user:
return

print("MESSAGE RECEIVED:", message.content)

reply = await generate_reply(message.content)
await message.channel.send(reply)

await bot.process_commands(message)


bot.run(TOKEN)
