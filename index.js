const { Client, GatewayIntentBits } = require('discord.js');
const { google } = require('googleapis');
const fs = require('fs');

const PREFIX = 'E://';
const DEPLOYMENT_CHANNEL_ID = '1380934057785036870'; // channel where deployments are sent
const DYN0_USER_ID = '155149108183695360'; // Dyno's user ID
const SPREADSHEET_ID = '1d2lxlL3z_rZ_3Tcz9Ps7cgnf2yycm8SSZtJDotMCMrI';

// Create Discord client with needed intents
const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.MessageContent,
  ],
});

// Google Sheets auth setup
const auth = new google.auth.GoogleAuth({
  keyFile: 'service-account.json',
  scopes: ['https://www.googleapis.com/auth/spreadsheets'],
});
const sheets = google.sheets({ version: 'v4', auth });

// Helper function to parse Dyno's deployment message content
function parseDynoMessage(content) {
  // Dyno message example:
  // `🚨 Elite Honor Guard Self-Deployment Log
  // -------------[DEPLOYMENT LOG DATABASE]-------------
  // [E://] DEPLOYMENT-LOG >> VIP: Queen | GUARDS: GUARD,GUARD,GUARD | DURATION: DURATION | VOUCH: VOUCH,VOUCH,VOUCH
  // ---------------------------------------------------------------------------------
  // [E://] SUBMITTED BY >> "SAPPHIRE"`

  // Extract the line that contains "VIP:"
  const deploymentLine = content.split('\n').find(line => line.includes('VIP:'));
  if (!deploymentLine) return null;

  // Extract fields from that line
  // Format after ">>": VIP: Queen | GUARDS: GUARD,GUARD,GUARD | DURATION: DURATION | VOUCH: VOUCH,VOUCH,VOUCH
  const parts = deploymentLine.split('>>')[1];
  if (!parts) return null;

  const fields = parts.split('|').map(part => part.trim());

  let vip = '', guards = '', duration = '', vouch = '';

  fields.forEach(field => {
    if (field.toUpperCase().startsWith('VIP:')) {
      vip = field.slice(4).trim();
    } else if (field.toUpperCase().startsWith('GUARDS:')) {
      guards = field.slice(7).trim();
    } else if (field.toUpperCase().startsWith('DURATION:')) {
      duration = field.slice(9).trim();
    } else if (field.toUpperCase().startsWith('VOUCH:')) {
      vouch = field.slice(6).trim();
    }
  });

  // Extract submitted by from line containing SUBMITTED BY
  const submitLine = content.split('\n').find(line => line.includes('SUBMITTED BY'));
  let submittedBy = 'Unknown';
  if (submitLine) {
    const match = submitLine.match(/"(.+?)"/);
    if (match && match[1]) submittedBy = match[1];
  }

  return { vip, guards, duration, vouch, submittedBy };
}

client.on('messageCreate', async (message) => {
  try {
    // Only listen in the deployment channel
    if (message.channel.id !== DEPLOYMENT_CHANNEL_ID) return;

    // Only listen to Dyno's messages
    if (message.author.id !== DYN0_USER_ID) return;

    // Check if message starts with your prefix (optional, based on your Dyno format)
    if (!message.content.includes('DEPLOYMENT-LOG')) return;

    const parsed = parseDynoMessage(message.content);
    if (!parsed) {
      console.log('Failed to parse Dyno deployment message.');
      return;
    }

    const { vip, guards, duration, vouch, submittedBy } = parsed;

    // Append data to Google Sheet in the order: VIP, Guards, Duration, Vouch, Submitted By, Timestamp
    await sheets.spreadsheets.values.append({
      spreadsheetId: SPREADSHEET_ID,
      range: 'Sheet1!A:F',
      valueInputOption: 'USER_ENTERED',
      requestBody: {
        values: [
          [
            vip,
            guards,
            duration,
            vouch,
            submittedBy,
            new Date().toISOString(),
          ],
        ],
      },
    });

    console.log('Deployment logged for:', submittedBy);

  } catch (error) {
    console.error('Error processing deployment log:', error);
  }
});

client.login(process.env.TOKEN);
