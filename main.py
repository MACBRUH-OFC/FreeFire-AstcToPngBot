import os
import subprocess
import tempfile
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Hardcoded configuration
BOT_TOKEN = "7459415423:AAEOwutnGXxLXsuKhQCdGIHmuyILwQIXLEE"
ALLOWED_GROUP_ID = -1002699301861
LIVE_BASE_URL = "https://dl.dir.freefiremobile.com/live/ABHotUpdates/IconCDN/android/"
ADVANCE_BASE_URL = "https://dl.dir.freefiremobile.com/advance/ABHotUpdates/IconCDN/android/"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message"""
    await update.message.reply_text(
        "🔥 Free Fire ASTC to PNG Converter 🔥\n"
        "Commands:\n"
        "/live <id> - Live server item\n"
        "/adv <id> - Advance server item"
    )

async def convert_astc_to_png(astc_data: bytes) -> bytes:
    """Convert ASTC to PNG using the binary"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        input_path = os.path.join(tmp_dir, "input.astc")
        output_path = os.path.join(tmp_dir, "output.png")
        
        with open(input_path, 'wb') as f:
            f.write(astc_data)
        
        subprocess.run(
            ["./astcenc", "-d", input_path, output_path, "8x8", "-fast"],
            check=True,
            timeout=8
        )
        
        with open(output_path, 'rb') as f:
            return f.read()

async def process_single_item(update: Update, base_url: str, server_name: str, item_id: str):
    """Process single item conversion"""
    try:
        # Download ASTC file
        response = requests.get(f"{base_url}{item_id}_rgb.astc", timeout=8)
        response.raise_for_status()
        
        # Convert to PNG
        png_data = await convert_astc_to_png(response.content)
        
        # Send result
        await update.message.reply_photo(
            photo=png_data,
            caption=f"{server_name} {item_id}"
        )
    except requests.exceptions.RequestException:
        await update.message.reply_text(f"❌ Failed to download {item_id}")
    except subprocess.TimeoutExpired:
        await update.message.reply_text("⌛ Conversion timed out")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {str(e)}")

async def live(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /live command"""
    if not context.args:
        await update.message.reply_text("Please provide item ID")
        return
    await process_single_item(update, LIVE_BASE_URL, "Live", context.args[0])

async def adv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /adv command"""
    if not context.args:
        await update.message.reply_text("Please provide item ID")
        return
    await process_single_item(update, ADVANCE_BASE_URL, "Advance", context.args[0])

def setup_handlers(application):
    """Configure command handlers"""
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("live", live))
    application.add_handler(CommandHandler("adv", adv))

def webhook(request):
    """Vercel serverless function handler"""
    if request.method == "POST":
        application = ApplicationBuilder().token(BOT_TOKEN).build()
        setup_handlers(application)
        
        # For Vercel deployment
        return {
            'statusCode': 200,
            'body': 'Webhook set successfully'
        }
    
    # Return simple response for GET requests
    return {
        'statusCode': 200,
        'body': 'Bot is running',
        'headers': {'Content-Type': 'text/plain'}
    }

if __name__ == '__main__':
    # Local development mode
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    setup_handlers(application)
    application.run_polling()
