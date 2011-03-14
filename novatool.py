from PySide.QtCore import *
from PySide.QtGui import *
import qt4reactor
import sys, tempfile, shutil, subprocess, os, platform

app = QApplication(sys.argv)
qt4reactor.install()

from twisted.internet import reactor
from twisted.internet.protocol import ClientCreator
from novacom2 import DeviceCollector, Novacom

def sendCommand(protocol, command):
    protocol.command = command
    protocol.transport.write('%s\n' % (command))

class NovacomDevice(Novacom):
    
    command = None

    def __init__(self, gui):
        self.gui = gui
        
    def cmd_return(self, ret):
        self.transport.loseConnection()
                
    def cmd_stdout(self, data):
        msgBox = QMessageBox()
        msgBox.setText('The file has been retrieved successfully.')
        msgBox.setInformativeText('Do you want to save the file?')
        msgBox.setStandardButtons(QMessageBox.Discard | QMessageBox.Open | QMessageBox.Save )
        msgBox.setDefaultButton(QMessageBox.Save)
        msgBox.setDetailedText(data)
        ret = msgBox.exec_()
        
        if ret == QMessageBox.Save:
            filename = self.command.split('/')[-1]
            filename = QFileDialog.getSaveFileName(self.gui, 'Save file', filename)
            if filename:
                f = open(str(filename[0]), 'w')
                f.write(data)
                f.close()
        elif ret == QMessageBox.Open:
            f = tempfile.NamedTemporaryFile(dir=self.gui.tempdir, delete=False)
            f.write(data)
            f.close()
            if self.gui.platform == 'Darwin':
                subprocess.call(['open',f.name])
            elif self.gui.platform == 'Windows':
                subprocess.call(['start',f.name])
            else:
                subprocess.call(['xdg-open',f.name])
                
    def cmd_stderr(self, data):
        sys.stderr.write(data)

class DeviceCollectorClient(DeviceCollector):
    
    def __init__(self, gui):
        self.gui = gui
        
    def connectionLost(self, reason):
        info = []
        for device in self.devices:
            info.append([device[0],device[3],device[1]])
        self.gui.deviceListModel = DeviceTableModel(info, self.gui.deviceListHeader, self.gui)
        self.gui.deviceList.setModel(self.gui.deviceListModel)
        self.gui.deviceList.resizeColumnsToContents()
        
class DeviceTableModel(QAbstractTableModel): 
    
    def __init__(self, datain, headerdata, parent=None, *args): 
        QAbstractTableModel.__init__(self, parent, *args) 
        self.arraydata = datain
        self.headerdata = headerdata
    
    def rowCount(self, parent):
        if self.arraydata:
            return len(self.arraydata)
        else:
            return 0
    
    def columnCount(self, parent):
        if self.arraydata:
            return len(self.arraydata[0])
        else:
            return 0 
    
    def data(self, index, role): 
        if not index.isValid(): 
            return None
        elif role != Qt.DisplayRole: 
            return None
        return self.arraydata[index.row()][index.column()] 
    
    def headerData(self, col, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.headerdata[col]
        return None

            
class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.resize(600, 220)
        self.setWindowIcon(QIcon('novacomInstaller.ico'))
        
        screen = QDesktopWidget().screenGeometry()
        size =  self.geometry()
        self.move((screen.width()-size.width())/2, (screen.height()-size.height())/2)
        
        self.novatool = QWidget(self)
        self.hbox = QHBoxLayout()
        
        self.deviceList = QTableView()
        self.deviceListHeader = ['Port','Device','NDUID']
        self.deviceListModel = DeviceTableModel([], self.deviceListHeader, self)
        self.deviceList.setModel(self.deviceListModel)
        self.deviceList.setShowGrid(False)
        self.deviceList.verticalHeader().setVisible(False)
        self.deviceList.horizontalHeader().setStretchLastSection(True)
        self.deviceList.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.deviceList.setSelectionMode(QAbstractItemView.SingleSelection)
        self.deviceList.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.hbox.addWidget(self.deviceList)
        
        self.buttons = QVBoxLayout()
        self.getFileButton = QPushButton('Get File')
        QObject.connect(self.getFileButton, SIGNAL('clicked()'), self.getFile)
        self.buttons.addWidget(self.getFileButton)
        self.sendFileButton = QPushButton('Send File')
        QObject.connect(self.sendFileButton, SIGNAL('clicked()'), self.sendFile)
        self.buttons.addWidget(self.sendFileButton)
        self.runCommandButton = QPushButton('Run Command')
        QObject.connect(self.runCommandButton, SIGNAL('clicked()'), self.runCommand)
        self.buttons.addWidget(self.runCommandButton)
        self.installIPKGButton = QPushButton('Install IPKG')
        QObject.connect(self.installIPKGButton, SIGNAL('clicked()'), self.installIPKG)
        self.buttons.addWidget(self.installIPKGButton)
        self.hbox.addLayout(self.buttons)
        
        self.novatool.setLayout(self.hbox)
        self.setCentralWidget(self.novatool)
        self.setWindowTitle('Novatool 1.0')
        self.setUnifiedTitleAndToolBarOnMac(True)
        
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
                
        self.platform = platform.system()
        self.tempdir = path = tempfile.mkdtemp()
                
        ClientCreator(reactor, DeviceCollectorClient, self).connectTCP('localhost', 6968)
        self.show()
        
    def getFile(self):
        selected = self.deviceList.selectedIndexes()
        if selected:
            filename, ok = QInputDialog.getText(self, 'Get file', 'Path to file:')
            if ok:
                port = self.deviceListModel.arraydata[selected[0].row()][0]
                c = ClientCreator(reactor, NovacomDevice, self)
                d = c.connectTCP('localhost', port)
                d.addCallback(sendCommand, 'get file://%s' % (str(filename)))
                
    def sendFile(self):
        print 'sendFile'
        filename = QFileDialog.getOpenFileName(self, caption='Send file')
        print filename
        
    def runCommand(self):
        print 'runCommand'
        
    def installIPKG(self):
        print 'installIPKG'
        
    def closeEvent(self, event=None):
        reactor.stop()
        
if __name__ == '__main__':
    mainWin = MainWindow()
    ret = reactor.run()
    shutil.rmtree(mainWin.tempdir)
    sys.exit(ret)