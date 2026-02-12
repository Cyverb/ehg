## EllieVC – Discord Voice Chat Bot (Gemini-powered)

EllieVC is a simple Discord bot that:

- **Joins your voice channel**
- **Uses Google Gemini to generate conversational replies**
- **Uses TTS (gTTS) to speak those replies in the voice channel**

This first version uses **text commands as the wake trigger** (e.g. you type “hey ellie”), and Ellie answers **out loud in VC**. At the end of this README there’s a short section describing how to move toward **true voice wake-word detection** if you want to experiment.

---

### 1. Prerequisites

- **Python 3.10+** installed
- **FFmpeg** installed and on your `PATH` (required for Discord audio playback)
  - Windows: download from the FFmpeg site, extract, and add the `bin` folder to your system `PATH`.
- A **Discord Bot**:
  - Create an application at the Discord Developer Portal.
  - Add a **Bot** user.
  - Enable **MESSAGE CONTENT INTENT** and **PRESENCE INTENT**.
  - Under OAuth2 → URL Generator, select:
    - Scopes: `bot`
    - Bot Permissions: at least `Connect`, `Speak`, `View Channels`, `Send Messages`
  - Invite the bot to your server with the generated URL.
- A **Google Gemini API key**:
  - Get one from Google AI Studio.
  - This will be used by Ellie to generate conversational replies.

---

### 2. Setup

From your workspace root (`EllieVC`):

```bash
pip install -r requirements.txt
```

Create a `.env` file next to `bot.py`:

```env
DISCORD_TOKEN=your_discord_bot_token_here
GEMINI_API_KEY=your_gemini_api_key_here
```

---

### 3. Running the bot

From the project folder:

```bash
python bot.py
```

If everything is configured correctly, you’ll see a log message that the bot is online.

---

### 4. Using Ellie in your server

- **Join VC**
  - Join a voice channel yourself.
  - In any text channel, type:
    - `!join`
  - Ellie joins the voice channel you’re in.

- **Talk to Ellie (wake phrase via text)**
  - In a text channel, type:
    - `hey ellie`  
      or
    - `!ellie hey ellie` (or any other message)
  - Ellie will:
    - Use Gemini to generate a conversational reply.
    - Use TTS (gTTS) to synthesize audio.
    - **Speak the reply in the voice channel**.

- **Leave VC**
  - `!leave`

---

### 5. Notes on real voice wake-word detection

Discord does not make continuous raw voice input trivial; you have to **record voice from the channel**, send it to a **speech-to-text model** (like Whisper or a Google Speech-to-Text API), and then check for your wake phrase (“hey ellie”) in the transcript.

To move toward a true “VC conversation” with spoken “hey ellie”:

- Use a Discord library build that supports **voice receive / recording** (e.g. `discord.py` with sinks, or specialized forks).
- Periodically send recorded chunks to a **speech-to-text service** (e.g. local Whisper, or Google Speech-to-Text).
- When the transcript contains “hey ellie”, send that transcript to Gemini for a reply, then TTS, then play it back as shown in `bot.py`.

The current code is structured so you can plug in that recording/transcription step later without changing the GPT + TTS reply path.

