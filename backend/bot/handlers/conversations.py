from telegram.ext import ConversationHandler


class BaseConversationHandler(ConversationHandler):
    STATE = None
    MANAGER = None

    def __init__(self, *args, **kwargs):
        super(BaseConversationHandler, self).__init__(
            self.entry_points(), self.states(), self.fallbacks(), *args, **kwargs
        )

    @property
    def states(self):
        raise NotImplementedError

    @property
    def entry_points(self):
        raise NotImplementedError

    @property
    def fallbacks(self):
        raise NotImplementedError

    def exit(self, bot, update):
        return ConversationHandler.END
