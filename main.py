import os
import subprocess
import tempfile
import requests
import zipfile
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
        "/live <id> - Single item\n"
        "/live <start>-<end> - Multiple items\n"
        "/adv <id> - Advance server\n\n"
        "Example: /live 710049001-10"
    )

def download_astc_file(url: str) -> bytes:
    response = requests.get(url, timeout=8)
    response.raise_for_status()
    return response.content

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

def process_command(update: Update, context: CallbackContext, base_url: str, server_name: str):
    try:
        if not context.args:
            update.message.reply_text("Please provide item ID(s)")
            return

        arg = context.args[0]
        
        if '-' in arg:
            start_id, end_id = arg.split('-')
            item_ids = [f"{start_id[:-2]}{i:02d}" for i in range(int(start_id[-2:]), int(end_id)+1)]
        else:
            item_ids = [arg]

        for item_id in item_ids[:5]:  # Max 5 items for free tier
            try:
                astc_data = download_astc_file(f"{base_url}{item_id}_rgb.astc")
                png_data = convert_astc_to_png(astc_data)
                update.message.reply_photo(photo=png_data, caption=f"{server_name} {item_id}")
            except Exception as e:
                update.message.reply_text(f"❌ Failed {item_id}: {str(e)}")

    except Exception as e:
        update.message.reply_text(f"⚠️ Error: {str(e)}")

def live(update: Update, context: CallbackContext):
    process_command(update, context, LIVE_BASE_URL, "Live")

def adv(update: Update, context: CallbackContext):
    process_command(update, context, ADVANCE_BASE_URL, "Advance")

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
