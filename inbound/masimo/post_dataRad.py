import time
import random
import requests 
import datetime
import MasimoRad

API_KEY = 'UHN_SPO2'

API_ENDPOINT = 'http://35.226.41.85:5000/upload_data'
#API_ENDPOINT = 'http://127.0.0.1/upload_data'

device="COM6"
oxi = MasimoRad.Masimo()
oxi.__init__()
if not oxi.setup_device(target=device, is_bluetooth=False):
    raise Exception('Connection attempt unsuccessful.')
oxi.initiate_device()
oxi.send_cmd(oxi.cmd_get_live_data)
timestamp = datetime.datetime.now()
counter = 1
while oxi.process_data():
    read_o2 = oxi.spo2/100
    read_hr = oxi.beat_per_minute
    # data to be sent to api 
    data = {
        'API_KEY':API_KEY,
        'DEV_ID':'Brian Masimo', 
        'DEV_TYPE': 'ToronTek',
        'DEV_MSG': 'Normal',
        'DEV_LOC': 'ER001 Bed#63',
        'RECORD_TIME': datetime.datetime.now(),
        'O2_VAL': read_o2,
        'HR_VAL': read_hr} 
    # Method allowed GET and POST
    # Get for testing connection
    # Post for upload data
    counter += 1
    if counter > 30:
        r = requests.post(url = API_ENDPOINT, data = data)
        #r = requests.get(url=API_ENDPOINT, params={'API_KEY':API_KEY})
        print (r.status_code, r.text)
        counter = 1
    #time.sleep(1)
