from ..handlers import conversations, commands, messages, callbacks
from backend.utils import inheritors

all_commands = [command for command in inheritors(commands.BaseCommandHandler)]
all_messages = [message for message in inheritors(messages.BaseMessageHandler)]
all_conversations = [conversation for conversation in inheritors(conversations.BaseConversationHandler)]
all_callback_queries = [callback for callback in inheritors(callbacks.BaseCallbackQueryHandler)]
