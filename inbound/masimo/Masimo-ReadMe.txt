
================
MasimoRad_live
================

Imports MasimoRad
This code continuously pulls data from the machine by calling oxi.process_data()

================
MasimoRad
================

Modified upon cms50ew code for familiarity. Most functions are never used. A few key changes are:

1) The data structure of the Masimo class is different. New variables are declared in the class, such as self.spo2

2) When reading the data, baudrate is different, and xonxoff is set to 0

3) Masimo.download_data() is not used

4) Masimo.process_data() is entirely re-written. You can find the details of how to parse the input inside.

================
post_dataRad
================

Post readings onto the server.

This is only a reference showing which numbers to upload, feel free to use your own uploading code