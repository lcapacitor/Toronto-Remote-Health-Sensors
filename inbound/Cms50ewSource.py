from .InboundSource import InboundSource
from queue import Queue
import time
import logging
import random
from .cms50ew import cms50ew
import platform
import serial

ERROR_NO_DATA_VAL = -10

_logger = logging.getLogger(__name__)

class Cms50ewSource(InboundSource):
    def __init__(self, config):
        super(Cms50ewSource, self).__init__(config)
        self.outputs = {
            "spo2": Queue(),
            "hr": Queue(),
            "status": Queue()
        }

    def run(self):
        _logger.info("Starting CMS50EWSource thread")
        self.no_data('Warning/Initializing...', finger='N')

        oxi = None

        while not self.stop_thread:
            # The CMS50E comes with an active cable that also acts as a serial UART to USB converter
            # Therefore unplugging the USB-A end and the USB-mini end has different behaviors
            # When the USB-A end is unplugged, the serial port disappearts on system
            # When the USB-mini end is unplugged, the serial port still exists but (presumably) has no data
            # Also, when the CMS50E does not have an active connection or is on battery 
            # and dies not detect finger, it turns itself off 

            if oxi is not None:
                oxi.close_device()

            oxi = cms50ew.CMS50EW()

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
                _logger.exception("Cannot initialize CMS50EW on %s", port_location)
                success = False

            # TODO: verify this is working, or maybe another instance needs to be initialized
            # It seems to work
            if not success:
                _logger.error("Cannot initialize CMS50EW on %s", port_location)
                self.no_data('Error/Sensor (%s) connection error, '
                             'try reconnect or reboot system if persists' % port_location, 
                             finger='N')
                oxi.close_device() # Not sure if this is necessary
                time.sleep(3)
                continue # Go to next loop
            else:
                _logger.info("Initialize CMS50EW on %s success", port_location)
            # Serial port initialization end

            oxi.old_pulse_rate = -1
            oxi.old_spo2 = -1
            oxi.old_status = 'No status'

            oxi.starttime = time.time()
            # _logger.debug("Entering main CMS50EW data loop")
            try:
                oxi.initiate_device()
                oxi.send_cmd(oxi.cmd_get_live_data)

                # update_live_data()
                finger_out = False
                low_signal_quality = False
                # global stdscr_height
                counter = 0
                
                while not self.stop_thread:
                    # _logger.debug("Entering main CMS50EW process data loop")
                    data = oxi.process_data()
                    finger = data[0]
                    pulse_rate = data[1]
                    spo2 = data[2]
                    
                    # Store live session data in object once every second
                    oxi.timer = time.time()
                    delta_time = oxi.timer - oxi.starttime
                    if not oxi.stored_data: # Might still be empty
                        if delta_time > 1:
                            oxi.stored_data.append([round(delta_time), finger, pulse_rate, spo2])
                    else:
                        if delta_time - oxi.stored_data[-1][0] > 1: # Save one data set per sec
                            oxi.stored_data.append([round(delta_time), finger, pulse_rate, spo2])
                        
                    if finger == 'Y':
                        # The counter > n condition serves to suppress hiccups where
                        # the oximeter reports "Finger out" when it isn't.
                        if not finger_out and counter > 10:
                            self.no_data('Error/Finger out', finger)
                            finger_out = True
                            low_signal_quality = False
                            counter = 0
                        elif not finger_out and counter < 11:
                            counter += 1
                    elif (pulse_rate == 0) or (spo2 == 0):
                            self.no_data('Warning/Low signal or initializing', finger)
                            finger_out = False
                            low_signal_quality = True
                    else:
                        self.data_update('Normal/Processing data', finger, pulse_rate, spo2)
                        finger_out = False
                        low_signal_quality = False



            except Exception as e:
                _logger.exception("Error in Cms50ewSource. Wait for retry.")
                self.no_data('Error/Cannot communicate with sensor, '
                             'try reconnect or reboot system if persists', 'N')
                oxi.close_device()
                time.sleep(3)

            # for stream in self.config["settings"]["randomstreams"]:
            #     que = self.outputs[stream["name"]]
            #     que.put(rng.randint(80,100))
            time.sleep(0.3) # TODO: Implement variable rate

        oxi.close_device()

        _logger.warning('CMS50EWSource terminated')

    def no_data(self, status, finger):
        self.outputs["spo2"].put(ERROR_NO_DATA_VAL)
        self.outputs["hr"].put(ERROR_NO_DATA_VAL)
        self.outputs["status"].put(status)

    def data_update(self, status, finger, pulse_rate, spo2):
        self.outputs["spo2"].put(spo2)
        self.outputs["hr"].put(pulse_rate)
        self.outputs["status"].put(status)

def main():
    logging.basicConfig(level=logging.DEBUG)

    config = {
        "protocol": "serial-cms50ew",
        "location": "COM3",
        "settings": {},
        "tag": "ToronTek"
    }

    source = Cms50ewSource(config)
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