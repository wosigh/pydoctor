from PySide.QtCore import *
from PySide.QtGui import *
import qt4reactor
import sys

app = QApplication(sys.argv)
qt4reactor.install()

from twisted.internet import reactor
from twisted.internet.protocol import ClientCreator
from novacom2 import DeviceCollector

class DeviceCollectorClient(DeviceCollector):
    
    def __init__(self, gui):
        self.gui = gui
        
    def connectionLost(self, reason):
        ndev = len(self.devices)
        self.gui.deviceList.setRowCount(ndev)
        for i in range(0,ndev):
            item = QTableWidgetItem()
            self.gui.deviceList.setItem(i, 0, item)
            self.gui.deviceList.item(i, 0).setText(str(self.devices[i][0]))
            item = QTableWidgetItem()
            self.gui.deviceList.setItem(i, 1, item)
            self.gui.deviceList.item(i, 1).setText(str(self.devices[i][3]))
            item = QTableWidgetItem()
            self.gui.deviceList.setItem(i, 2, item)
            self.gui.deviceList.item(i, 2).setText(str(self.devices[i][1]))
        self.gui.deviceList.resizeColumnsToContents()
            
class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.resize(560, 220)
        screen = QDesktopWidget().screenGeometry()
        size =  self.geometry()
        self.move((screen.width()-size.width())/2, (screen.height()-size.height())/2)
        
        self.novatool = QWidget(self)
        self.hbox = QHBoxLayout()
        
        self.deviceList = QTableWidget()
        self.deviceList.setColumnCount(3)
        self.deviceList.horizontalHeader().setSortIndicatorShown(False)
        self.deviceList.horizontalHeader().setStretchLastSection(True)
        self.deviceList.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.deviceList.setSelectionMode(QAbstractItemView.SingleSelection)
        self.deviceList.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.deviceList.setShowGrid(False)
        item = QTableWidgetItem()
        self.deviceList.setHorizontalHeaderItem(0, item)
        item = QTableWidgetItem()
        self.deviceList.setHorizontalHeaderItem(1, item)
        item = QTableWidgetItem()
        self.deviceList.setHorizontalHeaderItem(2, item)
        self.deviceList.horizontalHeaderItem(0).setText('Port')
        self.deviceList.horizontalHeaderItem(1).setText('Device')
        self.deviceList.horizontalHeaderItem(2).setText('NDUID')
        self.hbox.addWidget(self.deviceList)
        
        self.buttons = QVBoxLayout()
        self.getFileButton = QPushButton('Get File')
        self.buttons.addWidget(self.getFileButton)
        self.sendFileButton = QPushButton('Send File')
        self.buttons.addWidget(self.sendFileButton)
        self.runCommandButton = QPushButton('Run Command')
        self.buttons.addWidget(self.runCommandButton)
        self.installIPKGButton = QPushButton('Install IPKG')
        self.buttons.addWidget(self.installIPKGButton)
        self.hbox.addLayout(self.buttons)
        
        self.novatool.setLayout(self.hbox)
        self.setCentralWidget(self.novatool)
        self.setWindowTitle('Novatool 1.0')
        self.setUnifiedTitleAndToolBarOnMac(True)
        
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
                
        ClientCreator(reactor, DeviceCollectorClient, self).connectTCP('localhost', 6968)
        self.show()
        
    def closeEvent(self, event=None):
        reactor.stop()
        
if __name__ == '__main__':
    mainWin = MainWindow()
    sys.exit(reactor.run())