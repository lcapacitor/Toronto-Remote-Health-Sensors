import MasimoRad

def download(filenm="foo.txt",device="COM6"):
        """Function to deal with 'download' action argument"""
        oxi = MasimoRad.Masimo()
        print('Connecting to device ' + str(device) + ' ...')
        if not oxi.setup_device(target=device, is_bluetooth=False):
                raise Exception('Connection attempt unsuccessful.')
        oxi.initiate_device()
        oxi.send_cmd(oxi.cmd_get_live_data)
        while oxi.process_data():
                #print(oxi.spo2)
                #print(oxi.beat_per_minute)
                pass
                #oxi.write_csv(filenm)

if __name__ == '__main__':
        download("foo.txt","COM6")
