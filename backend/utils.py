import datetime
import time
from functools import wraps

from telegram import ChatAction


def inheritors(class_):
    subclasses = set()
    parents = [class_]
    while parents:
        parent = parents.pop()
        for child in parent.__subclasses__():
            if child not in subclasses:
                subclasses.add(child)
                parents.append(child)
    return subclasses


def timer(func):
    def wrapper(*args, **kwargs):
        t = time.time()
        res = func(*args, **kwargs)
        print("Function '{}', Resolved Time -> {}".format(func.__name__, datetime.timedelta(seconds=time.time() - t)))
        return res

    return wrapper


def send_action(action):
    """Sends `action` while processing func command."""

    def decorator(func):
        @wraps(func)
        def command_func(context, bot, update, *args, **kwargs):
            bot.send_chat_action(chat_id=update.effective_message.chat_id, action=action)
            return func(context, bot, update, *args, **kwargs)

        return command_func

    return decorator


send_typing_action = send_action(ChatAction.TYPING)
send_upload_video_action = send_action(ChatAction.UPLOAD_VIDEO)
send_upload_photo_action = send_action(ChatAction.UPLOAD_PHOTO)
