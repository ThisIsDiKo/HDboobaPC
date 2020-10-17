import queue
import threading
import serial
import serial.tools.list_ports_windows
import sys
from utils import *


class ComMonitorThread(threading.Thread):
    def __init__(self,
                 debugQueue,
                 monitorQueue,
                 port_num,
                 port_baud = 115200,
                 port_stopbits=serial.STOPBITS_ONE,
                 port_parity=serial.PARITY_NONE,
                 port_timeout=10):
        threading.Thread.__init__(self)

        self.serial_port = None
        self.serial_arg = dict(port=port_num,
                               baudrate=port_baud,
                               stopbits=port_stopbits,
                               parity=port_parity,
                               timeout=port_timeout)
        self.debugQueue = debugQueue
        self.monitorQueue = monitorQueue

        self.running = True
        self.incoming_array = []

    def get_serial_port(self):
        return self.serial_port

    def run(self):
        msg = ""
        try:
            if self.serial_port:
                self.serial_port.close()
            print("trying to connect")
            self.serial_port = serial.Serial(**self.serial_arg)
            print("got object: ", self.serial_port)
            self.debugQueue.put("connected")
            print("got queue")
        except:
            print("error")
            self.debugQueue.put("port error")

            return

        while self.running:

            try:
                new_data = self.serial_port.read(1)
                if new_data:
                    # print(new_data, end='\t')
                    self.monitorQueue.put(new_data)
                    self.incoming_array.append(int.from_bytes(new_data, 'big'))
                    # print('put byte {0}'.format(int.from_bytes(new_data, 'big')), end='\t')
                    result = parse_msg(self.incoming_array)
                    if result:
                        self.debugQueue.put(result)
                        if result['type'] == 'crc error':
                            self.incoming_array = self.incoming_array[result['endIndex'] + 1:]
                        else:
                            self.incoming_array = self.incoming_array[result['endIndex'] + 1:]
                else:
                    self.incoming_array = []
            except:
                print("unexpected byte")


        if self.serial_port:
            self.serial_port.close()

    def join(self, timeout=None):
        self.running = False
        threading.Thread.join(self, timeout)

    def send(self, byte_array):
        if self.serial_port:
            self.serial_port.write(byte_array)

    def stop(self):
        self.runing = False
        if self.serial_port:
            self.serial_port.close()

