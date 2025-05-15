import os
import subprocess
import tempfile
import requests
import zipfile
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

BOT_TOKEN = os.getenv('BOT_TOKEN')  # From environment variables
ALLOWED_GROUP_ID = -1002699301861  

# Base URLs
LIVE_BASE_URL = "https://dl.dir.freefiremobile.com/live/ABHotUpdates/IconCDN/android/"
ADVANCE_BASE_URL = "https://dl.dir.freefiremobile.com/advance/ABHotUpdates/IconCDN/android/"

def restricted(func):
    """Decorator to restrict access to the allowed group only"""
    def wrapped(update: Update, context: CallbackContext, *args, **kwargs):
        if update.effective_chat.id != ALLOWED_GROUP_ID:
            update.message.reply_text("⚠️ This bot is currently restricted to private use.")
            return
        return func(update, context, *args, **kwargs)
    return wrapped

@restricted
def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        "🔥 Free Fire ASTC to PNG Converter 🔥\n\n"
        "Commands:\n"
        "/live <id> - Live server item\n"
        "/live <start>-<end> - Multiple items\n"
        "/adv <id> - Advance server item\n"
        "/adv <start>-<end> - Multiple items\n"
    )

@restricted
def help_command(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        "Send item ID or range to convert:\n"
        "/live 710049001 - Single item\n"
        "/live 710049001-50 - From 001 to 050\n"
        "Same for /adv command\n\n"
        "Max 100 items per request"
    )

def download_astc_file(url: str, file_path: str) -> bool:
    try:
        response = requests.get(url, stream=True, timeout=15)
        if response.status_code == 200:
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
        return False
    except Exception:
        return False

def convert_astc_to_png(astc_path: str, png_path: str) -> bool:
    try:
        command = [
            "./astcenc-avx2",
            "-d", astc_path, png_path,
            "8x8", "-thorough"
        ]
        result = subprocess.run(command, capture_output=True, text=True, timeout=20)
        return result.returncode == 0
    except Exception:
        return False

def format_failed_ids(failed_ids):
    """Format failed IDs into ranges where possible"""
    if not failed_ids:
        return []
    
    failed_ids = sorted([int(id) for id in failed_ids])
    formatted = []
    start = failed_ids[0]
    prev = start
    
    for num in failed_ids[1:]:
        if num == prev + 1:
            prev = num
        else:
            if start == prev:
                formatted.append(f"{start:09d}")
            else:
                formatted.append(f"{start:09d}-{prev:09d}")
            start = num
            prev = num
    
    if start == prev:
        formatted.append(f"{start:09d}")
    else:
        formatted.append(f"{start:09d}-{prev:09d}")
    
    return formatted

def process_item_request(update: Update, context: CallbackContext, base_url: str, server_name: str):
    if not context.args:
        update.message.reply_text("Please provide item ID(s)")
        return
    
    input_range = context.args[0].strip()
    
    try:
        if '-' in input_range:
            # Handle range request
            parts = input_range.split('-')
            prefix = parts[0][:-2] if len(parts[0]) > 2 else ""
            start_num = int(parts[0][-2:]) if len(parts[0]) > 2 else int(parts[0])
            end_num = int(parts[1])
            
            if end_num <= start_num:
                update.message.reply_text("End number must be greater than start number")
                return
            
            if (end_num - start_num) > 100:
                update.message.reply_text("Maximum 100 items at once")
                return
            
            item_ids = [f"{prefix}{i:02d}" for i in range(start_num, end_num + 1)]
            is_bulk = True
        else:
            item_ids = [input_range]
            is_bulk = False
        
        with tempfile.TemporaryDirectory() as temp_dir:
            success_count = 0
            png_files = []
            failed_ids = []
            
            for item_id in item_ids:
                file_name = f"{item_id}_rgb.astc"
                url = base_url + file_name
                astc_path = os.path.join(temp_dir, file_name)
                png_path = os.path.join(temp_dir, f"{item_id}.png")
                
                if not download_astc_file(url, astc_path):
                    failed_ids.append(item_id)
                    continue
                
                if not convert_astc_to_png(astc_path, png_path):
                    failed_ids.append(item_id)
                    continue
                
                png_files.append(png_path)
                success_count += 1
            
            if is_bulk:
                if not png_files:
                    update.message.reply_text("❌ No items were processed successfully")
                    return
                
                # Create zip file
                zip_path = os.path.join(temp_dir, f"{server_name}_{input_range}.zip")
                with zipfile.ZipFile(zip_path, 'w') as zipf:
                    for png_file in png_files:
                        zipf.write(png_file, os.path.basename(png_file))
                
                # Send results
                with open(zip_path, 'rb') as f:
                    update.message.reply_document(
                        document=f,
                        caption=f"✅ {server_name} items {input_range} ({success_count} converted)"
                    )
                
                if failed_ids:
                    formatted_fails = format_failed_ids(failed_ids)
                    fail_message = "❌ FAILED ID'S:\n" + "\n".join(
                        [f"{id}❌" for id in formatted_fails]
                    )
                    update.message.reply_text(fail_message)
            else:
                if png_files:
                    with open(png_files[0], 'rb') as f:
                        update.message.reply_document(
                            document=f,
                            caption=f"✅ {server_name} item {item_ids[0]}"
                        )
                else:
                    update.message.reply_text(f"❌ Failed to process {item_ids[0]}")
    
    except Exception as e:
        update.message.reply_text(f"❌ Error: {str(e)}")

@restricted
def live_command(update: Update, context: CallbackContext) -> None:
    process_item_request(update, context, LIVE_BASE_URL, "Live")

@restricted
def adv_command(update: Update, context: CallbackContext) -> None:
    process_item_request(update, context, ADVANCE_BASE_URL, "Advance")

def main() -> None:
    updater = Updater(BOT_TOKEN)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("live", live_command))
    dispatcher.add_handler(CommandHandler("adv", adv_command))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
