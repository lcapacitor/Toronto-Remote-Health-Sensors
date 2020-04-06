from .InboundSource import InboundSource
from queue import Queue
import time
import logging
import random

_logger = logging.getLogger(__name__)

class RandomSource(InboundSource):
    def __init__(self, config):
        super(RandomSource, self).__init__(config)
        self.outputs = {
            stream["name"]: Queue() 
            for stream in config["settings"]["randomstreams"]
        }

    def run(self):
        rng = random.Random(self.config["settings"]["seed"])

        time_start = time.time()

        while not self.stop_thread:
            for stream in self.config["settings"]["randomstreams"]:
                que = self.outputs[stream["name"]]
                if (time.time() - time_start) % 20 > 10:
                    que.put(rng.randint(80,100))
                else:
                    que.put(rng.randint(-10,0))
            time.sleep(0.3) # TODO: Implement variable rate

        _logger.warning('RandomSource terminated')

def main():
    config = {
            "protocol": "randomgenerator",
            "location": "auto",
            "settings": {
                "seed": 0,
                "randomstreams": [
                    {
                        "name": "spo2",
                        "rate": 1
                    },
                    {
                        "name": "hr",
                        "rate": 1
                    }
                ]
            },
            "tag": "Local Random Data Generator",
        }
    source = RandomSource(config)
    source.start()
    for i in range(3):
        for key, que in source.outputs.items():
            print(key, end=': ')
            while not que.empty():
                print(que.get(), end=',')
            print()
        time.sleep(1)
    source.stop_thread = True
    source.join()

if __name__ == '__main__':
    main()
