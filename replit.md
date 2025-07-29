# Anonymous Telegram Bot

## Overview

This is an anonymous messaging Telegram bot that allows users to send messages to an admin while maintaining their anonymity through generated anonymous IDs. The system consists of a Telegram bot handler and a Flask web interface for the admin to view and respond to messages.

## User Preferences

Preferred communication style: Simple, everyday language.

## Recent Changes (July 29, 2025)

- Enhanced custom display name system where users choose personalized names instead of "anon_12345678"
- Added /changename command for users to update their display names anytime
- Updated web interface to prominently display chosen display names instead of anonymous IDs
- Implemented flexible reply system supporting both display names and anon IDs for admin responses
- Removed "Reply from Administrator" headers - users now receive plain messages only
- Added direct phone reply capability from Telegram admin chat
- **COMPLETED: Full Brazilian Portuguese translation** - All bot messages, commands, and web interface now in Portuguese
- **NEW: User blocking/unblocking system** - Admins can block problematic users via /block and /unblock commands or web interface
- **NEW: Typing indicators** - Users see "typing..." status when admin is responding to their messages
- **NEW: Photo support** - Users can now send photos anonymously with optional captions
- Bot successfully running on port 5004 with all enhanced features integrated and tested

## System Architecture

The application follows a modular architecture with clear separation of concerns:

1. **Bot Handler Layer** - Manages Telegram bot interactions and message processing
2. **Conversation Management Layer** - Handles user anonymization and message storage
3. **Web Interface Layer** - Provides admin dashboard for viewing and responding to messages
4. **Configuration Layer** - Centralizes environment variables and settings

The system uses in-memory storage for simplicity and runs both the Telegram bot and Flask web interface concurrently in separate threads.

## Key Components

### TelegramBotHandler (bot_handler.py)
- **Purpose**: Manages incoming Telegram messages and bot commands
- **Key Features**: 
  - Handles /start and /help commands
  - Forwards user messages to admin
  - Processes message replies from admin back to users
- **Architecture Decision**: Uses python-telegram-bot library for robust Telegram API integration

### ConversationManager (conversation_manager.py)
- **Purpose**: Manages user anonymization and conversation tracking
- **Key Features**:
  - Generates consistent anonymous IDs using MD5 hashing
  - Maps real user IDs to anonymous IDs
  - Stores conversation history in memory
  - Tracks active conversations and user metadata
- **Architecture Decision**: Uses MD5 hashing with salt for anonymous ID generation to ensure consistency while maintaining anonymity

### Flask Web Interface (web_interface.py)
- **Purpose**: Provides admin dashboard for message management
- **Key Features**:
  - Dashboard with conversation summary
  - Individual conversation views
  - Message reply functionality
  - Real-time conversation updates
- **Architecture Decision**: Chose Flask for simplicity and ease of integration with the bot system

### Configuration Management (config.py)
- **Purpose**: Centralizes all configuration settings
- **Key Features**:
  - Environment variable management
  - Validation of required settings
  - Default values for optional settings
  - Separate bot and web server ports
- **Architecture Decision**: Class-based configuration for better organization and validation

## Data Flow

1. **User Message Flow**:
   - User sends message to Telegram bot
   - Bot handler receives message and generates/retrieves anonymous ID
   - Message is stored in conversation manager
   - Message is forwarded to admin chat
   - Admin can view message in web interface

2. **Admin Reply Flow**:
   - Admin uses web interface to reply to anonymous user
   - Reply is sent through bot to original user
   - Conversation history is updated

3. **Anonymous ID Generation**:
   - MD5 hash of user_id + salt generates consistent anonymous ID
   - Anonymous ID maps back to real user for message delivery
   - No user data is permanently stored

## External Dependencies

### Core Libraries
- **python-telegram-bot**: Telegram Bot API integration
- **Flask**: Web interface framework
- **hashlib**: Anonymous ID generation
- **threading**: Concurrent bot and web server execution

### Frontend Dependencies
- **Bootstrap 5.1.3**: UI framework for responsive design
- **Feather Icons**: Icon library for consistent UI elements

### Runtime Dependencies
- Python 3.7+ (async/await support required)
- Environment variables for bot token and admin chat ID

## Deployment Strategy

### Environment Setup
- **Required Environment Variables**:
  - `TELEGRAM_BOT_TOKEN`: Bot token from BotFather
  - `ADMIN_CHAT_ID`: Telegram chat ID for admin
- **Optional Environment Variables**:
  - `SECRET_KEY`: Flask session security
  - `DEBUG`: Enable debug mode
  - `LOG_LEVEL`: Logging verbosity

### Port Configuration
- **Bot Handler**: Runs on port 8000 (configurable)
- **Web Interface**: Runs on port 5000 (configurable)
- **Host**: Configured for 0.0.0.0 to accept external connections

### Concurrency Model
- Main thread runs Telegram bot with polling
- Separate thread runs Flask web server
- Shared ConversationManager instance between both services
- No database required - uses in-memory storage

### Scalability Considerations
- Current design is single-instance only due to in-memory storage
- Memory limits set for conversations (1000 max) and message length (4096 chars)
- Auto-cleanup configured for 7-day conversation timeout
- For production scale, would need database backend and session management

### Security Features
- Anonymous ID generation prevents user identification
- Salt-based hashing for consistent but secure anonymization
- Admin-only access to conversation data
- No persistent storage of sensitive user information