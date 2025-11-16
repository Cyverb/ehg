const { Client, GatewayIntentBits } = require('discord.js');
const { google } = require('googleapis');
const http = require('http');
const fs = require('fs');
const path = require('path');

// Environment variables
const DISCORD_TOKEN = process.env.TOKEN;
const CHANNEL_ID = process.env.CHANNEL_ID;
const SPREADSHEET_ID = process.env.SHEET_ID;
const PORT = process.env.PORT || 3000;
const PREFIX = process.env.PREFIX || '!';

// Debug environment variables
console.log('DISCORD_TOKEN:', DISCORD_TOKEN ? 'Loaded' : 'Missing');
console.log('CHANNEL_ID:', CHANNEL_ID || 'Missing');
console.log('SPREADSHEET_ID:', SPREADSHEET_ID || 'Missing');
console.log('PORT:', PORT);

const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.MessageContent,
    GatewayIntentBits.GuildMembers,
    GatewayIntentBits.GuildMessageReactions,
  ],
});

// Google Sheets setup
const auth = new google.auth.GoogleAuth({
  keyFile: 'service-account.json',
  scopes: ['https://www.googleapis.com/auth/spreadsheets'],
});
const sheets = google.sheets({ version: 'v4', auth });

// Command handler
const commands = new Map();

// Path helper (fixes render/fs issues)
const pathTo = (...p) => path.join(__dirname, ...p);

// *********************************************************
// MANUAL COMMAND LOADER — FULLY FIXED
// *********************************************************
let loaded = 0;

function load(name, filename, aliases = []) {
  try {
    const filePath = pathTo('commands', filename);
    const cmd = require(filePath);

    if (!cmd || typeof cmd.execute !== 'function') {
      console.error(`❌ ${name} is missing execute()`);
      return;
    }

    commands.set(name.toLowerCase(), cmd);

    // Register aliases
    for (const alias of aliases) {
      commands.set(alias.toLowerCase(), cmd);
    }

    console.log(`✅ Loaded command: ${name}`);
    loaded++;

  } catch (err) {
    console.error(`❌ Failed to load ${name}:`, err.message);
  }
}

// ---- REAL COMMANDS ----
load("strike", "strike.js");
load("promotion", "promotion.js");

load("deploymentstartpoll", "deploymentStartPoll.js", [
  "deployment-start-poll",
  "dsppoll"
]);

load("deploymentstart", "deploymentStart.js", [
  "deploy-start",
  "deploystart"
]);

load("deploymentend", "deploymentEnd.js", [
  "deploy-end",
  "deployend"
]);

console.log(`📌 Total commands loaded: ${loaded}`);
console.log("📋 Commands registered:", Array.from(commands.keys()).join(", "));
// *********************************************************


// Message command handler
client.on('messageCreate', async (message) => {
  if (message.author.bot) return;
  if (!message.content.startsWith(PREFIX)) return;

  const withoutPrefix = message.content.slice(PREFIX.length).trim();

  let commandName = '';
  let args = [];

  // Longest-match for commands
  const sortedCommands = Array.from(commands.keys()).sort((a, b) => b.length - a.length);
  let matched = false;

  for (const cmd of sortedCommands) {
    if (withoutPrefix.toLowerCase().startsWith(cmd)) {
      const nextChar = withoutPrefix[cmd.length];
      if (!nextChar || nextChar === ' ' || nextChar === '|') {
        commandName = cmd;
        args = withoutPrefix.slice(cmd.length).trim().split(/\s+/);
        matched = true;
        break;
      }
    }
  }

  // Fallback simple parser
  if (!matched) {
    const parts = withoutPrefix.split(/\s+/);
    commandName = parts[0].toLowerCase();
    args = parts.slice(1);
  }

  console.log(`[Command] Attempt: ${commandName}`);

  const command = commands.get(commandName);
  if (!command) {
    console.log(`[Command] Not found: "${commandName}"`);
    return;
  }

  console.log(`[Command] Executing: ${commandName}`);

  try {
    await command.execute(message, args, { client, sheets, SPREADSHEET_ID });
  } catch (error) {
    console.error(`❌ Error executing ${commandName}:`, error);
    await message.reply('❌ Error executing this command.').catch(() => {});
  }
});

// HTTP server for Render port binding
http.createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'text/plain' });
  res.end('Bot is running\n');
}).listen(PORT, () => {
  console.log(`Server listening on port ${PORT}`);
});

client.once('ready', () => {
  console.log(`✅ Bot logged in as ${client.user.tag}`);
  console.log(`📋 Loaded commands:`, Array.from(commands.keys()).join(', '));
});

client.login(DISCORD_TOKEN);
