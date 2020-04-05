from queue import Queue
import time
import logging
from threading import Thread

class Connection(Thread):
    def __init__(self, config):
        super(Connection, self).__init__()
        self.config = config
        self.sources = []
        self._sinks = []
        self.outputs = []
        self.stop_thread = False

    @property
    def sinks(self):
        return self._sinks

    @sinks.setter
    def sinks(self, x):
        self._sinks = x
        self.outputs = [{
            key: Queue()
            for key in self.config["streams"]
        } for _ in self.sinks]
        for o, s in zip(self.outputs, self.sinks):
            s.inputs = o

    def run(self):
        while not self.stop_thread:
            for source in self.sources:
                for key, que in source.outputs.items():
                    while not que.empty():
                        val = que.get()
                        if key in self.config["streams"]:
                            for out in self.outputs:
                                out[key].put(val)
            time.sleep(1.0 / self.config["rate"])
