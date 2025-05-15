import os
import subprocess
import tempfile
import requests
import logging
import json
import base64
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram.ext import Application

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = "7459415423:AAEOwutnGXxLXsuKhQCdGIHmuyILwQIXLEE"
ALLOWED_GROUP_ID = -1002699301861
LIVE_BASE_URL = "https://dl.dir.freefiremobile.com/live/ABHotUpdates/IconCDN/android/"
ADVANCE_BASE_URL = "https://dl.dir.freefiremobile.com/advance/ABHotUpdates/IconCDN/android/"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message"""
    if update.message.chat_id != ALLOWED_GROUP_ID:
        await update.message.reply_text("❌ This bot is restricted to a specific group.")
        return
    await update.message.reply_text(
        "🔥 Free Fire ASTC to PNG Converter 🔥\n"
        "Commands:\n"
        "/live <id> - Live server item\n"
        "/adv <id> - Advance server item"
    )

async def convert_astc_to_png(astc_data: bytes) -> bytes:
    """Convert ASTC to PNG using the binary"""
    try:
        if not os.path.exists("./astcenc"):
            logger.error("astcenc binary not found")
            raise FileNotFoundError("astcenc binary missing")
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = os.path.join(tmp_dir, "input.astc")
            output_path = os.path.join(tmp_dir, "output.png")
            
            with open(input_path, 'wb') as f:
                f.write(astc_data)
            
            result = subprocess.run(
                ["./astcenc", "-d", input_path, output_path, "8x8", "-fast"],
                check=True,
                timeout=15,
                capture_output=True
            )
            logger.info(f"astcenc output: {result.stdout.decode()}")
            
            with open(output_path, 'rb') as f:
                return f.read()
    except FileNotFoundError as e:
        logger.error(f"ASTCENC binary error: {str(e)}")
        raise
    except subprocess.CalledProcessError as e:
        logger.error(f"ASTCENC failed: {e.stderr.decode()}")
        raise Exception(f"Conversion failed: {e.stderr.decode()}")
    except subprocess.TimeoutExpired:
        logger.error("ASTCENC timed out")
        raise Exception("Conversion timed out")
    except Exception as e:
        logger.error(f"Unexpected error in conversion: {str(e)}")
        raise

async def process_single_item(update: Update, base_url: str, server_name: str, item_id: str):
    """Process single item conversion"""
    try:
        # Download ASTC file
        response = requests.get(f"{base_url}{item_id}_rgb.astc", timeout=10)
        response.raise_for_status()
        
        # Convert to PNG
        png_data = await convert_astc_to_png(response.content)
        
        # Send result
        await update.message.reply_photo(
            photo=png_data,
            caption=f"{server_name} {item_id}"
        )
    except requests.exceptions.RequestException as e:
        logger.error(f"Download failed for {item_id}: {str(e)}")
        await update.message.reply_text(f"❌ Failed to download {item_id}")
    except Exception as e:
        logger.error(f"Error processing {item_id}: {str(e)}")
        await update.message.reply_text(f"⚠️ Error: {str(e)}")

async def live(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /live command"""
    if update.message.chat_id != ALLOWED_GROUP_ID:
        await update.message.reply_text("❌ This bot is restricted to a specific group.")
        return
    if not context.args:
        await update.message.reply_text("Please provide item ID")
        return
    await process_single_item(update, LIVE_BASE_URL, "Live", context.args[0])

async def adv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /adv command"""
    if update.message.chat_id != ALLOWED_GROUP_ID:
        await update.message.reply_text("❌ This bot is restricted to a specific group.")
        return
    if not context.args:
        await update.message.reply_text("Please provide item ID")
        return
    await process_single_item(update, ADVANCE_BASE_URL, "Advance", context.args[0])

def setup_handlers(application: Application):
    """Configure command handlers"""
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("live", live))
    application.add_handler(CommandHandler("adv", adv))

async def handle_update(update: dict, application: Application):
    """Process Telegram update"""
    try:
        await application.initialize()
        await application.process_update(Update.de_json(update, application.bot))
        await application.shutdown()
    except Exception as e:
        logger.error(f"Error processing update: {str(e)}")
        raise

def handler(event, context):
    """Vercel serverless function handler"""
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Initialize Telegram application
        application = ApplicationBuilder().token(BOT_TOKEN).build()
        setup_handlers(application)
        
        # Handle HTTP method
        method = event.get("httpMethod", "GET")
        path = event.get("path", "/")
        
        logger.info(f"Handling {method} request to {path}")
        
        if method == "GET":
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({
                    "status": "Bot is running",
                    "path": path,
                    "astcenc_exists": os.path.exists("./astcenc")
                })
            }
        
        if method == "POST" and path == "/":
            body = event.get("body", "")
            if not body:
                logger.error("Empty POST body")
                return {
                    "statusCode": 400,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": "Empty POST body"})
                }
            
            # Handle base64-encoded body (Vercel may encode POST bodies)
            try:
                if event.get("isBase64Encoded", False):
                    body = base64.b64decode(body).decode("utf-8")
                update = json.loads(body)
            except (json.JSONDecodeError, base64.binascii.Error) as e:
                logger.error(f"Invalid JSON or base64: {str(e)}")
                return {
                    "statusCode": 400,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": "Invalid JSON or base64"})
                }
            
            # Process Telegram update
            application.run_async(handle_update(update, application))
            
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"status": "success"})
            }
        
        logger.warning(f"Unhandled request: {method} {path}")
        return {
            "statusCode": 404,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Not found"})
        }
    except Exception as e:
        logger.error(f"Handler error: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(e)})
        }
