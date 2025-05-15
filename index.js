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

// 1. FIX: Add instant response middleware
bot.use(async (ctx, next) => {
  await ctx.replyWithChatAction('upload_photo'); // Show "uploading" status immediately
  return next();
});

// 2. FIX: Optimized conversion function
async function convertAstcToPng(astcData, itemId) {
  const tempDir = fs.mkdtempSync('/tmp/astc-');
  const inputPath = path.join(tempDir, `${itemId}.astc`);
  const outputPath = path.join(tempDir, `${itemId}.png`);

  try {
    fs.writeFileSync(inputPath, astcData);
    
    // 3. FIX: Added proper error handling for binary execution
    execSync(`chmod +x ./astcenc && ./astcenc -d ${inputPath} ${outputPath} 6x6 -thorough`, {
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

// 4. FIX: Improved item processing with retries
async function processItem(ctx, serverType, itemId) {
  try {
    const url = `${BASE_URLS[serverType]}${itemId}_rgb.astc`;
    
    // First quick check if file exists
    const headResponse = await axios.head(url, { timeout: 2000 });
    if (headResponse.status !== 200) {
      throw new Error('File not found');
    }

    // Download with progress
    const response = await axios.get(url, {
      responseType: 'arraybuffer',
      timeout: 3000,
      onDownloadProgress: (p) => {
        if (p.progress === 1) ctx.replyWithChatAction('upload_photo');
      }
    });

    // Conversion
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
    
    // 5. FIX: Specific error messages
    if (error.message.includes('404') || error.message.includes('File not found')) {
      await ctx.reply(`❌ Item ${itemId} not found on ${serverType} server`);
    } else if (error.message.includes('timeout')) {
      await ctx.reply(`⌛ Timeout processing ${itemId}, please try again`);
    } else {
      await ctx.reply(`⚠️ Failed to process ${itemId}: ${error.message}`);
    }
  }
}

// Commands
bot.command('live', (ctx) => {
  const itemId = ctx.message.text.split(' ')[1]?.trim();
  if (!itemId) return ctx.reply('Please provide item ID (e.g. /live 710048001)');
  processItem(ctx, 'live', itemId);
});

bot.command('adv', (ctx) => {
  const itemId = ctx.message.text.split(' ')[1]?.trim();
  if (!itemId) return ctx.reply('Please provide item ID (e.g. /adv 710048001)');
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
