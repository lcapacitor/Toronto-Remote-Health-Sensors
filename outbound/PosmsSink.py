from .OutboundSink import OutboundSink
import requests
import logging
import time
import datetime

_logger = logging.getLogger(__name__)

ERROR_UNSET = -1

class PosmsSink(OutboundSink):
    def __init__(self, config):
        super(PosmsSink, self).__init__(config)
        self.device_info = {}

    def run(self):
        # TODO: Do not update if no data available
        # TODO: Reuse session
        while not self.stop_thread:
            try:
                data = {
                    'API_KEY': self.config["settings"]["api_key"],
                    'DEV_ID': self.device_info.get("id", "unknown_id"), 
                    'DEV_TYPE': self.device_info.get("type", "unknown_type"),
                    'DEV_MSG': 'Unset',
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

                r = requests.post(url=self.config["location"], data=data)
                if r.status_code == 200: 
                    _logger.debug('%s', data)
                    _logger.debug('%s', r)
                    _logger.debug('%s', r.content)
                else:
                    _logger.warning('%s', data)
                    _logger.warning('%s', r)
                    _logger.warning('%s', r.content)
            except Exception as e:
                _logger.exception("Error in PosmsSink")

            time.sleep(1.0 / self.config["settings"]["rate"])

        _logger.warning('PosmsSink terminated')