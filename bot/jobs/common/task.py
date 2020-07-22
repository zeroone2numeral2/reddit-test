class Task:
    def __init__(self):
        self.interrupt_request = False

    def request_interrupt(self):
        self.interrupt_request = True

    def __call__(self, *args, **kwargs):
        raise NotImplementedError('__call__ must be overriden')
