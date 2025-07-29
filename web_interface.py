"""
Flask Web Interface for Admin Panel
Provides web-based interface for viewing and replying to messages
"""

import asyncio
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for
from werkzeug.serving import WSGIRequestHandler

logger = logging.getLogger(__name__)

def create_app():
    """Create and configure Flask application"""
    app = Flask(__name__)
    app.secret_key = 'anonymous_bot_secret_key_2025'
    
    # Disable Flask's request logging to reduce noise
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    
    @app.route('/')
    def index():
        """Main dashboard"""
        if not hasattr(app, 'conversation_manager'):
            return "Bot not initialized", 500
        
        summary = app.conversation_manager.get_conversation_summary()
        active_conversations = app.conversation_manager.get_active_conversations()
        
        # Sort conversations by last activity (most recent first)
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
        """View a specific conversation"""
        if not hasattr(app, 'conversation_manager'):
            return "Bot not initialized", 500
        
        conversation = app.conversation_manager.get_conversation(anon_id)
        user_data = app.conversation_manager.anon_to_user.get(anon_id, {})
        
        if not conversation and anon_id not in app.conversation_manager.anon_to_user:
            return "Conversation not found", 404
        
        return render_template('conversations.html', 
                             anon_id=anon_id, 
                             conversation=conversation,
                             user_data=user_data)
    
    @app.route('/send_reply', methods=['POST'])
    def send_reply():
        """Send a reply to a user"""
        if not hasattr(app, 'conversation_manager'):
            return jsonify({'success': False, 'error': 'Bot not initialized'}), 500
        
        anon_id = request.form.get('anon_id')
        message = request.form.get('message')
        
        if not anon_id or not message:
            return jsonify({'success': False, 'error': 'Missing anon_id or message'}), 400
        
        # Get user ID
        user_id = app.conversation_manager.get_user_id(anon_id)
        if not user_id:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        # Get the bot handler from the main thread
        # We need to access the bot instance to send messages
        try:
            # This is a bit hacky, but we need to get the bot instance
            # In a production environment, you might want to use a message queue
            import main
            from bot_handler import TelegramBotHandler
            
            # Find the bot handler instance (this assumes it's stored globally)
            # For a more robust solution, consider using a proper message queue
            success = asyncio.run(send_message_to_user(user_id, message, anon_id))
            
            if success:
                return jsonify({'success': True})
            else:
                return jsonify({'success': False, 'error': 'Failed to send message'}), 500
                
        except Exception as e:
            logger.error(f"Error sending reply: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/conversations')
    def api_conversations():
        """API endpoint for getting conversations data"""
        if not hasattr(app, 'conversation_manager'):
            return jsonify({'error': 'Bot not initialized'}), 500
        
        summary = app.conversation_manager.get_conversation_summary()
        active_conversations = app.conversation_manager.get_active_conversations()
        
        return jsonify({
            'summary': summary,
            'conversations': active_conversations
        })
    
    return app

async def send_message_to_user(user_id: int, message: str, anon_id: str):
    """Helper function to send message to user via bot"""
    # This is a simplified approach - in production, use a proper message queue
    try:
        # We'll store the reply in a global variable that the bot can check
        # This is not ideal but works for this implementation
        if not hasattr(send_message_to_user, 'pending_replies'):
            send_message_to_user.pending_replies = []
        
        send_message_to_user.pending_replies.append({
            'user_id': user_id,
            'message': message,
            'anon_id': anon_id,
            'timestamp': datetime.now()
        })
        
        return True
    except Exception as e:
        logger.error(f"Error queuing message: {e}")
        return False

# Global function to get pending replies (used by bot handler)
def get_pending_replies():
    """Get and clear pending replies"""
    if hasattr(send_message_to_user, 'pending_replies'):
        replies = send_message_to_user.pending_replies.copy()
        send_message_to_user.pending_replies.clear()
        return replies
    return []
