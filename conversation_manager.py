"""
Conversation Manager
Handles anonymous ID generation, user mapping, and message storage
"""

import hashlib
import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class ConversationManager:
    def __init__(self):
        # Map anonymous IDs to user data
        self.anon_to_user: Dict[str, dict] = {}
        # Map user IDs to anonymous IDs
        self.user_to_anon: Dict[int, str] = {}
        # Store conversation messages by anonymous ID
        self.conversations: Dict[str, List[dict]] = {}
        # Track active conversations
        self.active_conversations: Dict[str, dict] = {}
        
    def _generate_anon_id(self, user_id: int) -> str:
        """Generate a consistent anonymous ID for a user"""
        # Use a hash of user_id with a salt for anonymity
        salt = "anonymous_bot_salt_2025"
        hash_input = f"{user_id}_{salt}".encode('utf-8')
        hash_digest = hashlib.md5(hash_input).hexdigest()
        # Return first 8 characters for readability
        return f"anon_{hash_digest[:8]}"
    
    def register_user(self, user_id: int, username: Optional[str] = None) -> str:
        """Register a user and return their anonymous ID"""
        # Check if user already has an anonymous ID
        if user_id in self.user_to_anon:
            return self.user_to_anon[user_id]
        
        # Generate new anonymous ID
        anon_id = self._generate_anon_id(user_id)
        
        # Store mappings
        user_data = {
            'user_id': user_id,
            'username': username,
            'registered_at': datetime.now(),
            'last_activity': datetime.now()
        }
        
        self.anon_to_user[anon_id] = user_data
        self.user_to_anon[user_id] = anon_id
        
        # Initialize conversation
        if anon_id not in self.conversations:
            self.conversations[anon_id] = []
        
        logger.info(f"Registered new user: {anon_id} (user_id: {user_id})")
        return anon_id
    
    def get_user_id(self, anon_id: str) -> Optional[int]:
        """Get user ID from anonymous ID"""
        user_data = self.anon_to_user.get(anon_id)
        return user_data['user_id'] if user_data else None
    
    def get_anon_id(self, user_id: int) -> Optional[str]:
        """Get anonymous ID from user ID"""
        return self.user_to_anon.get(user_id)
    
    def add_message(self, anon_id: str, message_data: dict):
        """Add a message to the conversation"""
        if anon_id not in self.conversations:
            self.conversations[anon_id] = []
        
        self.conversations[anon_id].append(message_data)
        
        # Update last activity
        if anon_id in self.anon_to_user:
            self.anon_to_user[anon_id]['last_activity'] = datetime.now()
        
        # Update active conversations
        self.active_conversations[anon_id] = {
            'last_message': message_data['message'][:100] + ('...' if len(message_data['message']) > 100 else ''),
            'last_activity': message_data['timestamp'],
            'direction': message_data['direction'],
            'username': self.anon_to_user.get(anon_id, {}).get('username', 'Unknown'),
            'message_count': len(self.conversations[anon_id])
        }
        
        logger.info(f"Added message to conversation {anon_id}: {message_data['direction']}")
    
    def get_conversation(self, anon_id: str) -> List[dict]:
        """Get all messages in a conversation"""
        return self.conversations.get(anon_id, [])
    
    def get_active_conversations(self) -> Dict[str, dict]:
        """Get all active conversations with summary info"""
        return self.active_conversations
    
    def get_conversation_summary(self) -> dict:
        """Get a summary of all conversations"""
        total_conversations = len(self.active_conversations)
        total_messages = sum(len(conv) for conv in self.conversations.values())
        
        # Recent activity (last 24 hours)
        recent_activity = 0
        for conv_data in self.active_conversations.values():
            time_diff = datetime.now() - conv_data['last_activity']
            if time_diff.total_seconds() < 86400:  # 24 hours
                recent_activity += 1
        
        return {
            'total_conversations': total_conversations,
            'total_messages': total_messages,
            'recent_activity': recent_activity,
            'registered_users': len(self.anon_to_user)
        }
