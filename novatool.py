from PySide.QtCore import *
from PySide.QtGui import *
import qt4reactor
import sys, tempfile, shutil, subprocess, os, platform, struct

app = QApplication(sys.argv)
qt4reactor.install()

from twisted.internet import reactor
from twisted.internet.protocol import ClientCreator, ReconnectingClientFactory
from twisted.internet.error import ConnectionRefusedError
from novacom2 import DeviceCollector, Novacom, NovacomDebug

def cmd_getFile(protocol, file):
    
    protocol.file__ = file
    protocol.transport.write('get file://%s\n' % (file))

def cmd_sendFile(protocol, file, dest):
    
    protocol.file__ = file
    protocol.transport.write('put file://%s\n' % (dest))
    
def cmd_memBoot(protocol, file):
    
    protocol.file__ = file
    protocol.transport.write('boot mem://%s\n')

class NovacomGet(Novacom):
    
    file__ = None

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
            filename = self.file__.split('/')[-1]
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

class NovacomSend(Novacom):
    
    file__ = None

    def __init__(self, gui):
        self.gui = gui
        
    def cmd_status(self, msg):
        msgBox = QMessageBox()
        ok = False
        if msg == 'ok 0':
            datalen = len(self.file__)
            written = 0
            while written < datalen:
                towrite = datalen - written
                if towrite > self.PACKET_MAX:
                    towrite = self.PACKET_MAX
                self.transport.write(struct.pack('<IIII',self.MAGIC,1,towrite,0)+self.file__[written:written+towrite])
                written += towrite
            self.transport.write(struct.pack('<IIII',self.MAGIC,1,20,2))
            self.transport.write(struct.pack('<IIIII',0,0,0,0,0))
            self.transport.write(struct.pack('<IIII',self.MAGIC,1,20,2))
            self.transport.write(struct.pack('<IIIII',2,0,0,0,0))
            self.transport.loseConnection()
            ok = True
        if ok:
            msgBox.setText('The file has been sent successfully.')
        else:
            msgBox.setText('The file fail to be sent.')
            msgBox.setInformativeText(msg)
        msgBox.exec_()

class NovacomDebugClient(NovacomDebug):
    
    def __init__(self, gui):
        self.gui = gui
        
    def connectionMade(self):
        self.gui.updateStatusBar(True, 'Connected to novacomd.')
        ClientCreator(reactor, DeviceCollectorClient, self.gui).connectTCP('localhost', 6968)

    def connectionLost(self, reason):
        self.gui.updateStatusBar(False, 'Connection to novacomd lost.')
        self.gui.deviceListModel = DeviceTableModel([], self.gui.deviceListHeader, self.gui)
        self.gui.deviceList.setModel(self.gui.deviceListModel)
        self.gui.deviceList.horizontalHeader().setVisible(False)
        
    def devicesChanged(self):
        ClientCreator(reactor, DeviceCollectorClient, self.gui).connectTCP('localhost', 6968)
        
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
        if info:
            self.gui.deviceList.horizontalHeader().setVisible(True)
            self.gui.deviceList.selectRow(0)
        else:
            self.gui.deviceList.horizontalHeader().setVisible(False)
        
        
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

class DebugFactory(ReconnectingClientFactory):
    
    maxDelay = 10
    factor = 1.05
    
    def __init__(self, gui):
        self.gui = gui
    
    def buildProtocol(self, addr):
        self.resetDelay()
        return NovacomDebugClient(self.gui)
    
    def startedConnecting(self, connector):
        self.gui.updateStatusBar(False, 'Connecting to novacomd ...')

    def clientConnectionLost(self, connector, reason):
        ReconnectingClientFactory.clientConnectionLost(self, connector, reason)
        self.gui.updateStatusBar(False, 'Connection to novacomd lost!')

    def clientConnectionFailed(self, connector, reason):
        ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)
        self.gui.updateStatusBar(False, 'Connection to novacomd failed!')
            
class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setMinimumSize(620, 280)
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
        self.logo = QLabel()
        self.logo.setPixmap(QPixmap('novacomInstaller.ico').scaled(128,128))
        self.buttons.addWidget(self.logo)
        self.getFileButton = QPushButton('Get File')
        QObject.connect(self.getFileButton, SIGNAL('clicked()'), self.getFile)
        self.buttons.addWidget(self.getFileButton)
        self.sendFileButton = QPushButton('Send File')
        QObject.connect(self.sendFileButton, SIGNAL('clicked()'), self.sendFile)
        self.buttons.addWidget(self.sendFileButton)
        self.memBootButton = QPushButton('Mem Boot')
        QObject.connect(self.memBootButton, SIGNAL('clicked()'), self.memBoot)
        self.buttons.addWidget(self.memBootButton)
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
        
        self.icon_disconneced = QPixmap('network-disconnect.png')
        self.icon_connected = QPixmap('network-connect.png')
        self.statusBar = QStatusBar()
        self.statusIcon = QLabel()
        self.statusMsg = QLabel()
        self.updateStatusBar(False, None)
        self.setStatusBar(self.statusBar)
                
        self.menuBar = QMenuBar()
        self.filemenu = QMenu('File')
        self.filemenu.addAction('Install Novacom Driver')
        self.filemenu.addSeparator()
        self.filemenu.addAction('Quit')
        self.menuBar.addMenu(self.filemenu)
        self.aboutmenu = QMenu('Help')
        self.aboutmenu.addAction('About')
        self.menuBar.addMenu(self.aboutmenu)
        self.setMenuBar(self.menuBar)
                
        self.platform = platform.system()
        self.tempdir = path = tempfile.mkdtemp()
        
        reactor.connectTCP('localhost', 6970, DebugFactory(self))
        
        self.show()
        
    def updateStatusBar(self, connected, msg):
        if connected:
            self.statusIcon.setPixmap(self.icon_connected)
        else:
            self.statusIcon.setPixmap(self.icon_disconneced)
        self.statusBar.addWidget(self.statusIcon)
        if msg:
            self.statusMsg.setText(msg)
            self.statusBar.addWidget(self.statusMsg)
        
    def getFile(self):
        selected = self.deviceList.selectedIndexes()
        if selected:
            filename, ok = QInputDialog.getText(self, 'Get file', 'Path to file:')
            if ok:
                port = self.deviceListModel.arraydata[selected[0].row()][0]
                c = ClientCreator(reactor, NovacomGet, self)
                d = c.connectTCP('localhost', port)
                d.addCallback(sendCommand, str(filename))
                
    def sendFile(self):
        selected = self.deviceList.selectedIndexes()
        if selected:
            infile = QFileDialog.getOpenFileName(self, caption='Send file')
            if infile[0]:
                outfile, ok = QInputDialog.getText(self, 'Send file', 'Path to file:')
                if ok:
                    f = open(str(infile[0]),'r')
                    data = f.read()
                    f.close()
                    port = self.deviceListModel.arraydata[selected[0].row()][0]
                    c = ClientCreator(reactor, NovacomSend, self)
                    d = c.connectTCP('localhost', port)
                    d.addCallback(cmd_sendFile, data, str(outfile))        

    def memBoot(self):
        selected = self.deviceList.selectedIndexes()
        if selected:
            infile = QFileDialog.getOpenFileName(self, caption='Mem boot kernel')
            if infile[0]:
                f = open(str(infile[0]),'r')
                data = f.read()
                f.close()
                port = self.deviceListModel.arraydata[selected[0].row()][0]
                c = ClientCreator(reactor, NovacomSend, self)
                d = c.connectTCP('localhost', port)
                d.addCallback(cmd_memBoot, data)
        
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