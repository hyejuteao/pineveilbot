#!/usr/bin/env python3
"""
Main entry point for the Anonymous Telegram Bot
Runs both the Telegram bot and Flask web interface concurrently
"""

import os
import logging
import threading
from bot_handler import TelegramBotHandler
from web_interface import create_app
from conversation_manager import ConversationManager

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def run_flask_app(app, conversation_manager):
    """Run Flask app in a separate thread"""
    app.conversation_manager = conversation_manager
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

def main():
    """Main function to start both bot and web interface"""
    # Get bot token and admin chat ID from environment
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    admin_chat_id = os.getenv('ADMIN_CHAT_ID')
    
    if not bot_token:
        logger.error("TELEGRAM_BOT_TOKEN environment variable is required")
        return
    
    if not admin_chat_id:
        logger.error("ADMIN_CHAT_ID environment variable is required")
        return
    
    try:
        admin_chat_id = int(admin_chat_id)
    except ValueError:
        logger.error("ADMIN_CHAT_ID must be a valid integer")
        return
    
    # Initialize conversation manager
    conversation_manager = ConversationManager()
    
    # Initialize bot handler
    bot_handler = TelegramBotHandler(bot_token, admin_chat_id, conversation_manager)
    
    # Create Flask app
    flask_app = create_app()
    
    # Start Flask app in a separate thread
    flask_thread = threading.Thread(
        target=run_flask_app,
        args=(flask_app, conversation_manager),
        daemon=True
    )
    flask_thread.start()
    
    logger.info("Starting Anonymous Telegram Bot...")
    logger.info("Web interface available at http://0.0.0.0:5000")
    
    # Start the bot (this will block)
    bot_handler.start()

if __name__ == '__main__':
    main()
