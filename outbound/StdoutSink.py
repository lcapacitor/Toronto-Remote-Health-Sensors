from .OutboundSink import OutboundSink
import time

class StdoutSink(OutboundSink):
    def run(self):
        while not self.stop_thread:             
            for key, que in self.inputs.items():
                print(key, end=': ')
                while not que.empty():
                    print(que.get(), end=',')
                print()
            time.sleep(1)

def main():
    from inbound.RandomSource import RandomSource
    source_config = {
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
    sink_config = {
        "tag": "Print to Stdout"
    }

    source = RandomSource(source_config)
    sink = StdoutSink(sink_config)
    sink.inputs = source.outputs
    source.start()
    sink.start()
    time.sleep(5)
    source.stop_thread = True
    sink.stop_thread = True
    source.join()
    sink.join()

if __name__ == '__main__':
    main()
