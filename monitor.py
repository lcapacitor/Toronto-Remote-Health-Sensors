import inbound.RandomSource
import outbound.PosmsSink
import json
import sys
import argparse
import logging
import time
import signal

_logger = logging.getLogger(__name__)

INBOUND_CLASS_MAP = {
    'randomgenerator': inbound.RandomSource.RandomSource
}

OUTBOUND_CLASS_MAP = {
    'http-post-posms': outbound.PosmsSink.PosmsSink
}

def main(argv):
    parser = argparse.ArgumentParser(description='Take data source as inbounds and send to services as outbounds.')
    parser.add_argument('config', help='configuration file (.json)')
    args = parser.parse_args(argv)

    with open(args.config) as f:
        config = json.load(f)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    log_config = config.get("log", {})
    logging.basicConfig(level=log_config["level"].upper(), format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # ch = logging.StreamHandler()
    # ch.setFormatter(formatter)
    # _logger.addHandler(ch)
    if "level" in log_config:
        _logger.setLevel(log_config["level"].upper())
    if "file" in log_config: # https://docs.python.org/3/howto/logging-cookbook.html
        fh = logging.FileHandler(log_config["file"])
        fh.setFormatter(formatter)
        _logger.addHandler(fh)
        
    _logger.info("Configuration parsed")


    inbound_objs = {
        inbound_config["tag"] : 
        INBOUND_CLASS_MAP[inbound_config["protocol"]](inbound_config)
        for inbound_config in config.get("inbounds", [])
    }

    outbound_objs = {
        outbound_config["tag"] : 
        OUTBOUND_CLASS_MAP[outbound_config["protocol"]](outbound_config)
        for outbound_config in config.get("outbounds", [])
    }

    if "connections" not in config or len(config["connections"]) == 0:
        _logger.error("No connection specified in configuration to establish")
        return
    # TODO: Allow multiple connections
    for connection_config in config["connections"]:
        inbound_obj = inbound_objs[connection_config["inbound"]]
        outbound_obj = outbound_objs[connection_config["outbound"]]
        outbound_obj.inputs = inbound_obj.outputs
        outbound_obj.device_info = config.get("info", {})

    for key, obj in inbound_objs.items():
        obj.start()
    for key, obj in outbound_objs.items():
        obj.start()

    # https://stackoverflow.com/a/31464349/6610243
    killed = [False]
    def exit_gracefully(signum, frame):
        _logger.warning("Main program terminating...")
        killed[0] = True
        for key, obj in inbound_objs.items():
            _logger.warning("Terminating %s", obj)
            obj.stop_thread = True
        for key, obj in outbound_objs.items():
            _logger.warning("Terminating %s", obj)
            obj.stop_thread = True
        for key, obj in inbound_objs.items():
            obj.join()
        for key, obj in outbound_objs.items():
            obj.join()

    signal.signal(signal.SIGINT, exit_gracefully)
    signal.signal(signal.SIGTERM, exit_gracefully)

    while not killed[0]:
        time.sleep(1e-3)

    _logger.warning("Main program terminated")

if __name__ == '__main__':
    try:
        main(sys.argv[1:])
    except Exception as e:
        _logger.exception("Main exception: %s", e)
