import inbound.RandomSource
import inbound.Cms50ewSource
import inbound.MasimoSource
import outbound.PosmsSink
import outbound.MqttSink
import outbound.StdoutSink
from Connection import Connection
import json
import sys
import argparse
import logging
import time
import signal
import socket
import uuid
import platform

_logger = logging.getLogger(__name__)

INBOUND_CLASS_MAP = {
    'randomgenerator': inbound.RandomSource.RandomSource,
    'serial-cms50ew': inbound.Cms50ewSource.Cms50ewSource,
    'serial-masimorad': inbound.MasimoSource.MasimoRadSource
}

OUTBOUND_CLASS_MAP = {
    'http-post-posms': outbound.PosmsSink.PosmsSink,
    'mqtt': outbound.MqttSink.MqttSink,
    'stdout': outbound.StdoutSink.StdoutSink
}

def getserial():
    '''
    https://raspberrypi.stackexchange.com/a/2087
    '''
    # Extract serial from cpuinfo file
    cpuserial = "0000000000000000"
    try:
        f = open('/proc/cpuinfo','r')
        for line in f:
            if line[0:6]=='Serial':
                cpuserial = line[10:26]
        f.close()
    except:
        cpuserial = "ERROR000000000"
    return cpuserial

def main(argv):
    parser = argparse.ArgumentParser(description='Take data source as inbounds and send to services as outbounds.')
    parser.add_argument('config', help='configuration file (.json)')
    args = parser.parse_args(argv)

    with open(args.config) as f:
        config = json.load(f)

    if "info" in config:
        if config["info"].get("id", "auto") == "auto":
            if platform.system() == 'Windows':
                config["info"]["id"] = socket.gethostname() + '-' + hex(uuid.getnode()) # This changes everytime Raspberry Pi reboots...
            else:
                config["info"]["id"] = socket.gethostname() + '-' + getserial()
        if config["info"].get("location", "auto") == "auto":
            config["info"]["location"] = socket.gethostbyname(socket.gethostname())

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

    # Initialize in and out bound objetcs if they are marked as active
    inbound_objs = {
        inbound_config["tag"] : 
        INBOUND_CLASS_MAP[inbound_config["protocol"]](inbound_config)
        for inbound_config in config.get("inbounds", [])
        if inbound_config["active"]
    }

    outbound_objs = {
        outbound_config["tag"] : 
        OUTBOUND_CLASS_MAP[outbound_config["protocol"]](outbound_config)
        for outbound_config in config.get("outbounds", [])
        if outbound_config["active"]
    }

    # Establish connections: currently only "fan out" is supported
    if "connections" not in config or len(config["connections"]) == 0:
        _logger.error("No connection specified in configuration to establish")
        return
    # TODO: Allow multiple connections - Validate implementation
    connections = []
    for connection_config in config["connections"]:
        sources = [inbound_objs[key] for key in connection_config["inbound"]]
        sinks = [outbound_objs[key] for key in connection_config["outbound"]]
        conn = Connection(connection_config)
        conn.sources = sources
        conn.sinks = sinks
        connections.append(conn)

    # Start connection, source, and sink threads
    for conn in connections:
        conn.start()
    for key, obj in inbound_objs.items():
        obj.start()
    for key, obj in outbound_objs.items():
        obj.device_info = config.get("info", {})
        obj.start()

    # Handle Control-C exit
    # https://stackoverflow.com/a/31464349/6610243
    killed = [False]
    def exit_gracefully(signum, frame):
        _logger.warning("Main program terminating...")
        killed[0] = True
        for conn in connections:
            conn.stop_thread = True
        for key, obj in inbound_objs.items():
            _logger.warning("Terminating %s", obj)
            obj.stop_thread = True
        for key, obj in outbound_objs.items():
            _logger.warning("Terminating %s", obj)
            obj.stop_thread = True

    signal.signal(signal.SIGINT, exit_gracefully)
    signal.signal(signal.SIGTERM, exit_gracefully)

    # Loop main thread to wait for KeyboardInterrupt
    while not killed[0]:
        time.sleep(1e-3)

    for conn in connections:
        conn.join()
    for key, obj in inbound_objs.items():
        obj.join()
    for key, obj in outbound_objs.items():
        obj.join()

    _logger.warning("Main program terminated")

if __name__ == '__main__':
    try:
        main(sys.argv[1:])
    except Exception as e:
        _logger.exception("Main exception: %s", e)
