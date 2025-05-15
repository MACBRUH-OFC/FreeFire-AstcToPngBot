const { Telegraf } = require('telegraf');
const axios = require('axios');
const fs = require('fs');
const { execSync } = require('child_process');
const path = require('path');

// Configuration
const BOT_TOKEN = '7459415423:AAEOwutnGXxLXsuKhQCdGIHmuyILwQIXLEE';
const ALLOWED_GROUP_ID = -1002699301861;
const LIVE_BASE_URL = 'https://dl.dir.freefiremobile.com/live/ABHotUpdates/IconCDN/android/';
const ADVANCE_BASE_URL = 'https://dl.dir.freefiremobile.com/advance/ABHotUpdates/IconCDN/android/';

const bot = new Telegraf(BOT_TOKEN);

// Middleware to restrict access to specific group
bot.use((ctx, next) => {
  if (ctx.chat && ctx.chat.id === ALLOWED_GROUP_ID) {
    return next();
  }
  return ctx.reply('⚠️ This bot is currently restricted to private use.');
});

// Start command
bot.command('start', (ctx) => {
  ctx.reply(
    '🔥 Free Fire ASTC to PNG Converter 🔥\n' +
    'Commands:\n' +
    '/live <id> - Live server item\n' +
    '/adv <id> - Advance server item'
  );
});

// Convert ASTC to PNG
async function convertAstcToPng(astcData, itemId) {
  const tempDir = path.join('/tmp', `astc_${Date.now()}`);
  fs.mkdirSync(tempDir);
  
  const inputPath = path.join(tempDir, `${itemId}.astc`);
  const outputPath = path.join(tempDir, `${itemId}.png`);
  
  fs.writeFileSync(inputPath, astcData);
  
  try {
    execSync(`./astcenc -d ${inputPath} ${outputPath} 8x8 -fast`, {
      timeout: 8000
    });
    
    return fs.readFileSync(outputPath);
  } finally {
    // Clean up
    try { fs.unlinkSync(inputPath); } catch {}
    try { fs.unlinkSync(outputPath); } catch {}
    try { fs.rmdirSync(tempDir); } catch {}
  }
}

// Process single item
async function processItem(ctx, baseUrl, serverName, itemId) {
  try {
    const url = `${baseUrl}${itemId}_rgb.astc`;
    const response = await axios.get(url, {
      responseType: 'arraybuffer',
      timeout: 8000
    });
    
    ctx.reply('⏳ Converting...');
    const pngData = await convertAstcToPng(response.data, itemId);
    
    await ctx.replyWithPhoto({
      source: Buffer.from(pngData),
      filename: `${itemId}.png`
    }, {
      caption: `✅ ${serverName} ${itemId}`
    });
  } catch (error) {
    console.error('Conversion error:', error);
    ctx.reply(`❌ Failed to process ${itemId}`);
  }
}

// Commands
bot.command('live', (ctx) => {
  const itemId = ctx.message.text.split(' ')[1];
  if (!itemId) return ctx.reply('Please provide item ID');
  processItem(ctx, LIVE_BASE_URL, 'Live', itemId);
});

bot.command('adv', (ctx) => {
  const itemId = ctx.message.text.split(' ')[1];
  if (!itemId) return ctx.reply('Please provide item ID');
  processItem(ctx, ADVANCE_BASE_URL, 'Advance', itemId);
});

// Vercel serverless function handler
module.exports = async (req, res) => {
  if (req.method === 'POST') {
    try {
      await bot.handleUpdate(req.body);
      res.status(200).send('OK');
    } catch (error) {
      console.error('Error handling update:', error);
      res.status(500).send('Error');
    }
  } else {
    res.status(200).send('Free Fire ASTC to PNG Bot is running');
  }
};

// Local development
if (process.env.NODE_ENV === 'development') {
  bot.launch();
  console.log('Bot is running in polling mode...');
}
