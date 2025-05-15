const { Telegraf } = require('telegraf');
const axios = require('axios');
const fs = require('fs');
const { execSync } = require('child_process');
const path = require('path');

// Config
const BOT_TOKEN = '7459415423:AAEOwutnGXxLXsuKhQCdGIHmuyILwQIXLEE';
const ALLOWED_GROUP_ID = -1002699301861;
const BASE_URLS = {
  live: 'https://dl.dir.freefiremobile.com/live/ABHotUpdates/IconCDN/android/',
  advance: 'https://dl.dir.freefiremobile.com/advance/ABHotUpdates/IconCDN/android/'
};

const bot = new Telegraf(BOT_TOKEN);

// Middleware to only respond to commands in group
bot.use((ctx, next) => {
  if (ctx.chat?.id !== ALLOWED_GROUP_ID || !ctx.message?.text?.startsWith('/')) {
    return;
  }
  return next();
});

// Start command
bot.command('start', (ctx) => {
  ctx.reply(
    '🔥 Free Fire ASTC to PNG Converter 🔥\n' +
    'Commands:\n' +
    '/live <id> - Live server item\n' +
    '/adv <id> - Advance server item\n\n' +
    'Example: /live 710049001'
  );
});

// Optimized conversion with retries
async function convertAstcToPng(astcData, itemId) {
  const tempDir = fs.mkdtempSync('/tmp/astc-');
  const inputPath = path.join(tempDir, `${itemId}.astc`);
  const outputPath = path.join(tempDir, `${itemId}.png`);

  try {
    fs.writeFileSync(inputPath, astcData);
    
    // Using fastest compression for speed
    execSync(`chmod +x ./astcenc && ./astcenc -d ${inputPath} ${outputPath} 6x6 -fastest`, {
      timeout: 4000
    });

    if (!fs.existsSync(outputPath)) {
      throw new Error('Conversion failed');
    }

    return fs.readFileSync(outputPath);
  } finally {
    // Cleanup
    [inputPath, outputPath].forEach(file => {
      try { fs.unlinkSync(file); } catch {}
    });
    try { fs.rmdirSync(tempDir); } catch {}
  }
}

// Process item with optimized timing
async function processItem(ctx, serverType, itemId) {
  try {
    const url = `${BASE_URLS[serverType]}${itemId}_rgb.astc`;
    
    // Immediate feedback
    await ctx.replyWithChatAction('upload_photo');
    
    // Fast download with retry
    const response = await axios.get(url, {
      responseType: 'arraybuffer',
      timeout: 2500,
      retry: 1
    });

    // Convert with progress feedback
    await ctx.replyWithChatAction('upload_photo');
    const pngBuffer = await convertAstcToPng(response.data, itemId);
    
    // Send result
    await ctx.replyWithPhoto({
      source: pngBuffer,
      filename: `${itemId}.png`
    }, {
      caption: `✅ ${serverType === 'live' ? 'Live' : 'Advance'} ${itemId}`
    });

  } catch (error) {
    console.error(`Error processing ${itemId}:`, error.message);
    
    if (error.response?.status === 404) {
      await ctx.reply(`❌ ${itemId} not found on ${serverType} server`);
    } else if (error.code === 'ECONNABORTED') {
      await ctx.reply(`⌛ Server busy, try again later`);
    } else {
      await ctx.reply(`⚠️ Failed to process ${itemId}: ${error.message}`);
    }
  }
}

// Command handlers with strict validation
bot.command('live', (ctx) => {
  const itemId = ctx.message.text.split(' ')[1]?.trim();
  if (!itemId || !/^\d{9}$/.test(itemId)) {
    return ctx.reply('❌ Invalid ID format. Use: /live 710049001');
  }
  processItem(ctx, 'live', itemId);
});

bot.command('adv', (ctx) => {
  const itemId = ctx.message.text.split(' ')[1]?.trim();
  if (!itemId || !/^\d{9}$/.test(itemId)) {
    return ctx.reply('❌ Invalid ID format. Use: /adv 710049001');
  }
  processItem(ctx, 'advance', itemId);
});

// Vercel handler
module.exports = async (req, res) => {
  if (req.method === 'POST') {
    try {
      await bot.handleUpdate(req.body);
      return res.status(200).send('OK');
    } catch (error) {
      console.error('Webhook error:', error);
      return res.status(500).send('Error');
    }
  }
  return res.status(200).send('Bot is running');
};

// Local dev
if (process.env.NODE_ENV === 'development') {
  bot.launch();
  console.log('Bot running in polling mode');
}
