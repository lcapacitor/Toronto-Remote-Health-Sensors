from .InboundSource import InboundSource
from queue import Queue
import time
import logging
import random
from .cms50ew import cms50ew

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

        oxi = cms50ew.CMS50EW()
        self.oxi = oxi

        success = False
        while not success and not self.stop_thread:
            # TODO: auto serial port detection
            port_location = self.config["location"]
            try:
                success = oxi.setup_device(target=port_location, is_bluetooth=False)
            except Exception as e:
                _logger.exception("Cannot initialize CMS50EW on %s", port_location)
                success = False
            # TODO: verify this is working, or maybe another instance needs to be initialized
            if not success:
                _logger.error("Cannot initialize CMS50EW on %s", port_location)
                self.no_data('Error/Sensor (%s) connection error, '
                             'try reconnect or reboot system if keep failing' % port_location, 
                             finger='N')
                time.sleep(3)
            else:
                _logger.info("Initialize CMS50EW on %s success", port_location)

        oxi.old_pulse_rate = -1
        oxi.old_spo2 = -1
        oxi.old_status = 'No status'

        oxi.starttime = time.time()

        while not self.stop_thread:
            oxi.initiate_device()
            oxi.send_cmd(oxi.cmd_get_live_data)

            try:
                # update_live_data()
                finger_out = False
                low_signal_quality = False
                # global stdscr_height
                counter = 0
                
                while not self.stop_thread:
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



            except (TypeError, bluetooth.btcommon.BluetoothError) as e:
                _logger.exception("Error in Cms50ewSource")

            # for stream in self.config["settings"]["randomstreams"]:
            #     que = self.outputs[stream["name"]]
            #     que.put(rng.randint(80,100))
            time.sleep(0.3) # TODO: Implement variable rate

        _logger.warning('CMS50EWSource terminated')

    def no_data(self, status, finger):
        self.outputs["spo2"].put(ERROR_NO_DATA_VAL)
        self.outputs["hr"].put(ERROR_NO_DATA_VAL)
        self.outputs["status"].put(status)

    def data_update(self, status, finger, pulse_rate, spo2):
        self.outputs["spo2"].put(spo2)
        self.outputs["hr"].put(pulse_rate)
        self.outputs["status"].put(status)

