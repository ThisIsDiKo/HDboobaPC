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

                            msg_to_show += 'Получен пакет с информацией об устройстве\n'
                            msg_to_show += 'UID: {0}\n'.format(s['UID'])
                            msg_to_show += 'Dev ID: {0}\tRev ID: {1}\n'.format(hex(s['Dev ID']), hex(s['Rev ID']))
                            msg_to_show += 'Версия загрузчика: {0}\n'.format(hex(s['Version']))
                            msg_to_show += 'Размер буффера: {0}\n'.format(s['Rec Buf Size'])
                            msg_to_show += 'Размер флеш кбайт: {0}\n'.format(s['Flash Size'])
                            msg_to_show += 'Адрес начала флеш: {0}\n'.format(hex(s['Memory Addr']))
                            msg_to_show += 'Адрес начала программы: {0}\n'.format(hex(s['Programm Addr']))
                            self.print_debug_text(msg_to_show)
                        elif s['type'] == 'erase':
                            msg_to_show += 'Получен пакет с информацией об очистке флеш памяти\n'
                            msg_to_show += 'Размер ответа: {0}\n'.format(s['size'])
                            if s['size'] > 0:
                                msg_to_show += 'Очищено место для: {0} байт\n'.format(deserialize_32bit(s['erased bytes'])[0])
                            self.print_debug_text(msg_to_show)


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
        msg = [197, 58, 4, 0, 0x00, 0x80, 0x00, 0x00]
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

    def array_prepare(self):
        f = open('HDBooba.bin', 'rb')
        bin_data = f.read()
        print(bin_data[:32])
        print('file length: {0}'.format(len(bin_data)))
        val = [i for i in range(8191)]
        o = [serialize_32bit(i) for i in val]
        byte_array = []
        for p in o:
            for byte in p:
                byte_array.append(byte)
        p = []
        byte_array = list(bin_data)
        print(byte_array[:32])
        print('len before append: {0} {1}'.format(len(byte_array), int(len(byte_array) / 1024)))
        if int(len(byte_array) / 1024) != 0:
            ness_number_of_bytes = (int(len(byte_array) / 1024))*1024 + 1024 - len(byte_array)
            print('Не хватает {0}'.format(ness_number_of_bytes))
            for i in range(ness_number_of_bytes):
                byte_array.append(0)

        print('len after append: {0}'.format(len(byte_array)))
        for i in range(0, len(byte_array), 1024):
            temp = byte_array[i:i+1024]
            #print(temp)
            d = {}
            d['packet'] = temp.copy()
            d['crc'] = serialize_32bit(custom_crc32(temp))
            #print(d['crc'])



if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    ex = MainWindow()
    sys.exit(app.exec_())
