const { Client, GatewayIntentBits } = require('discord.js');
const { google } = require('googleapis');
const http = require('http');

const DISCORD_TOKEN = process.env.TOKEN;
const CHANNEL_ID = process.env.CHANNEL_ID;
const SPREADSHEET_ID = process.env.SHEET_ID;
const PORT = process.env.PORT || 3000;
const PREFIX = process.env.PREFIX || '!';

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

const auth = new google.auth.GoogleAuth({
  keyFile: 'service-account.json',
  scopes: ['https://www.googleapis.com/auth/spreadsheets'],
});
const sheets = google.sheets({ version: 'v4', auth });

const commands = new Map();

commands.set('strike', {
  execute: async (message, args) => {
    message.reply('Strike command executed!');
  },
});

commands.set('promotion', {
  execute: async (message, args) => {
    message.reply('Promotion command executed!');
  },
});

commands.set('deploymentstartpoll', {
  execute: async (message, args) => {
    message.reply('Deployment start poll executed!');
  },
});
commands.set('deployment-start-poll', commands.get('deploymentstartpoll'));
commands.set('dsppoll', commands.get('deploymentstartpoll'));

commands.set('deploymentstart', {
  execute: async (message, args) => {
    message.reply('Deployment start executed!');
  },
});
commands.set('deploy-start', commands.get('deploymentstart'));
commands.set('deploystart', commands.get('deploymentstart'));

commands.set('deploymentend', {
  execute: async (message, args) => {
    message.reply('Deployment end executed!');
  },
});
commands.set('deploy-end', commands.get('deploymentend'));
commands.set('deployend', commands.get('deploymentend'));

console.log(`📌 Total commands loaded: ${commands.size}`);
console.log('📋 Registered commands:', Array.from(commands.keys()).join(', '));

client.on('messageCreate', async (message) => {
  if (message.author.bot) return;
  if (!message.content.startsWith(PREFIX)) return;

  const withoutPrefix = message.content.slice(PREFIX.length).trim();
  let commandName = '';
  let args = [];

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

  if (!matched) {
    const parts = withoutPrefix.split(/\s+/);
    commandName = parts[0].toLowerCase();
    args = parts.slice(1);
  }

  const command = commands.get(commandName);
  if (!command) return;

  try {
    await command.execute(message, args, { client, sheets, SPREADSHEET_ID });
  } catch (err) {
    console.error(`❌ Error executing command ${commandName}:`, err);
    message.reply('❌ Error executing this command.').catch(() => {});
  }
});

http.createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'text/plain' });
  res.end('Bot is running\n');
}).listen(PORT, () => {
  console.log(`Server listening on port ${PORT}`);
});

client.once('ready', () => {
  console.log(`✅ Bot logged in as ${client.user.tag}`);
  console.log('📋 Loaded commands:', Array.from(commands.keys()).join(', '));
});

client.login(DISCORD_TOKEN);
