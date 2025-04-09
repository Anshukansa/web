import os
import logging
import hashlib
import hmac
import time
from urllib.parse import urlencode

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', 'YOUR_BOT_TOKEN')
WEBAPP_URL = os.environ.get('WEBAPP_URL', 'http://localhost:5000')
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')  # Must match your Flask app's secret key

def generate_secure_link(user_id, user_name):
    """Generate a secure link with encrypted parameters."""
    # Prepare data to include in the URL
    data = {
        'user_id': user_id,
        'user_name': user_name,
        'timestamp': int(time.time())
    }
    
    # Create a query string from the data
    query_string = urlencode(data)
    
    # Generate HMAC signature for security
    signature = hmac.new(
        SECRET_KEY.encode(),
        query_string.encode(),
        hashlib.sha256
    ).hexdigest()
    
    # Add signature to data
    data['signature'] = signature
    
    # Create final URL with all parameters
    url = f"{WEBAPP_URL}/telegram-form?{urlencode(data)}"
    
    return url

def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    user_id = user.id
    user_name = f"{user.first_name} {user.last_name}" if user.last_name else user.first_name
    
    # Generate secure link for this specific Telegram user
    secure_link = generate_secure_link(user_id, user_name)
    
    # Create inline keyboard with button to access form
    keyboard = [
        [InlineKeyboardButton("🔒 Manage iPhone Preferences", url=secure_link)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send welcome message with button
    update.message.reply_html(
        f"Hi {user.mention_html()}! Welcome to iPhone Flippers bot.\n\n"
        f"Click the button below to access your iPhone preferences form:",
        reply_markup=reply_markup
    )

def check_preferences(update: Update, context: CallbackContext) -> None:
    """Provide a link to check user's current preferences"""
    user = update.effective_user
    user_id = user.id
    user_name = f"{user.first_name} {user.last_name}" if user.last_name else user.first_name
    
    # Generate secure link for this user
    secure_link = generate_secure_link(user_id, user_name)
    
    # Create inline keyboard with button
    keyboard = [
        [InlineKeyboardButton("🔒 View/Update Preferences", url=secure_link)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(
        "Click the button below to view or update your iPhone preferences:",
        reply_markup=reply_markup
    )

def help_command(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /help is issued."""
    update.message.reply_text(
        "iPhone Flippers Bot Help:\n\n"
        "/start - Get access to your iPhone preferences\n"
        "/check - Check your current preferences\n"
        "/help - Show this help message"
    )

def main() -> None:
    """Start the bot."""
    # Create the Updater and pass it your bot's token
    updater = Updater(BOT_TOKEN)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # Register command handlers
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("check", check_preferences))

    # Start the Bot
    updater.start_polling()
    logger.info("Bot started polling")

    # Run the bot until you press Ctrl-C
    updater.idle()

if __name__ == '__main__':
    main()