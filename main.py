import os
import subprocess
import requests
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

BOT_TOKEN = os.getenv('BOT_TOKEN')
ALLOWED_GROUP_ID = -1002699301861

# Base URLs
LIVE_BASE_URL = "https://dl.dir.freefiremobile.com/live/ABHotUpdates/IconCDN/android/"
ADVANCE_BASE_URL = "https://dl.dir.freefiremobile.com/advance/ABHotUpdates/IconCDN/android/"

def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        "🔥 Free Fire ASTC to PNG Converter 🔥\n"
        "Commands:\n"
        "/live <id> - Live server item\n"
        "/adv <id> - Advance server item\n\n"
        "Example: /live {item id}"
    )

def convert_astc_to_png(astc_data: bytes) -> bytes:
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

def process_single_item(update: Update, base_url: str, server_name: str, item_id: str):
    try:
        # Download ASTC file
        response = requests.get(f"{base_url}{item_id}_rgb.astc", timeout=8)
        response.raise_for_status()
        
        # Convert to PNG
        png_data = convert_astc_to_png(response.content)
        
        # Send result
        update.message.reply_photo(
            photo=png_data,
            caption=f"{server_name} {item_id}"
        )
    except requests.exceptions.RequestException:
        update.message.reply_text(f"❌ Failed to download {item_id}")
    except subprocess.TimeoutExpired:
        update.message.reply_text("⌛ Conversion timed out")
    except Exception as e:
        update.message.reply_text(f"⚠️ Error: {str(e)}")

def live(update: Update, context: CallbackContext):
    if not context.args:
        update.message.reply_text("Please provide item ID")
        return
    process_single_item(update, LIVE_BASE_URL, "Live", context.args[0])

def adv(update: Update, context: CallbackContext):
    if not context.args:
        update.message.reply_text("Please provide item ID")
        return
    process_single_item(update, ADVANCE_BASE_URL, "Advance", context.args[0])

def vercel_handler(event, context):
    updater = Updater(BOT_TOKEN)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("live", live))
    dp.add_handler(CommandHandler("adv", adv))
    updater.start_polling()
    return {'statusCode': 200}

if __name__ == '__main__':
    vercel_handler(None, None)
