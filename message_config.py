"""
Message Configuration System
Manages editable bot messages with admin controls
"""

import json
import os
import logging

logger = logging.getLogger(__name__)

class MessageConfig:
    def __init__(self):
        self.config_file = "bot_messages.json"
        self.default_messages = {
            "welcome_admin": {
                "text": "🔧 <b>Painel do Administrador</b>\n\nVocê é o administrador do bot. As mensagens dos usuários serão encaminhadas para você aqui.\n\nPara responder a uma mensagem, use a interface web na URL configurada.\n\nComandos:\n/help - Mostrar esta mensagem de ajuda\n/block anon_12345678 - Bloquear um usuário\n/unblock anon_12345678 - Bloquear um usuário\n/editmsg - Editar mensagens do bot\n\n💻 <b>Interface Web:</b> Acesse para ver todas as conversas e gerenciar usuários\n📱 <b>Responder pelo celular:</b> Use o formato 'NomeUsuario: sua resposta'",
                "description": "Mensagem de boas-vindas para o administrador"
            },
            "welcome_user": {
                "text": "🔒 <b>Bot de Mensagens Anônimas</b>\n\nBem-vindo! Este bot permite que você envie mensagens anônimas.\n\nPrimeiro, escolha um nome de exibição que será mostrado no lugar de um ID anônimo.\nEste nome será visível para a pessoa que receber suas mensagens, mas sua identidade real permanece oculta.\n\n📸 <b>Novo:</b> Agora você também pode enviar fotos anonimamente!\n\n<b>Envie-me o nome de exibição desejado:</b>",
                "description": "Mensagem de boas-vindas para novos usuários"
            },
            "welcome_back": {
                "text": "🔒 <b>Bot de Mensagens Anônimas</b>\n\nBem-vindo de volta, <b>{display_name}</b>!\n\nVocê pode enviar mensagens anônimas através deste bot. Suas mensagens serão encaminhadas com seu nome de exibição escolhido.\n\n📸 <b>Novo:</b> Agora você também pode enviar fotos anonimamente!\n\nComandos:\n/help - Mostrar esta mensagem de ajuda\n/changename - Alterar seu nome de exibição",
                "description": "Mensagem de boas-vindas para usuários que retornam"
            },
            "name_prompt": {
                "text": "Por favor, envie-me seu novo nome de exibição:",
                "description": "Prompt para definir nome de exibição"
            },
            "name_too_long": {
                "text": "Nome de exibição muito longo. Por favor, escolha um nome com 50 caracteres ou menos:",
                "description": "Aviso quando nome é muito longo"
            },
            "name_empty": {
                "text": "Nome de exibição não pode estar vazio. Por favor, escolha um nome de exibição:",
                "description": "Aviso quando nome está vazio"
            },
            "name_set_success": {
                "text": "✅ Ótimo! Seu nome de exibição agora é: <b>{display_name}</b>\n\nAgora você pode enviar mensagens anônimas. Elas serão encaminhadas com seu nome de exibição escolhido.\n\nUse /changename a qualquer momento para alterar seu nome de exibição.",
                "description": "Confirmação de nome definido com sucesso"
            },
            "message_sent": {
                "text": "✅ Sua mensagem anônima foi enviada com sucesso!",
                "description": "Confirmação de mensagem enviada"
            },
            "photo_sent": {
                "text": "✅ Sua foto foi enviada anonimamente!",
                "description": "Confirmação de foto enviada"
            },
            "send_error": {
                "text": "❌ Desculpe, houve um erro ao enviar sua mensagem. Tente novamente mais tarde.",
                "description": "Erro ao enviar mensagem"
            },
            "photo_error": {
                "text": "❌ Desculpe, houve um erro ao enviar sua foto. Tente novamente mais tarde.",
                "description": "Erro ao enviar foto"
            },
            "set_name_first": {
                "text": "Por favor, defina seu nome de exibição primeiro usando /start",
                "description": "Aviso para definir nome primeiro"
            },
            "set_name_for_photo": {
                "text": "Por favor, primeiro envie seu nome de exibição como texto.",
                "description": "Aviso para definir nome antes de enviar foto"
            },
            "start_first": {
                "text": "Por favor, use /start primeiro para configurar seu nome de exibição.",
                "description": "Aviso para usar /start primeiro"
            },
            "user_blocked": {
                "text": "✅ Usuário {anon_id} foi bloqueado.",
                "description": "Confirmação de usuário bloqueado"
            },
            "user_unblocked": {
                "text": "✅ Usuário {anon_id} foi desbloqueado.",
                "description": "Confirmação de usuário desbloqueado"
            },
            "reply_sent": {
                "text": "✅ Resposta enviada para {display_name}",
                "description": "Confirmação de resposta enviada"
            },
            "reply_failed": {
                "text": "❌ Falha ao enviar resposta para {identifier}",
                "description": "Erro ao enviar resposta"
            },
            "user_not_found": {
                "text": "❌ Usuário {identifier} não encontrado",
                "description": "Usuário não encontrado para resposta"
            },
            "reply_format_help": {
                "text": "📱 Para responder pelo Telegram, use este formato:\n<code>NomeExibição: Sua mensagem de resposta aqui</code>\nou\n<code>anon_12345678: Sua mensagem de resposta aqui</code>\n\nVocê pode copiar o nome/ID das mensagens que eu encaminho para você.",
                "description": "Ajuda sobre formato de resposta"
            },
            "new_message_notification": {
                "text": "📩 <b>Nova Mensagem Anônima</b>\n\nDe: <b>{display_name}</b> (<code>{anon_id}</code>)\nHorário: {timestamp}\n\n<i>{message}</i>\n\n📱 <b>Responder pelo celular:</b> <code>{display_name}: sua resposta aqui</code>\n💻 Ou use a interface web para responder.",
                "description": "Notificação de nova mensagem para admin"
            },
            "new_photo_notification": {
                "text": "📸 <b>Nova Foto Anônima</b>\n\nDe: <b>{display_name}</b> (<code>{anon_id}</code>)\nHorário: {timestamp}\n\n{caption_text}📱 <b>Responder pelo celular:</b> <code>{display_name}: sua resposta aqui</code>\n💻 Ou use a interface web para responder.",
                "description": "Notificação de nova foto para admin"
            }
        }
        self.load_messages()

    def load_messages(self):
        """Load messages from file or create default"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.messages = json.load(f)
                    # Add any new default messages that don't exist
                    for key, value in self.default_messages.items():
                        if key not in self.messages:
                            self.messages[key] = value
            else:
                self.messages = self.default_messages.copy()

            self.save_messages()
            logger.info("Messages loaded successfully")
        except Exception as e:
            logger.error(f"Error loading messages: {e}")
            self.messages = self.default_messages.copy()

    def save_messages(self):
        """Save messages to file"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.messages, f, ensure_ascii=False, indent=2)
            logger.info("Messages saved successfully")
        except Exception as e:
            logger.error(f"Error saving messages: {e}")

    def get_message(self, key, **kwargs):
        """Get a message with optional formatting"""
        if key not in self.messages:
            logger.warning(f"Message key '{key}' not found")
            return f"Message '{key}' not configured"

        message = self.messages[key]['text']

        # Format message with provided kwargs
        try:
            return message.format(**kwargs)
        except KeyError as e:
            logger.warning(f"Missing format parameter for message '{key}': {e}")
            return message

    def set_message(self, key, text):
        """Set a message text"""
        if key in self.messages:
            self.messages[key]['text'] = text
            self.save_messages()
            return True
        return False

    def list_messages(self):
        """List all available messages"""
        return {k: v['description'] for k, v in self.messages.items()}

    def get_message_info(self, key):
        """Get message info including current text and description"""
        if key in self.messages:
            return self.messages[key]
        return None

    def reset_message(self, key):
        """Reset a message to default"""
        if key in self.default_messages:
            self.messages[key] = self.default_messages[key].copy()
            self.save_messages()
            return True
        return False

    def reset_all_messages(self):
        """Reset all messages to default values"""
        try:
            self.messages = self.default_messages.copy()
            self.save_messages()
            logger.info("All messages reset to default")
            return True
        except Exception as e:
            logger.error(f"Error resetting all messages: {e}")
            return False

    def get_all_message_keys(self):
        """Get all available message keys"""
        return list(self.default_messages.keys())