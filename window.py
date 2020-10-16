from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from serialThread import ComMonitorThread
import serial.tools.list_ports_windows as comPortList
import queue
import io
import shutil
from hdboobaModel import HDBoobaModel

from datetime import datetime, date, time

from utils import *

class ComboBox(QComboBox):
    popUpSignal = pyqtSignal()
    def showPopUp(self):
        self.popUpSignal.emit()
        super(ComboBox, self).showPopup()

class MainWindow(QWidget):
    def __init__(self):
        QWidget.__init__(self)

        self.mcu_model = HDBoobaModel()
        self.firmware_dict = None

        self.debugQueue = queue.Queue()
        self.monitorQueue = queue.Queue()
        self.monitorThread = None

        self.cboxComPort = ComboBox()
        self.update_port_list()
        self.cboxComPort.popUpSignal.connect(self.update_port_list)

        self.btnConnect = QPushButton("Подключение")
        self.btnConnect.clicked.connect(self.onclick_connect)

        self.debugTextField = QTextEdit()
        self.monitorTextField = QTextEdit()

        self.btnInfo = QPushButton("Информация")
        self.btnInfo.clicked.connect(self.onclick_info)
        self.btnErase = QPushButton("Очистить флеш")
        self.btnErase.clicked.connect(self.onclick_erase)


        self.comPortLayout = QHBoxLayout()
        self.comPortLayout.addWidget(self.cboxComPort)
        self.comPortLayout.addWidget(self.btnConnect)

        self.textEditLayout = QHBoxLayout()
        self.textEditLayout.addWidget(self.debugTextField)
        self.textEditLayout.addWidget(self.monitorTextField)

        self.btnsLayout = QHBoxLayout()
        self.btnsLayout.addWidget(self.btnInfo)
        self.btnsLayout.addWidget(self.btnErase)


        self.mainLayout = QVBoxLayout()
        self.mainLayout.addLayout(self.comPortLayout)
        self.mainLayout.addLayout(self.textEditLayout)
        self.mainLayout.addLayout(self.btnsLayout)

        self.setLayout(self.mainLayout)
        self.setWindowTitle("HDBooba")
        self.setMinimumSize(1000, 500)
        self.show()

        self.updateTimer = QTimer()
        self.updateTimer.timeout.connect(self.check_buffer)

        self.array_prepare()

    def check_buffer(self):
        monitor_msg = ''
        debug_msg = ''
        s = ''
        try:
            while self.monitorQueue.qsize() > 0:
                s = self.monitorQueue.get(block=False, timeout=None)
                decoded_s = 0
                try:
                    if s == b'\x00':
                        decoded_s = '0x00'
                    else:
                        decoded_s = s.decode('utf-8')
                except:
                    decoded_s = hex(int.from_bytes(s, 'big'))
                monitor_msg += decoded_s
            if monitor_msg:
                self.print_monitor_text(monitor_msg)

            while not self.debugQueue.empty():
                s = {}
                s = self.debugQueue.get(block=False, timeout=None)
                debug_msg += str(s)
            if debug_msg:
                #self.print_debug_text(debug_msg)
                if type(s) is dict:
                    msg_to_show = ''
                    if 'type' in s.keys():
                        print('got correct answer: {0}'.format(s['type']))
                        if s['type'] == 'info':

                            self.mcu_model.start_address = s['Memory Addr']
                            self.mcu_model.bootloader_version = s['Version']
                            self.mcu_model.flash_size = s['Flash Size'] * 1024

                            if s['Rec Buf Size'] > 1030:
                                self.mcu_model.increment_address = 1024
                            else:
                                self.mcu_model.increment_address = 512

                            self.mcu_model.current_step = 'got info'

                            msg_to_show += 'Получен пакет с информацией об устройстве\n'
                            msg_to_show += 'UID: {0}\n'.format(s['UID'])
                            msg_to_show += 'Dev ID: {0}\tRev ID: {1}\n'.format(hex(s['Dev ID']), hex(s['Rev ID']))
                            msg_to_show += 'Версия загрузчика: {0}\n'.format(hex(s['Version']))
                            msg_to_show += 'Размер буффера: {0}\n'.format(s['Rec Buf Size'])
                            msg_to_show += 'Размер флеш кбайт: {0}\n'.format(s['Flash Size'])
                            msg_to_show += 'Адрес начала флеш: {0}\n'.format(hex(s['Memory Addr']))
                            msg_to_show += 'Адрес начала программы: {0}\n'.format(hex(s['Programm Addr']))
                            self.print_debug_text(msg_to_show)

                            self.array_prepare()
                            self.send_page_packet()

                        elif s['type'] == 'erase':
                            msg_to_show += 'Получен пакет с информацией об очистке флеш памяти\n'
                            msg_to_show += 'Размер ответа: {0}\n'.format(s['size'])
                            if s['size'] > 0:
                                msg_to_show += 'Очищено место для: {0} байт\n'.format(deserialize_32bit(s['erased bytes'])[0])
                            self.print_debug_text(msg_to_show)
                        elif s['type'] == 'write':
                            if s['address'] == self.mcu_model.current_address:



        except:
            pass

    def onclick_connect(self):
        portName = self.cboxComPort.currentText()
        portBaud = 115200


        if self.monitorThread is None:
            self.monitorThread = ComMonitorThread(self.debugQueue, self.monitorQueue, portName, portBaud)
            print("monitor created")
            self.monitorThread.start()
            print("monitor started")
            com_error = self.debugQueue.get()[0]
            print("got status")
            if com_error is not "port error":
                print("not error status")
                self.print_debug_text("Port Connected")
                self.updateTimer.start(200)
                return

            self.print_debug_text("Connection error")


    def onclick_info(self):
        msg = [151, 104, 0, 0]
        msg = add_preamb_and_crc(msg)
        self.send_buf(msg)
        pass

    def onclick_erase(self):
        if self.mcu_model.start_address != 0:
            if self.firmware_dict:
                serialized_firmware_size = serialize_32bit(self.firmware_dict['firmware size'])
                msg = [197, 58, 4, 0]
                msg.extend(serialized_firmware_size)
            else:
                msg = [197, 58, 4, 0, 0x00, 0x00, 0x00, 0x00]
        msg = add_preamb_and_crc(msg)
        self.send_buf(msg)
        pass

    def update_port_list(self):
        l = list()
        self.cboxComPort.clear()
        for p in comPortList.comports():
            l.append(p.device)
        self.cboxComPort.addItems(l)

    def send_buf(self, buf, debug=True):
        if debug:
            msg = "send buf: {0}".format(buf)
            self.print_debug_text(msg)
        if self.monitorThread is not None:
            print('sending array')
            self.monitorThread.send(bytearray(buf))

    def print_debug_text(self, text):
        timestamp = datetime.now().strftime("%H:%M:%S")
        text = "{0} --> {1}".format(timestamp, text)
        self.debugTextField.moveCursor(QTextCursor.End)
        self.debugTextField.insertPlainText(text)
        self.debugTextField.insertPlainText("\n")

    def print_monitor_text(self, text):
        self.monitorTextField.moveCursor(QTextCursor.End)
        self.monitorTextField.insertPlainText(text)

    def send_page_packet(self):
        print('{0} {1}< {2} {3}'.format(self.firmware_dict['current page'], type(self.firmware_dict['current page']),
                                        self.firmware_dict['total pages'], type(self.firmware_dict['total pages'])))
        print('hello')
        msg = [0x38, 0xc7]
        print('hello')
        print('page size: {0}'.format(self.firmware_dict['page size']))
        packet_len = serialize_16bit(self.firmware_dict['page size'] + 4)
        print('packet len: {0}'.format(packet_len))
        addr_ser = serialize_32bit(
            self.firmware_dict['pages'][self.firmware_dict['current page']]['page start address'])
        print('ser address: {0}'.format(addr_ser))
        msg.extend(packet_len)
        msg.extend(addr_ser)
        msg.extend(self.firmware_dict['pages'][self.firmware_dict['current page']]['page'])
        print(len(msg), msg)



    def array_prepare(self):
        try:
            f = open('demo.bin', 'rb')
        except:
            print('error opening file')
            return
        bin_data = f.read()
        print(bin_data[:32])
        print('file length: {0}'.format(len(bin_data)))
        byte_array = list(bin_data)

        self.firmware_dict = dict()
        self.firmware_dict['page size'] = 1024
        self.firmware_dict['current page'] = 0
        self.firmware_dict['pages'] = list()


        if int(len(byte_array) / 1024) != 0:
            ness_number_of_bytes = (int(len(byte_array) / 1024))*1024 + 1024 - len(byte_array)
            for i in range(ness_number_of_bytes):
                byte_array.append(0)

        self.firmware_dict['crc'] = custom_crc32(byte_array)
        self.firmware_dict['firmware size'] = len(byte_array)
        self.firmware_dict['total pages'] = int(self.firmware_dict['firmware size'] / self.firmware_dict['page size'])


        for i in range(0, len(byte_array), self.firmware_dict['page size']):
            temp = byte_array[i:i+self.firmware_dict['page size']]
            d = dict()
            d['page id'] = int(i / self.firmware_dict['page size'])
            d['page start address'] = int(i / self.firmware_dict['page size']) * self.firmware_dict['page size'] + self.mcu_model.start_address
            d['page'] = temp.copy()

            self.firmware_dict['pages'].append(d.copy())

        print('num of pages: {0}'.format(len(self.firmware_dict['pages'])))
        for pageInfo in self.firmware_dict['pages']:
            print('{0} --> {1}: {2}'.format(pageInfo['page id'], hex(pageInfo['page start address']), pageInfo['page'][:20]))




if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    ex = MainWindow()
    sys.exit(app.exec_())
