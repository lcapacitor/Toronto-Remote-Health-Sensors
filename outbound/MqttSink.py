from .OutboundSink import OutboundSink
import time
import paho.mqtt.client as mqtt

class MqttSink(OutboundSink):
    def __init__(self, config):
        super(MqttSink, self).__init__(config)
        self.device_info = {}

    def run(self):
        client = mqtt.Client()
        if self.config["settings"]["tls"]:
            client.tls_set_context()
        client.username_pw_set(self.config["settings"]["username"], 
                               self.config["settings"]["password"])
        client.connect(self.config["location"], 
                       self.config["settings"]["port"], 60)

        while not self.stop_thread:             
            for key, que in self.inputs.items():
                if not que.empty():
                    while not que.empty():
                        val = que.get() # Only sent last value in queue
                    topic = (self.config["settings"]["topic_prefix"] + 
                             self.device_info.get("id", "unknown") + '/' + 
                             key)
                    ret = client.publish(topic, val)
                    print(topic, val, ret)
            time.sleep(1)

        client.disconnect()

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
        "protocol": "mqtt",
        "location": "mqtt.shirunjie.com",
        "settings": {
            "port": 8883,
            "tls": True,
            "topic_prefix": "/mtsinai/001/",
            "username": "mtsinaimonitor",
            "password": "WillyWong"
        },
        "tag": "MQTT"
    }

    source = RandomSource(source_config)
    sink = MqttSink(sink_config)
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
