from utils import *
val = [i for i in range(1000)]
o = [serialize_32bit(i) for i in val]
byte_array = []
for p in o:
    for byte in p:
        byte_array.append(byte)

demoFile = open('demo.bin', 'wb')

demoFile.write(bytearray(byte_array))

demoFile.close()
