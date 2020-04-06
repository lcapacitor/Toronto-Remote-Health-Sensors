from .InboundSource import InboundSource
from queue import Queue
import time
import logging
from .cms50ew import cms50ew # For serial port scanner
from .masimo import MasimoRad
import platform
import serial

ERROR_NO_DATA_VAL = -10

_logger = logging.getLogger(__name__)

class MasimoRadSource(InboundSource):
    def __init__(self, config):
        super(MasimoRadSource, self).__init__(config)
        self.outputs = {
            "spo2": Queue(),
            "hr": Queue(),
            "status": Queue()
        }

    def run(self):
        _logger.info("Starting MasimoRadSource thread")
        self.no_data('Warning/Initializing...', finger='N')

        oxi = None

        while not self.stop_thread:
            if oxi is not None:
                oxi.close_device()

            oxi = MasimoRad.Masimo()

            # Serial port initialization start
            # success = False
            # while not success and not self.stop_thread:
                # TODO: auto serial port detection
            port_location = self.config["location"]
            if port_location == "auto":
                if platform.system() == 'Windows':
                    # Dummy
                    class o():
                        pass
                    scanner = o()
                    scanner.accessible_ports = []
                    for i in range(0, 10):
                        port = 'COM%d' % i
                        try:
                            s = serial.Serial(port)
                            scanner.accessible_ports.append(port)
                            s.close()
                        except serial.SerialException:
                            pass
                elif platform.system() == 'Linux':
                    scanner = cms50ew.DeviceScan(is_bluetooth=False, serial_glob='/dev/ttyUSB[0-9]')
                else:
                    scanner = cms50ew.DeviceScan(is_bluetooth=False)
                if len(scanner.accessible_ports) > 0:
                    _logger.info('%s available serial ports found: %s', len(scanner.accessible_ports), scanner.accessible_ports)
                    port_location = scanner.accessible_ports[0]
                else:
                    _logger.error('No available serial port found')
                    self.no_data('Error/No connected sensor found, '
                                 'try reconnect or reboot system if persists', 
                                  finger='N')
                    time.sleep(0.5) # This needs to be done quickly before device turns itself off
                    continue

            try:
                # It seems success can only be False when bluetooth failed, 
                # otherwise if serial failed it throws Exception
                success = oxi.setup_device(target=port_location, is_bluetooth=False)
            except Exception as e:
                _logger.exception("Cannot initialize MasimoRad on %s", port_location)
                success = False

            # TODO: verify this is working, or maybe another instance needs to be initialized
            # It seems to work
            if not success:
                _logger.error("Cannot initialize MasimoRad on %s", port_location)
                self.no_data('Error/Sensor (%s) connection error, '
                             'try reconnect or reboot system if persists' % port_location, 
                             finger='N')
                oxi.close_device() # Not sure if this is necessary
                time.sleep(3)
                continue # Go to next loop
            else:
                _logger.info("Initialize MasimoRad on %s success", port_location)
            # Serial port initialization end

            # _logger.debug("Entering main MasimoRad data loop")
            try:
                oxi.initiate_device()
                oxi.send_cmd(oxi.cmd_get_live_data)
                
                while not self.stop_thread:
                    # _logger.debug("Entering main MasimoRad process data loop")
                    
                    oxi.process_data()

                    self.outputs["spo2"].put(oxi.spo2)
                    self.outputs["hr"].put(oxi.beat_per_minute)

                    if self.outputs["spo2"] == 0 and self.outputs["hr"] == 0:
                        self.outputs["status"].put("Warning/Finger out")
                    else:
                        self.outputs["status"].put("Normal/Proessing data")

            except Exception as e:
                _logger.exception("Error in MasimoRadSource. Wait for retry.")
                self.no_data('Error/Cannot communicate with sensor, '
                             'try reconnect or reboot system if persists', 'N')
                oxi.close_device()
                time.sleep(3)

            time.sleep(0)

        oxi.close_device()

        _logger.warning('MasimoRadSource terminated')

    def no_data(self, status, finger):
        self.outputs["spo2"].put(ERROR_NO_DATA_VAL)
        self.outputs["hr"].put(ERROR_NO_DATA_VAL)
        self.outputs["status"].put(status)

def main():
    logging.basicConfig(level=logging.DEBUG)

    config = {
        "protocol": "serial-masimorad",
        "location": "COM3",
        "settings": {},
        "tag": "Masimo"
    }

    source = MasimoRadSource(config)
    source.start()

    try:
        while source.is_alive():
            for key, que in source.outputs.items():
                print('%s(n=%d)' % (key, que.qsize()), end=':\t')
                val = None
                while not que.empty():
                    val = que.get()
                print(val, end=',')
                print()
            print()
            time.sleep(1)
    except KeyboardInterrupt:
        source.stop_thread = True
        source.join()

if __name__ == '__main__':
    main()