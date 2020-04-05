from .OutboundSink import OutboundSink
import time
import paho.mqtt.client as mqtt
import logging
import datetime

_logger = logging.getLogger(__name__)

class MqttSink(OutboundSink):
    def __init__(self, config):
        super(MqttSink, self).__init__(config)
        self.device_info = {}

    def run(self):
        while not self.stop_thread:
            client = mqtt.Client()
            try:
                if self.config["settings"]["tls"]:
                    client.tls_set_context()
                client.username_pw_set(self.config["settings"]["username"], 
                                       self.config["settings"]["password"])
                client.connect(self.config["location"], 
                               self.config["settings"]["port"], 60)

                for key, val in self.device_info.items():
                    topic = (self.config["settings"]["topic_prefix"] + 
                             self.device_info.get("id", "unknown") + '/' + 
                             key)
                    ret = client.publish(topic, val)
                    _logger.debug("Published: %s: %s -> %s", topic, val, ret)

                while not self.stop_thread:

                    topic = (self.config["settings"]["topic_prefix"] + 
                             self.device_info.get("id", "unknown") + '/ping')
                    ret = client.publish(topic, datetime.datetime.now().isoformat())

                    for key, que in self.inputs.items():
                        val = -1
                        if not que.empty():
                            while not que.empty():
                                val = que.get() # Only sent last value in queue
                            topic = (self.config["settings"]["topic_prefix"] + 
                                     self.device_info.get("id", "unknown") + '/' + 
                                     key)
                            ret = client.publish(topic, val)
                            _logger.debug("Published: %s: %s -> %s", topic, val, ret)
                    time.sleep(1)

                client.disconnect()
            except Exception as e:
                _logger.exception("MQTT unexpected exception")

                topic = (self.config["settings"]["topic_prefix"] + 
                         self.device_info.get("id", "unknown") + '/error')
                val = str(e)
                ret = client.publish(topic, val)
                _logger.debug("Published: %s: %s -> %s", topic, val, ret)

                topic = (self.config["settings"]["topic_prefix"] + 
                         self.device_info.get("id", "unknown") + '/status')
                val = "Error/MQTT error state"
                ret = client.publish(topic, val)
                _logger.debug("Published: %s: %s -> %s", topic, val, ret)

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
