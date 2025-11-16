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

// Load commands
const loadCommand = (commandName) => {
  try {
    const command = require(`./commands/${commandName}.js`);
    commands.set(commandName.toLowerCase(), command);
    console.log(`✅ Loaded command: ${commandName}`);
  } catch (error) {
    console.error(`❌ Failed to load command ${commandName}:`, error.message);
  }
};

// Initialize commands
const commandFiles = ['strike', 'promotion', 'deploymentStartPoll', 'deploymentStart', 'deploymentEnd'];
commandFiles.forEach(loadCommand);

// Register aliases (commands are loaded synchronously)
const pollCmd = commands.get('deploymentstartpoll');
const startCmd = commands.get('deploymentstart');
const endCmd = commands.get('deploymentend');

if (pollCmd) {
  commands.set('deployment-start-poll', pollCmd);
  commands.set('dsppoll', pollCmd);
}
if (startCmd) {
  commands.set('deploystart', startCmd);
  commands.set('deploy-start', startCmd);
}
if (endCmd) {
  commands.set('deployend', endCmd);
  commands.set('deploy-end', endCmd);
}

// Message command handler
client.on('messageCreate', async (message) => {
  if (message.author.bot) return;
  if (!message.content.startsWith(PREFIX)) return;

  const withoutPrefix = message.content.slice(PREFIX.length).trim();
  const [rawCommand, ...args] = withoutPrefix.split(/\s+/);
  const commandName = rawCommand.toLowerCase();

  const command = commands.get(commandName);
  if (!command) return;

  try {
    await command.execute(message, args, { client, sheets, SPREADSHEET_ID });
  } catch (error) {
    console.error(`Error executing command ${commandName}:`, error);
    await message.reply('❌ An error occurred while executing this command.').catch(() => {});
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
});

client.login(DISCORD_TOKEN);
