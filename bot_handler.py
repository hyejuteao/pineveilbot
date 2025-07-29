"""
Telegram Bot Handler
Manages incoming messages, forwarding, and bot commands
"""

import logging
import asyncio
from datetime import datetime
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from conversation_manager import ConversationManager

logger = logging.getLogger(__name__)

class TelegramBotHandler:
    def __init__(self, bot_token: str, admin_chat_id: int, conversation_manager: ConversationManager):
        self.bot_token = bot_token
        self.admin_chat_id = admin_chat_id
        self.conversation_manager = conversation_manager
        self.application = None
        self.bot = None
        
    def start(self):
        """Start the Telegram bot"""
        # Create application
        self.application = Application.builder().token(self.bot_token).build()
        self.bot = self.application.bot
        
        # Add handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Start the bot
        logger.info("Bot is starting...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user_id = update.effective_user.id
        
        if user_id == self.admin_chat_id:
            message = (
                "🔧 <b>Admin Panel</b>\n\n"
                "You are the bot administrator. Messages from users will be forwarded to you here.\n\n"
                "To reply to a message, use the web interface at your configured URL.\n\n"
                "Commands:\n"
                "/help - Show this help message"
            )
        else:
            # Register user and get anonymous ID
            anon_id = self.conversation_manager.register_user(user_id, update.effective_user.username)
            message = (
                "🔒 <b>Anonymous Messaging Bot</b>\n\n"
                "Welcome! You can send anonymous messages through this bot.\n\n"
                f"Your anonymous ID: <code>{anon_id}</code>\n\n"
                "Just send me any message and it will be forwarded anonymously.\n\n"
                "Commands:\n"
                "/help - Show this help message"
            )
        
        await update.message.reply_text(message, parse_mode='HTML')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        await self.start_command(update, context)
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming text messages"""
        user_id = update.effective_user.id
        message_text = update.message.text
        
        if user_id == self.admin_chat_id:
            # This is a message from admin - handle it through web interface
            await update.message.reply_text(
                "⚠️ Please use the web interface to reply to user messages.\n"
                "Direct messages here are not forwarded to users."
            )
            return
        
        # This is a message from a regular user
        anon_id = self.conversation_manager.register_user(user_id, update.effective_user.username)
        
        # Store the message
        message_data = {
            'timestamp': datetime.now(),
            'anon_id': anon_id,
            'user_id': user_id,
            'username': update.effective_user.username,
            'message': message_text,
            'direction': 'incoming'
        }
        
        self.conversation_manager.add_message(anon_id, message_data)
        
        # Forward to admin
        admin_message = (
            f"📩 <b>New Anonymous Message</b>\n\n"
            f"From: <code>{anon_id}</code>\n"
            f"Time: {message_data['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"<i>{message_text}</i>\n\n"
            f"💬 Use the web interface to reply to this message."
        )
        
        try:
            await self.bot.send_message(
                chat_id=self.admin_chat_id,
                text=admin_message,
                parse_mode='HTML'
            )
            
            # Confirm to user
            await update.message.reply_text(
                "✅ Your anonymous message has been sent successfully!"
            )
            
        except Exception as e:
            logger.error(f"Failed to forward message to admin: {e}")
            await update.message.reply_text(
                "❌ Sorry, there was an error sending your message. Please try again later."
            )
    
    async def send_reply_to_user(self, user_id: int, message: str, anon_id: str):
        """Send a reply message to a user (called from web interface)"""
        try:
            # Store the reply message
            message_data = {
                'timestamp': datetime.now(),
                'anon_id': anon_id,
                'user_id': user_id,
                'message': message,
                'direction': 'outgoing'
            }
            
            self.conversation_manager.add_message(anon_id, message_data)
            
            # Send to user
            user_message = (
                f"📬 <b>Reply from Administrator</b>\n\n"
                f"<i>{message}</i>"
            )
            
            await self.bot.send_message(
                chat_id=user_id,
                text=user_message,
                parse_mode='HTML'
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send reply to user {user_id}: {e}")
            return False
