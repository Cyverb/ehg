const { Client, GatewayIntentBits } = require('discord.js');
const { google } = require('googleapis');
const http = require('http');

// Environment variables from Render
const DISCORD_TOKEN = process.env.TOKEN;
const CHANNEL_ID = process.env.CHANNEL_ID;
const SPREADSHEET_ID = process.env.SHEET_ID;
const PORT = process.env.PORT || 3000;
const WARRANT_ROLE_ID = process.env.WARRANT_ROLE_ID || '1253735270914719787';

// Debug environment variables (remove after confirming)
console.log('DISCORD_TOKEN:', DISCORD_TOKEN ? 'Loaded' : 'Missing');
console.log('CHANNEL_ID:', CHANNEL_ID || 'Missing');
console.log('SPREADSHEET_ID:', SPREADSHEET_ID || 'Missing');
console.log('PORT:', PORT);

const client = new Client({
  intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildMessages, GatewayIntentBits.MessageContent],
});

// Google Sheets setup
const auth = new google.auth.GoogleAuth({
  keyFile: 'service-account.json', // Make sure this file is uploaded to your Render project root
  scopes: ['https://www.googleapis.com/auth/spreadsheets'],
});
const sheets = google.sheets({ version: 'v4', auth });

// Simple command handler: !warrant
client.on('messageCreate', async (message) => {
  if (message.author.bot) return;

  const prefix = process.env.PREFIX || '!';
  if (!message.content.startsWith(prefix)) return;

  const withoutPrefix = message.content.slice(prefix.length).trim();
  const [rawCommand, ...rest] = withoutPrefix.split(' ');
  const command = rawCommand.toLowerCase();

  if (command !== 'warrant') return;

  const parts = rest.join(' ').split('|').map(s => s.trim()).filter(Boolean);
  // Expected:
  // !warrant @RoleToNotify | @Subject or Name | Summary/Reason | Threat Level | Threat bullets (semicolon-separated) | Actions (semicolon-separated)
  if (parts.length < 2) {
    await message.reply('Usage: !warrant @RoleToNotify | @Subject or Name | Summary/Reason | Threat Level | threat1; threat2; threat3 | action1; action2; action3');
    return;
  }

  const defaultRoleMention = `<@&${WARRANT_ROLE_ID}>`;
  const roleMention = parts[0] && parts[0] !== '-' ? parts[0] : defaultRoleMention;
  const subject = parts[1] || 'Unknown Subject';
  const summaryReason = parts[2] || 'Subject is to be arrested on-sight if criteria are met.';
  const threatLevel = parts[3] || 'Level I – Civil disruption, protests, or interference';
  const threatBullets = (parts[4] || 'Subject attempted to bribe EHG Command; Subject is a threat to EHG integrity').split(';').map(s => s.trim()).filter(Boolean);
  const actionBullets = (parts[5] || 'Detainment of individual; Interrogation conducted by HARBINGER; Termination is approved if individual causes a scene.').split(';').map(s => s.trim()).filter(Boolean);

  const threatList = threatBullets.map(b => `- ${b}`).join('\n');
  const actionList = actionBullets.map(b => `- ${b}`).join('\n');

  const noticeLines = [
    `${roleMention}`,
    '',
    '**NOTICE – Active Warrant**',
    '',
    `All personnel are to keep an eye out for, or on, ${subject}. ${summaryReason} Personnel are advised to approach with caution. Once the arrest is completed, an incident report should be filled out with a summary of what happened during the arrest of this individual.`,
    '',
    `**Threat Level** – ${threatLevel}`,
    '',
    '**Indicators / Justification**',
    threatList,
    '',
    '**Actions Requested**',
    actionList
  ];

  const content = noticeLines.join('\n');
  await message.channel.send({ content });
});

client.on('messageCreate', async (message) => {
  if (message.channel.id !== CHANNEL_ID) return;
  if (message.author.id !== '155149108183695360') return; // Dyno's user ID

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
        values: [[vip, guards, duration, vouch, submitter, new Date().toISOString()]],
      },
    });
    console.log('✅ Deployment logged.');
  } catch (error) {
    console.error('❌ Error logging deployment:', error);
  }
});

// HTTP server for Render port binding
http.createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'text/plain' });
  res.end('Bot is running\n');
}).listen(PORT, () => {
  console.log(`Server listening on port ${PORT}`);
});

client.login(DISCORD_TOKEN);
