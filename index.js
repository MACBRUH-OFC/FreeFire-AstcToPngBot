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

// 1. FIX: Only respond to commands in group
bot.use((ctx, next) => {
  // Ignore if not a command or not in allowed group
  if (!ctx.message || !ctx.message.text || !ctx.message.text.startsWith('/') || ctx.chat.id !== ALLOWED_GROUP_ID) {
    return;
  }
  return next();
});

// Start command
bot.command('start', (ctx) => {
  ctx.reply(
    '🔥 Free Fire ASTC to PNG Converter 🔥\n' +
    'Commands:\n' +
    '/live <id> - Convert from Live server\n' +
    '/adv <id> - Convert from Advance server\n\n' +
    'Example: /live 710049001'
  );
});

// Optimized conversion function
async function convertAstcToPng(astcData, itemId) {
  const tempDir = fs.mkdtempSync('/tmp/astc-');
  const inputPath = path.join(tempDir, `${itemId}.astc`);
  const outputPath = path.join(tempDir, `${itemId}.png`);

  try {
    fs.writeFileSync(inputPath, astcData);
    
    // 2. FIX: Updated conversion parameters for Free Fire assets
    execSync(`./astcenc -d ${inputPath} ${outputPath} 6x6 -fast`, {
      timeout: 5000,
      stdio: 'pipe'
    });

    if (!fs.existsSync(outputPath)) {
      throw new Error('Conversion failed - no output file');
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

// Process item with better error handling
async function processItem(ctx, serverType, itemId) {
  try {
    const url = `${BASE_URLS[serverType]}${itemId}_rgb.astc`;
    
    // Show typing indicator
    await ctx.replyWithChatAction('upload_photo');
    
    // Download with timeout
    const response = await axios.get(url, {
      responseType: 'arraybuffer',
      timeout: 3000
    });

    // Convert
    const pngBuffer = await convertAstcToPng(response.data, itemId);
    
    // Send result
    await ctx.replyWithPhoto({
      source: pngBuffer,
      filename: `${itemId}.png`
    }, {
      caption: `✅ ${serverType === 'live' ? 'Live' : 'Advance'} Server ${itemId}`
    });

  } catch (error) {
    console.error(`Error processing ${itemId}:`, error.message);
    
    // 3. FIX: Specific error messages
    if (error.response?.status === 404) {
      await ctx.reply(`❌ Item ${itemId} not found on ${serverType} server`);
    } else if (error.code === 'ECONNABORTED') {
      await ctx.reply(`⌛ Download timeout for ${itemId}, server may be busy`);
    } else if (error.message.includes('timeout')) {
      await ctx.reply(`⌛ Conversion timeout for ${itemId}, please try again`);
    } else {
      await ctx.reply(`⚠️ Failed to process ${itemId}: ${error.message}`);
    }
  }
}

// Commands with strict validation
bot.command('live', (ctx) => {
  const itemId = ctx.message.text.split(' ')[1]?.trim();
  if (!itemId || !/^\d+$/.test(itemId)) {
    return ctx.reply('Please provide a valid item ID (e.g. /live 710049001)');
  }
  processItem(ctx, 'live', itemId);
});

bot.command('adv', (ctx) => {
  const itemId = ctx.message.text.split(' ')[1]?.trim();
  if (!itemId || !/^\d+$/.test(itemId)) {
    return ctx.reply('Please provide a valid item ID (e.g. /adv 710049001)');
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
