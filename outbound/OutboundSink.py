from threading import Thread

class OutboundSink(Thread):
    def __init__(self, config):
        super(OutboundSink, self).__init__()
        self.config = config
        self.inputs = {}
        self.stop_thread = False

    def run(self):
        raise NotImplementedError("This method must be implemented in sub-classes")
