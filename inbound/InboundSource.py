from threading import Thread

class InboundSource(Thread):
    def __init__(self, config):
        super(InboundSource, self).__init__()
        self.config = config
        self.outputs = {}
        self.stop_thread = False

    def run(self):
        raise NotImplementedError("This method must be implemented in sub-classes")
