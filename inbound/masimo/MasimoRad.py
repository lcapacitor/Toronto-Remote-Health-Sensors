#!/usr/bin/env python3

import serial
import glob
import datetime
import csv

class Masimo():
    """Class to instantiate a CMS50EW pulse oximeter."""
    def __init__(self):
        self.pulse_xdata, self.pulse_ydata, self.spo2_xdata, self.spo2_ydata, self.finger_data = [[0], [0], [0], [0], ['Y']]
        self.x_label = 'Time [s]' # Define x-axis label for plots
        self.x_values = []
        self.plot_title = 'Saved session'
        self.n_data_points = 0
        self.timer = 0
        self.starttime = 0
        self.stored_data = []
        self.stored_data_time = 0
        self.date = datetime.datetime(2020,10,10)
        self.serial_number = 'serial'
        self.spo2 = 0
        self.beat_per_minute = 0
        self.perfusion_index = 0.1
        self.alarm = 'alarm'
        # Most of the following commands we don't use. They are just there as
        # some sort of documentation
        self.cmd_hello1 = b'\x7d\x81\xa7\x80\x80\x80\x80\x80\x80'
        self.cmd_hello2 = b'\x7d\x81\xa2\x80\x80\x80\x80\x80\x80'
        self.cmd_hello3 = b'\x7d\x81\xa0\x80\x80\x80\x80\x80\x80'
        self.cmd_session_hello = b'\x7d\x81\xad\x80\x80\x80\x80\x80\x80'
        self.cmd_get_session_count = b'\x7d\x81\xa3\x80\x80\x80\x80\x80\x80'
        self.cmd_get_session_time = b'\x7d\x81\xa5\x80\x80\x80\x80\x80\x80'
        self.cmd_get_session_duration = b'\x7d\x81\xa4\x80\x80\x80\x80\x80\x80'
        self.cmd_get_user_info = b'\x7d\x81\xab\x80\x80\x80\x80\x80\x80'
        self.cmd_get_session_data = b'\x7d\x81\xa6\x80\x80\x80\x80\x80\x80'
        self.cmd_get_deviceid = b'\x7d\x81\xaa\x80\x80\x80\x80\x80\x80'
        self.cmd_get_info = b'\x7d\x81\xb0\x80\x80\x80\x80\x80\x80'
        self.cmd_get_model = b'\x7d\x81\xa8\x80\x80\x80\x80\x80\x80'
        self.cmd_get_vendor = b'\x7d\x81\xa9\x80\x80\x80\x80\x80\x80'
        self.cmd_session_erase = b'\x7d\x81\xae\x80\x80\x80\x80\x80\x80'
        self.cmd_custom = b'\x7d\x81\xf5\x80\x80\x80\x80\x80\x80'
        self.cmd_session_stuff = b'\x7d\x81\xaf\x80\x80\x80\x80\x80\x80'
        self.cmd_get_live_data = b'\x7d\x81\xa1\x80\x80\x80\x80\x80\x80'
        
    def setup_device(self, target, is_bluetooth=False):
        self.target = target
        self.is_bluetooth = is_bluetooth
        if self.is_bluetooth:
            self.btsock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)

        else:
            self.ser = serial.Serial(self.target,
                                     baudrate = 9600,
                                     parity = serial.PARITY_NONE,
                                     stopbits = serial.STOPBITS_ONE,
                                     bytesize = serial.EIGHTBITS,
                                     timeout = 0.1,
                                     xonxoff = 0)
            return True
            
    def initiate_device(self):
        """Sends bytes to device which seem to serve its initialization."""
        self.send_cmd(self.cmd_hello1)
        response = self.recv()
        if not response:
            return False
        self.send_cmd(self.cmd_hello2)
        self.send_cmd(self.cmd_hello3)
        self.recv()
        return True
        
    def recv(self, bytes=1):
        """Receives entire response from device and saves it in list."""
        response_list = []
        while True:
            response = self.ser.read()
                
            if response:
                response_list.append(response)
            else:
                break
        return response_list
        
    def send_cmd(self, cmd, debug=False):
        """
        Sends specified command to device and prints debug output if debug flag
        is set.
        """
        self.ser.write(cmd)
        if debug:
            print("Write:    ", cmd)
            response = []
            while True:
                r = response.append(self.ser.read())
                if self.ser.in_waiting == 0:
                    break
            response_string = ' '.join([str(ord(r)) for r in response])
            print("Response: ", response)
            
    def get_session_count(self):
        """Checks if stored data is available and stores result in self.sess_available."""
        self.send_cmd(self.cmd_get_session_count)
        response = self.recv()
        
        session_count = ord(response[3]) & 0x7f
        if session_count == 1:
            self.sess_available = 'Yes'
        else:
            self.sess_available = 'No'

    def get_session_duration(self):
        """Retrieves session duration, calculates data points"""
        self.send_cmd(self.cmd_get_session_duration)
        response = self.recv()
        
        response_conv = []
        for r in response:
            response_conv.append(ord(r) & 0x7f)
            
        # I got the following logic from Mark Watkins' SleepyHead
        duration = ((response_conv[1] & 0x04) << 5)
        duration |= response_conv[4]
        duration |= (response_conv[5] | ((response_conv[1] & 0x08) << 4)) << 8
        duration |= (response_conv[6] | ((response_conv[1] & 0x10) << 3)) << 16
        
        duration_seconds = duration / 2
        self.sess_duration = datetime.timedelta(seconds=duration_seconds)
        self.sess_data_points = round(self.sess_duration.total_seconds() / 3)
        
    def get_vendor(self):
        """Retrieves vendor and stores it in self.vendor."""
        self.send_cmd(self.cmd_get_vendor)
        response = self.recv()
        self.vendor = ''.join([chr(ord(r) & 0x7f) for r in response if chr(ord(r) & 0x7f).isalnum()])
    
    def get_model(self):
        """Retrieves model and stores it in self.model."""
        self.send_cmd(self.cmd_get_model)
        response = self.recv()
        self.model = ''.join([chr(ord(r) & 0x7f) for r in response if chr(ord(r) & 0x7f).isalnum()])
        
    def get_user(self):
        """Retrieves user and stores it in self.user."""
        self.send_cmd(self.cmd_get_user_info)
        response = self.recv()
        self.user = ''.join([chr(ord(r) & 0x7f) for r in response if chr(ord(r) & 0x7f).isalnum()])
                        
    def process_data(self):
        """Reads data from device and returns key values."""
        line = self.ser.readline()
        parsed_string = line.split()
        
        # make sure we got a full record before we continue.
        # The first record read can often be a partial record.
        
        if len(parsed_string)>10:
        #cleanup nulls at the beginning of the line
            while parsed_string[0][0] == '\x00':
                parsed_string[0] = parsed_string[0][1:]
        #Time
            self.date = datetime.datetime.strptime((parsed_string[0]).decode() + " " + (parsed_string[1]).decode(), "%m/%d/%y %H:%M:%S")
            print(self.date)
        #SN
            self.serial_number = parsed_string[2].split(("=").encode())[1]
            self.serial_number = self.serial_number.decode()
            print(self.serial_number)
        #SPO2 (error when finger's out and the ouput is --, consider adding a try / except)
            self.spo2 = int(parsed_string[3].split(("=").encode())[1].replace(("%").encode(), ("").encode()))
            print(self.spo2)
        #BPM (error when finger's out and the ouput is --, consider adding a try / except)
            self.beat_per_minute = int(parsed_string[4].split(("=").encode())[1])
            print(self.beat_per_minute)
        #PI (error when finger's out and the ouput is --, consider adding a try / except)
            self.perfusion_index = float(parsed_string[5].split(("=").encode())[1].replace(("%").encode(), ("").encode()))
            print(self.perfusion_index)
            self.alarm = parsed_string[10].split(("=").encode())[1]
            self.alarm = self.alarm.decode()
            print(self.alarm)
        return 1
    
    def download_data(self):
        """
        Downloads stored session data from device one value at a time to allow
        the UI's control over this process. The results are stored in self.data_stored
        Another possibility would be to implement the download process fully here and
        have the progress checked regularly via len(self.stored_data) by the UI.
        """
        try: 
            data = self.process_data()
        except (TypeError): # These exceptions are raised when there is no data left to download
            self.stored_data_time = 0 # Reset the timer
            print('No data left to download')
            return False
        else:
            data.insert(0, self.stored_data_time)
            self.stored_data.append(data)
            self.stored_data_time += 1 # A data point is stored every three seconds
            return True
        
    def convert_datetime(self):
        """Replaces time deltas with absolute time."""
        for data in self.stored_data:
            newtime = self.pydatetime + datetime.timedelta(0, data[0])
            self.x_values.append(data[0]) # Copy original values for Matplotlib
            data[0] = newtime.time().strftime('%H:%M:%S')
        self.x_label = 'Time'
        enddatetime = self.pydatetime + datetime.timedelta(0, self.x_values[-1])
        self.plot_title = str('Recorded session from ' + 
                                   self.pydatetime.strftime('%d %B %Y, %H:%M:%S') + ' to ' 
                                   + enddatetime.strftime('%d %B %Y, %H:%M:%S'))
        
    def write_csv(self, filename):
        """Writes session data as CSV file."""
        with open(filename, 'w') as f:
            datawriter = csv.writer(f, delimiter=',', lineterminator='\n')
            datawriter.writerow([self.x_label, 'Finger out[true/false]', 'Pulse rate [bpm]', 'SpO2 [%]'])
            datawriter.writerows(self.stored_data)

    def close_device(self):
        """Closes device socket"""
        if hasattr(self, "ser"):
            self.ser.close()
            
    def write_svg(self, filename):
        """Writes Pygal plot as SVG."""
        with open(filename, 'wb') as file:
            file.write(self.chart)

    def open_csv(self, filename):
        """Opens and processes CSV session file."""
        with open(filename, 'r') as file:
            reader = csv.reader(file)
            next(reader) # Skip header
            self.stored_data = []
            for row in reader:
                self.stored_data.append([float(row[0]), row[1], int(row[2]), int(row[3])])
        if (len(self.stored_data)) > 1:
            self.sess_available = 'Yes'
            self.sess_duration = datetime.timedelta(seconds=self.stored_data[-1][0])
        else:
            self.sess_available = 'No'
        
    def erase_session(self):
        """
        Erases the stored session from the device.
        Doesn't work right now.
        """
        self.send_cmd(self.cmd_session_erase)
        print('Sent erase command')
        
class DeviceScan():
    """Scans for serial or Bluetooth devices."""
    def __init__(self, is_bluetooth=False):
        self.accessible_ports = []
        self.get_serial_ports()

    def get_bt_devices(self):
        """
        Scans for Bluetooth devices, looks up their name and returns a dictionary with both
        the devices' MAC address and name.
        """
        self.devices_dict = {}

    def get_serial_ports(self):
        """
        Tries to access serial ports and returns them as a list if successful.
        """
        available_ports = glob.glob('/dev/tty[A-Za-z]*')

        for port in available_ports:
            try:
                s = serial.Serial(port)
                self.accessible_ports.append(port)
                s.close()
            except serial.SerialException:
                pass
