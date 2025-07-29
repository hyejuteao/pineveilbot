#!/usr/bin/env python3
"""
Simple Anonymous Telegram Bot
A working version that avoids import conflicts
"""

import os
import logging
import threading
import time
import asyncio
from datetime import datetime
from flask import Flask, render_template, request, jsonify
import json
import hashlib
import requests
from message_config import MessageConfig

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class SimpleConversationManager:
    def __init__(self):
        self.anon_to_user = {}
        self.user_to_anon = {}
        self.conversations = {}
        self.active_conversations = {}
        self.blocked_users = set()  # Store blocked anonymous IDs

    def _generate_anon_id(self, user_id):
        salt = "anonymous_bot_salt_2025"
        hash_input = f"{user_id}_{salt}".encode('utf-8')
        hash_digest = hashlib.md5(hash_input).hexdigest()
        return f"anon_{hash_digest[:8]}"

    def register_user(self, user_id, username=None, display_name=None):
        if user_id in self.user_to_anon:
            # Update display name if provided
            anon_id = self.user_to_anon[user_id]
            if display_name and anon_id in self.anon_to_user:
                self.anon_to_user[anon_id]['display_name'] = display_name
            return anon_id

        anon_id = self._generate_anon_id(user_id)
        user_data = {
            'user_id': user_id,
            'username': username,
            'display_name': display_name,
            'registered_at': datetime.now(),
            'last_activity': datetime.now()
        }

        self.anon_to_user[anon_id] = user_data
        self.user_to_anon[user_id] = anon_id

        if anon_id not in self.conversations:
            self.conversations[anon_id] = []

        logger.info(f"Registered new user: {anon_id} (user_id: {user_id})")
        return anon_id

    def get_display_name(self, anon_id):
        user_data = self.anon_to_user.get(anon_id)
        if user_data and user_data.get('display_name'):
            return user_data['display_name']
        return anon_id

    def get_user_id(self, anon_id):
        user_data = self.anon_to_user.get(anon_id)
        return user_data['user_id'] if user_data else None

    def add_message(self, anon_id, message_data):
        if anon_id not in self.conversations:
            self.conversations[anon_id] = []

        self.conversations[anon_id].append(message_data)

        if anon_id in self.anon_to_user:
            self.anon_to_user[anon_id]['last_activity'] = datetime.now()

        self.active_conversations[anon_id] = {
            'last_message': message_data['message'][:100] + ('...' if len(message_data['message']) > 100 else ''),
            'last_activity': message_data['timestamp'],
            'direction': message_data['direction'],
            'username': self.anon_to_user.get(anon_id, {}).get('username', 'Unknown'),
            'display_name': message_data.get('display_name', self.anon_to_user.get(anon_id, {}).get('display_name', anon_id)),
            'message_count': len(self.conversations[anon_id])
        }

    def get_conversation(self, anon_id):
        return self.conversations.get(anon_id, [])

    def get_active_conversations(self):
        return self.active_conversations

    def get_conversation_summary(self):
        total_conversations = len(self.active_conversations)
        total_messages = sum(len(conv) for conv in self.conversations.values())

        recent_activity = 0
        for conv_data in self.active_conversations.values():
            time_diff = datetime.now() - conv_data['last_activity']
            if time_diff.total_seconds() < 86400:
                recent_activity += 1

        return {
            'total_conversations': total_conversations,
            'total_messages': total_messages,
            'recent_activity': recent_activity,
            'registered_users': len(self.anon_to_user),
            'blocked_users': len(self.blocked_users)
        }

    def block_user(self, anon_id):
        """Block a user by their anonymous ID"""
        self.blocked_users.add(anon_id)
        logger.info(f"Blocked user: {anon_id}")
        return True

    def unblock_user(self, anon_id):
        """Unblock a user by their anonymous ID"""
        self.blocked_users.discard(anon_id)
        logger.info(f"Unblocked user: {anon_id}")
        return True

    def is_user_blocked(self, anon_id):
        """Check if a user is blocked"""
        return anon_id in self.blocked_users

class SimpleTelegramBot:
    def __init__(self, bot_token, admin_chat_id, conversation_manager):
        self.bot_token = bot_token
        self.admin_chat_id = admin_chat_id
        self.conversation_manager = conversation_manager
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.last_update_id = 0
        self.pending_replies = []
        self.waiting_for_name = {}  # Track users setting their display name
        self.admin_typing_for = {}  # Track when admin is typing to specific users
        self.message_config = MessageConfig()  # Initialize message configuration
        self.admin_editing_message = {}  # Track admin editing messages

    def send_typing_action(self, chat_id):
        """Send typing action to show the bot is typing"""
        try:
            response = requests.post(f"{self.base_url}/sendChatAction", {
                'chat_id': chat_id,
                'action': 'typing'
            })
            return response.json().get('ok', False)
        except Exception as e:
            logger.error(f"Error sending typing action: {e}")
            return False

    def send_message(self, chat_id, text, parse_mode='HTML'):
        url = f"{self.base_url}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': parse_mode
        }
        try:
            response = requests.post(url, data=data)
            return response.json().get('ok', False)
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False

    def send_photo(self, chat_id, photo_file_id, caption=None):
        """Send a photo using file_id"""
        url = f"{self.base_url}/sendPhoto"
        data = {
            'chat_id': chat_id,
            'photo': photo_file_id
        }
        if caption:
            data['caption'] = caption

        try:
            response = requests.post(url, data=data)
            return response.json().get('ok', False)
        except Exception as e:
            logger.error(f"Error sending photo: {e}")
            return False

    def get_updates(self):
        url = f"{self.base_url}/getUpdates"
        params = {'offset': self.last_update_id + 1, 'timeout': 30}
        try:
            response = requests.get(url, params=params)
            data = response.json()
            if data.get('ok'):
                return data.get('result', [])
        except Exception as e:
            logger.error(f"Error getting updates: {e}")
        return []

    def handle_update(self, update):
        if 'message' not in update:
            return

        message = update['message']
        user_id = message['from']['id']
        username = message['from'].get('username')
        text = message.get('text', '')
        photo = message.get('photo')

        # Check if this is an admin command
        if user_id == self.admin_chat_id and text.startswith('/block '):
            anon_id = text.replace('/block ', '').strip()
            if self.conversation_manager.block_user(anon_id):
                self.send_message(user_id, self.message_config.get_message('user_blocked', anon_id=anon_id))
            return
        elif user_id == self.admin_chat_id and text.startswith('/unblock '):
            anon_id = text.replace('/unblock ', '').strip()
            if self.conversation_manager.unblock_user(anon_id):
                self.send_message(user_id, self.message_config.get_message('user_unblocked', anon_id=anon_id))
            return
        elif user_id == self.admin_chat_id and text.startswith('/editmsg'):
            self.handle_admin_edit_message(user_id, text)
            return
        elif user_id == self.admin_chat_id and text.startswith('/resetmsg '):
            message_key = text.replace('/resetmsg ', '').strip()
            if self.message_config.reset_message(message_key):
                self.send_message(user_id, f"✅ Mensagem '{message_key}' resetada ao padrão.")
            else:
                self.send_message(user_id, f"❌ Mensagem '{message_key}' não encontrada.")
            return
        elif user_id == self.admin_chat_id and text == '/resetall':
            self.message_config.reset_all_messages()
            self.send_message(user_id, "✅ Todas as mensagens foram resetadas ao padrão.")
            return
        elif user_id == self.admin_chat_id and text == '/webeditor':
            replit_url = os.getenv('REPL_URL', 'http://0.0.0.0:5000')
            message = f"""🌐 <b>Editor Web de Mensagens</b>

🔗 <b>Editor:</b> {replit_url}/message_editor
📱 <b>Dashboard:</b> {replit_url}

💡 <b>Como acessar no Replit:</b>
• Clique na aba "Webview" no topo
• OU procure por "Open in new tab"
• OU use sua URL do Replit que termina em .replit.dev

🚨 <b>IMPORTANTE:</b> NÃO use http://0.0.0.0:5000 diretamente!
Use sempre a URL automática do Replit."""
            self.send_message(user_id, message)
            return

        if text.startswith('/start') or text.startswith('/help'):
            self.handle_start_command(user_id, username)
        elif text.startswith('/changename'):
            if user_id != self.admin_chat_id:
                self.waiting_for_name[user_id] = True
                self.send_message(user_id, self.message_config.get_message('name_prompt'))
        elif photo:
            self.handle_photo_message(user_id, username, photo, text)
        elif text and not text.startswith('/'):
            self.handle_text_message(user_id, username, text)

    def handle_start_command(self, user_id, username):
        if user_id == self.admin_chat_id:
            message = self.message_config.get_message('welcome_admin')
        else:
            anon_id = self.conversation_manager.register_user(user_id, username)
            user_data = self.conversation_manager.anon_to_user.get(anon_id)

            if not user_data or not user_data.get('display_name'):
                # Ask for display name
                self.waiting_for_name[user_id] = True
                message = self.message_config.get_message('welcome_user')
            else:
                display_name = user_data['display_name']
                message = self.message_config.get_message('welcome_back', display_name=display_name)

        self.send_message(user_id, message)

    def handle_photo_message(self, user_id, username, photo, caption=None):
        # Block admin from sending photos (they should use web interface)
        if user_id == self.admin_chat_id:
            return

        anon_id = self.conversation_manager.register_user(user_id, username)

        # Check if user is blocked
        if self.conversation_manager.is_user_blocked(anon_id):
            return  # Silently ignore blocked users

        # Check if waiting for display name
        if user_id in self.waiting_for_name:
            self.send_message(user_id, self.message_config.get_message('set_name_for_photo'))
            return

        # Check if user has display name
        user_data = self.conversation_manager.anon_to_user.get(anon_id)
        if not user_data or not user_data.get('display_name'):
            self.send_message(user_id, self.message_config.get_message('start_first'))
            return

        display_name = user_data['display_name']

        # Get the largest photo size
        largest_photo = max(photo, key=lambda p: p.get('file_size', 0))
        file_id = largest_photo['file_id']

        # Store message
        message_data = {
            'timestamp': datetime.now(),
            'anon_id': anon_id,
            'user_id': user_id,
            'username': username,
            'display_name': display_name,
            'message': '[FOTO]' + (f' - {caption}' if caption else ''),
            'direction': 'incoming',
            'photo_file_id': file_id,
            'caption': caption
        }
        self.conversation_manager.add_message(anon_id, message_data)

        # Forward to admin
        caption_text = f"<i>{caption}</i>\n\n" if caption else ""
        admin_caption = self.message_config.get_message('new_photo_notification',
            display_name=display_name,
            anon_id=anon_id,
            timestamp=message_data['timestamp'].strftime('%d/%m/%Y %H:%M:%S'),
            caption_text=caption_text
        )

        if self.send_photo(self.admin_chat_id, file_id, admin_caption):
            self.send_message(user_id, self.message_config.get_message('photo_sent'))
        else:
            self.send_message(user_id, self.message_config.get_message('photo_error'))

    def handle_admin_edit_message(self, user_id, text):
        """Handle admin message editing commands"""
        message = """🔧 <b>Editor de Mensagens do Bot</b>

✨ <b>Interface Web Disponível!</b>

Para editar as mensagens do bot de forma mais fácil e intuitiva, acesse a interface web:

🌐 <b>URL:</b> http://0.0.0.0:5000/message_editor

📝 <b>Na interface web você pode:</b>
• Ver todas as mensagens organizadas por categoria
• Editar qualquer mensagem com preview em tempo real
• Resetar mensagens individuais ou todas de uma vez
• Interface muito mais fácil de usar!

📱 <b>Comandos rápidos pelo Telegram:</b>
/resetmsg <código> - Resetar mensagem específica
/resetall - Resetar todas as mensagens

💡 <b>Recomendação:</b> Use a interface web para uma experiência muito melhor!"""

        self.send_message(user_id, message)

    def handle_text_message(self, user_id, username, text):
        # Check if user is setting their display name
        if user_id in self.waiting_for_name and user_id != self.admin_chat_id:
            # Validate display name
            if len(text) > 50:
                self.send_message(user_id, self.message_config.get_message('name_too_long'))
                return
            if len(text.strip()) < 1:
                self.send_message(user_id, self.message_config.get_message('name_empty'))
                return

            display_name = text.strip()
            anon_id = self.conversation_manager.register_user(user_id, username, display_name)
            del self.waiting_for_name[user_id]

            self.send_message(user_id, self.message_config.get_message('name_set_success', display_name=display_name))
            return

        if user_id == self.admin_chat_id:
            # Check if this is a reply to a user (format: "anon_12345678: your reply message" or "DisplayName: your reply message")
            if ':' in text:
                parts = text.split(':', 1)
                if len(parts) == 2:
                    identifier = parts[0].strip()
                    reply_message = parts[1].strip()

                    # Try to find user by anon_id first, then by display name
                    target_user_id = None
                    anon_id = None

                    if identifier.startswith('anon_'):
                        # Direct anon_id lookup
                        anon_id = identifier
                        target_user_id = self.conversation_manager.get_user_id(anon_id)
                    else:
                        # Search by display name
                        for anon_id_key, user_data in self.conversation_manager.anon_to_user.items():
                            if user_data.get('display_name') == identifier:
                                anon_id = anon_id_key
                                target_user_id = user_data['user_id']
                                break

                    if target_user_id and anon_id:
                        # Send typing indicator to user while admin is typing
                        self.send_typing_action(target_user_id)
                        if self.send_reply_to_user(target_user_id, reply_message, anon_id):
                            display_name = self.conversation_manager.get_display_name(anon_id)
                            self.send_message(user_id, self.message_config.get_message('reply_sent', display_name=display_name))
                        else:
                            self.send_message(user_id, self.message_config.get_message('reply_failed', identifier=identifier))
                    else:
                        self.send_message(user_id, self.message_config.get_message('user_not_found', identifier=identifier))
                else:
                    self.send_message(user_id, self.message_config.get_message('reply_format_help'))
            else:
                self.send_message(user_id, self.message_config.get_message('reply_format_help'))
            return

        # Check if user has set a display name
        anon_id = self.conversation_manager.register_user(user_id, username)

        # Check if user is blocked
        if self.conversation_manager.is_user_blocked(anon_id):
            return  # Silently ignore blocked users

        user_data = self.conversation_manager.anon_to_user.get(anon_id)

        if not user_data or not user_data.get('display_name'):
            self.send_message(user_id, self.message_config.get_message('set_name_first'))
            return

        display_name = user_data['display_name']

        message_data = {
            'timestamp': datetime.now(),
            'anon_id': anon_id,
            'user_id': user_id,
            'username': username,
            'display_name': display_name,
            'message': text,
            'direction': 'incoming'
        }

        self.conversation_manager.add_message(anon_id, message_data)

        admin_message = self.message_config.get_message('new_message_notification',
            display_name=display_name,
            anon_id=anon_id,
            timestamp=message_data['timestamp'].strftime('%d/%m/%Y %H:%M:%S'),
            message=text
        )

        if self.send_message(self.admin_chat_id, admin_message):
            self.send_message(user_id, self.message_config.get_message('message_sent'))
        else:
            self.send_message(user_id, self.message_config.get_message('send_error'))

    def send_reply_to_user(self, user_id, message, anon_id):
        try:
            message_data = {
                'timestamp': datetime.now(),
                'anon_id': anon_id,
                'user_id': user_id,
                'message': message,
                'direction': 'outgoing'
            }

            self.conversation_manager.add_message(anon_id, message_data)

            user_message = message

            return self.send_message(user_id, user_message)
        except Exception as e:
            logger.error(f"Failed to send reply to user {user_id}: {e}")
            return False

    def run(self):
        logger.info("Starting bot polling...")
        while True:
            try:
                updates = self.get_updates()
                for update in updates:
                    self.last_update_id = update['update_id']
                    self.handle_update(update)
                time.sleep(1)
            except Exception as e:
                logger.error(f"Error in bot loop: {e}")
                time.sleep(5)

    def handle_admin_help(self, user_id):
        """Show admin help message"""
        help_text = self.message_config.get_message('admin_help', {
            'display_name': 'Admin'
        })
        return self.send_message(user_id, help_text)

    def show_all_templates(self, user_id):
        """Show all available message templates"""
        templates = self.message_config.get_all_message_keys()

        message = "📝 <b>Todas as Mensagens Editáveis:</b>\n\n"

        for i, template in enumerate(templates, 1):
            # Convert template key to readable name
            readable_name = template.replace('_', ' ').title()
            message += f"{i}. <code>{template}</code> - {readable_name}\n"

        message += f"\n📋 <b>Total:</b> {len(templates)} mensagens\n\n"
        message += "💡 <b>Como editar:</b>\n"
        message += "• Interface Web: http://0.0.0.0:5000/message_editor\n"
        message += "• Reset uma mensagem: <code>/resetmsg nome_da_mensagem</code>\n"
        message += "• Reset todas: <code>/resetall</code>"

        return self.send_message(user_id, message)

# Global instances
conversation_manager = SimpleConversationManager()
bot = None

# Flask app
app = Flask(__name__)
app.secret_key = 'anonymous_bot_secret_key_2025'

@app.route('/')
def index():
    summary = conversation_manager.get_conversation_summary()
    active_conversations = conversation_manager.get_active_conversations()

    sorted_conversations = dict(sorted(
        active_conversations.items(),
        key=lambda x: x[1]['last_activity'],
        reverse=True
    ))

    return render_template('index.html', 
                         summary=summary, 
                         conversations=sorted_conversations)

@app.route('/conversation/<anon_id>')
def view_conversation(anon_id):
    conversation = conversation_manager.get_conversation(anon_id)
    user_data = conversation_manager.anon_to_user.get(anon_id, {})

    if not conversation and anon_id not in conversation_manager.anon_to_user:
        return "Conversation not found", 404

    return render_template('conversations.html', 
                         anon_id=anon_id, 
                         conversation=conversation,
                         user_data=user_data)

@app.route('/send_reply', methods=['POST'])
def send_reply():
    anon_id = request.form.get('anon_id')
    message = request.form.get('message')

    if not anon_id or not message:
        return jsonify({'success': False, 'error': 'Missing anon_id or message'}), 400

    user_id = conversation_manager.get_user_id(anon_id)
    if not user_id:
        return jsonify({'success': False, 'error': 'User not found'}), 404

    # Send typing indicator before sending reply
    if bot:
        bot.send_typing_action(user_id)

    if bot and bot.send_reply_to_user(user_id, message, anon_id):
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Failed to send message'}), 500

@app.route('/block_user', methods=['POST'])
def block_user():
    anon_id = request.form.get('anon_id')

    if not anon_id:
        return jsonify({'success': False, 'error': 'Missing anon_id'}), 400

    if conversation_manager.block_user(anon_id):
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Failed to block user'}), 500

@app.route('/unblock_user', methods=['POST'])
def unblock_user():
    anon_id = request.form.get('anon_id')

    if not anon_id:
        return jsonify({'success': False, 'error': 'Missing anon_id'}), 400

    if conversation_manager.unblock_user(anon_id):
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Failed to unblock user'}), 500

@app.route('/api/conversations')
def api_conversations():
    summary = conversation_manager.get_conversation_summary()
    active_conversations = conversation_manager.get_active_conversations()

    return jsonify({
        'summary': summary,
        'conversations': active_conversations
    })

@app.route('/message_editor')
def message_editor():
    """Message editor interface"""
    return render_template('message_editor.html')

@app.route('/api/messages')
def api_messages():
    """Get all messages for editing"""
    if bot and hasattr(bot, 'message_config'):
        messages = {}
        for key, data in bot.message_config.messages.items():
            messages[key] = {
                'text': data['text'],
                'description': data['description']
            }
        return jsonify({'success': True, 'messages': messages})
    return jsonify({'success': False, 'error': 'Bot not initialized'})

@app.route('/api/update_message', methods=['POST'])
def api_update_message():
    """Update a specific message"""
    if not bot or not hasattr(bot, 'message_config'):
        return jsonify({'success': False, 'error': 'Bot not initialized'})

    data = request.get_json()
    key = data.get('key')
    text = data.get('text')

    if not key or not text:
        return jsonify({'success': False, 'error': 'Missing key or text'})

    if bot.message_config.set_message(key, text):
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Failed to update message'})

@app.route('/api/reset_message', methods=['POST'])
def api_reset_message():
    """Reset a message to default"""
    if not bot or not hasattr(bot, 'message_config'):
        return jsonify({'success': False, 'error': 'Bot not initialized'})

    data = request.get_json()
    key = data.get('key')

    if not key:
        return jsonify({'success': False, 'error': 'Missing key'})

    if bot.message_config.reset_message(key):
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Failed to reset message'})

@app.route('/api/reset_all_messages', methods=['POST'])
def api_reset_all_messages():
    """Reset all messages to default"""
    if not bot or not hasattr(bot, 'message_config'):
        return jsonify({'success': False, 'error': 'Bot not initialized'})

    if bot.message_config.reset_all_messages():
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Failed to reset messages'})

def run_bot():
    global bot
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    admin_chat_id = os.getenv('ADMIN_CHAT_ID')

    if admin_chat_id:
        admin_chat_id = int(admin_chat_id)

    bot = SimpleTelegramBot(bot_token, admin_chat_id, conversation_manager)
    bot.run()

def run_flask():
    # Start web interface
    port = int(os.getenv('PORT', 5000))
    logger.info(f"Web interface available at http://0.0.0.0:{port}")

    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

def main():
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

    # Start bot in a separate thread
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()

    logger.info("Starting Anonymous Telegram Bot...")
    logger.info("Web interface available at http://0.0.0.0:5000")

    # Start Flask app (this will block)
    run_flask()

if __name__ == '__main__':
    main()