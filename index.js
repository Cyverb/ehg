const { Client, GatewayIntentBits } = require('discord.js');
const { google } = require('googleapis');
const http = require('http');

// Environment variables from Render
const DISCORD_TOKEN = process.env.TOKEN;
const CHANNEL_ID = process.env.CHANNEL_ID;
const SPREADSHEET_ID = process.env.SHEET_ID;
const PORT = process.env.PORT || 3000; // Render expects this

const client = new Client({
  intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildMessages, GatewayIntentBits.MessageContent]
});

// Google Sheets setup
const auth = new google.auth.GoogleAuth({
  keyFile: 'service-account.json', // Upload this file to Render project
  scopes: ['https://www.googleapis.com/auth/spreadsheets']
});
const sheets = google.sheets({ version: 'v4', auth });

client.on('messageCreate', async (message) => {
  if (message.channel.id !== CHANNEL_ID) return;
  if (message.author.id !== '155149108183695360') return; // Dyno's ID

  const content = message.content;
  if (!content.includes('DEPLOYMENT-LOG')) return;

  const vip = content.match(/VIP:\s*(.*?)\s*\|/i)?.[1] || '';
  const guards = content.match(/GUARDS:\s*(.*?)\s*\|/i)?.[1] || '';
  const duration = content.match(/DURATION:\s*(.*?)\s*\|/i)?.[1] || '';
  const vouch = content.match(/VOUCH:\s*(.*?)\s*/i)?.[1] || '';
  const submitter = content.match(/SUBMITTED BY\s*>>\s*"(.+?)"/i)?.[1] || 'Unknown';

  try {
    await sheets.spreadsheets.values.append({
      spreadsheetId: SPREADSHEET_ID,
      range: 'Sheet1!A:F',
      valueInputOption: 'USER_ENTERED',
      requestBody: {
        values: [[vip, guards, duration, vouch, submitter, new Date().toISOString()]]
      }
    });
    console.log('✅ Deployment logged.');
  } catch (error) {
    console.error('❌ Error logging deployment:', error);
  }
});

// Dummy HTTP server for Render port binding
http.createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'text/plain' });
  res.end('Bot is running\n');
}).listen(PORT, () => {
  console.log(`Server listening on port ${PORT}`);
});

// Login Discord bot
client.login(DISCORD_TOKEN);
