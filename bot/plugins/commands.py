class Command:
    EXIT = 'exit'
    EXIT_RE = r'^/exit\b'
    CANCEL = 'cancel'
    CANCEL_RE = r'^/cancel\b'
    CANCEL_OR_DONE = ['cancel', 'done']
    CANCEL_OR_DONE_RE = r'^/(?:cancel|done)\b'
