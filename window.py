from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
#from serialTread import ComMonitorThread
import serial.tools.list_ports_windows as comPortList
import queue
import io
import shutil

class ComboBox(QComboBox):
    popUpSignal = pyqtSignal()
    def showPopUp(self):
        self.popUpSignal.emit()
        super(ComboBox, self).showPopup()

class MainWindow(QWidget):
    def __init__(self):
        QWidget.__init__(self)

        self.debugQueue = queue.Queue()
        self.monitorQueue = queue.Queue()

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


    def onclick_connect(self):
        pass

    def onclick_info(self):
        pass

    def onclick_erase(self):
        pass

    def update_port_list(self):
        l = list()
        self.cboxComPort.clear()
        for p in comPortList.comports():
            l.append(p.device)
        self.cboxComPort.addItems(l)

if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    ex = MainWindow()
    sys.exit(app.exec_())
