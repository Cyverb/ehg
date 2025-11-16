const { Client, GatewayIntentBits } = require('discord.js');
const { google } = require('googleapis');
const http = require('http');

const DISCORD_TOKEN = process.env.TOKEN;
const CHANNEL_ID = process.env.CHANNEL_ID;
const SPREADSHEET_ID = process.env.SHEET_ID;
const PORT = process.env.PORT || 3000;
const PREFIX = process.env.PREFIX || '!';

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

// ----------------- STRIKE -----------------
commands.set('strike', {
  execute: async (message, args, { sheets, SPREADSHEET_ID }) => {
    if (!args[0]) return message.reply('❌ Please mention a user: !strike @User');

    const user = message.mentions.users.first();
    if (!user) return message.reply('❌ Invalid user mention.');

    let strikes = 0;

    try {
      const res = await sheets.spreadsheets.values.get({
        spreadsheetId: SPREADSHEET_ID,
        range: 'Strikes!A:B', // A=User ID, B=Strike count
      });

      const rows = res.data.values || [];
      const foundIndex = rows.findIndex(row => row[0] === user.id);

      if (foundIndex !== -1) {
        strikes = parseInt(rows[foundIndex][1] || '0', 10) + 1;
        await sheets.spreadsheets.values.update({
          spreadsheetId: SPREADSHEET_ID,
          range: `Strikes!B${foundIndex + 1}`,
          valueInputOption: 'RAW',
          requestBody: { values: [[strikes]] },
        });
      } else {
        strikes = 1;
        await sheets.spreadsheets.values.append({
          spreadsheetId: SPREADSHEET_ID,
          range: 'Strikes!A:B',
          valueInputOption: 'RAW',
          requestBody: { values: [[user.id, strikes]] },
        });
      }
    } catch (err) {
      console.error('Error accessing Strikes sheet:', err);
    }

    message.channel.send(
      `User: ${user.tag}\nTotal Strikes: ${strikes}\nDate: ${new Date().toLocaleDateString()}`
    );
  },
});

// ----------------- PROMOTION -----------------
commands.set('promotion', {
  execute: async (message, args, { sheets, SPREADSHEET_ID }) => {
    if (!args[0]) return message.reply('❌ Please mention a user: !promotion @User NewRank');

    const user = message.mentions.users.first();
    if (!user) return message.reply('❌ Invalid user mention.');
    const newRank = args[1] || 'Unknown';

    let previousRank = 'None';

    try {
      const res = await sheets.spreadsheets.values.get({
        spreadsheetId: SPREADSHEET_ID,
        range: 'Ranks!A:B',
      });

      const rows = res.data.values || [];
      const foundIndex = rows.findIndex(row => row[0] === user.id);

      if (foundIndex !== -1) {
        previousRank = rows[foundIndex][1] || 'None';
        await sheets.spreadsheets.values.update({
          spreadsheetId: SPREADSHEET_ID,
          range: `Ranks!B${foundIndex + 1}`,
          valueInputOption: 'RAW',
          requestBody: { values: [[newRank]] },
        });
      } else {
        await sheets.spreadsheets.values.append({
          spreadsheetId: SPREADSHEET_ID,
          range: 'Ranks!A:B',
          valueInputOption: 'RAW',
          requestBody: { values: [[user.id, newRank]] },
        });
      }
    } catch (err) {
      console.error('Error accessing Ranks sheet:', err);
    }

    message.channel.send(
      `User: ${user.tag}\nPrevious Rank: ${previousRank}\nNew Rank: ${newRank}\nDate: ${new Date().toLocaleDateString()}`
    );
  },
});

// ----------------- DEPLOYMENT START POLL -----------------
commands.set('deploymentstartpoll', {
  execute: async (message, args) => {
    message.channel.send(`Deployment start poll created! Use reactions to vote.`);
  },
});
commands.set('deployment-start-poll', commands.get('deploymentstartpoll'));
commands.set('dsppoll', commands.get('deploymentstartpoll'));

// ----------------- DEPLOYMENT START -----------------
commands.set('deploymentstart', {
  execute: async (message, args) => {
    message.channel.send(
      `Deployment started!\nTime: ${args[0] || 'Unknown'}\nTeam: ${args[1] || 'Unknown'}`
    );
  },
});
commands.set('deploy-start', commands.get('deploymentstart'));
commands.set('deploystart', commands.get('deploymentstart'));

// ----------------- DEPLOYMENT END -----------------
commands.set('deploymentend', {
  execute: async (message, args) => {
    message.channel.send(
      `Deployment ended!\nTime: ${args[0] || 'Unknown'}\nTeam: ${args[1] || 'Unknown'}`
    );
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
