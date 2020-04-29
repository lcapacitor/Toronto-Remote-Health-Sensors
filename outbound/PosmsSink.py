from .OutboundSink import OutboundSink
import requests
import logging
import time
import datetime
import os

_logger = logging.getLogger(__name__)

ERROR_UNSET = -1

class PosmsSink(OutboundSink):
    def __init__(self, config):
        super(PosmsSink, self).__init__(config)
        self.device_info = {}

    def run(self):
        # TODO: Do not update if no data available
        # TODO: Reuse session
        last_valid_data_time = -999999999

        # Check if API KEY exists
        api_key_path = self.config["settings"]["api_key"]
        if not os.path.isfile(api_key_path):
            _logger.exception("Error in PosmsSink: Invalid API KEY path ({})".format(api_key_path))
        else:
            # Read encrypted API KEY
            with open(api_key_path, 'rb') as file:
                enc_API_KEY = file.read()

            while not self.stop_thread:
                try:
                    data = {
                        'API_KEY': enc_API_KEY.decode("utf-8"),
                        'DEV_ID': self.device_info.get("id", "unknown_id"), 
                        'DEV_TYPE': self.device_info.get("type", "unknown_type"),
                        'DEV_MSG': 'Error/Status unavailable due to recent reconnect, device off, or finger out',
                        'DEV_LOC': self.device_info.get("location", "unknown_location"),
                        'RECORD_TIME': datetime.datetime.now(),
                        'O2_VAL': ERROR_UNSET,
                        'HR_VAL': ERROR_UNSET
                    }

                    for key, que in self.inputs.items():
                        data_key = self.config["settings"]["key_map"][key]
                        # Take the last value
                        while not que.empty():
                            if data_key == 'DEV_MSG':
                                data[data_key] = str(que.get())
                            else:
                                data[data_key] = que.get()

                    if data['O2_VAL'] > 0 and data['HR_VAL'] > 0:
                        last_valid_data_time = time.time()
                    if (data['O2_VAL'] > 0 and data['HR_VAL'] > 0) or (
                        time.time() - last_valid_data_time > self.config["settings"].get("suppress_error", 40)):
                        data['O2_VAL'] /= 100.0
                        post_url = self.config["location"]

                        # Deal with https and http post
                        if post_url.split(':')[0]=='https': # if post to HTTPs
                            if os.path.isfile(self.config["certificate"]):
                                import urllib3  # to disable "Certificate has no 'subjectAltName'" warning
                                urllib3.disable_warnings(urllib3.exceptions.SecurityWarning)
                                r = requests.post(url=post_url, data=data, verify=self.config["certificate"])
                            else:
                                _logger.exception("Error in PosmsSink: Invalid Certificate path ({})".format(self.config["certificate"]))
                        else: # if HTTP
                            r = requests.post(url=self.config["location"], data=data)
                        if r.status_code == 200: 
                            _logger.debug('%s', data)
                            _logger.debug('%s', r)
                            _logger.debug('%s', r.content)
                        else:
                            _logger.warning('%s', data)
                            _logger.warning('%s', r)
                            _logger.warning('%s', r.content)
                    else:
                        _logger.warning('Suprresing error: %s', data)
                except Exception as e:
                    _logger.exception("Error in PosmsSink")

                if not self.stop_thread:
                    time.sleep(1.0 / self.config["settings"]["rate"])

        _logger.warning('PosmsSink terminated')