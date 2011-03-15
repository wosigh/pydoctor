#!/usr/bin/env python

from PySide.QtCore import *
from PySide.QtGui import *
import qt4reactor
import sys, tempfile, shutil, subprocess, os, platform, struct, tarfile, shlex
from systeminfo import *
from httpunzip import *

app = QApplication(sys.argv)
qt4reactor.install()

from twisted.internet import reactor
from twisted.internet.protocol import ClientCreator, ReconnectingClientFactory
from twisted.internet.error import ConnectionRefusedError
from novacom2 import DeviceCollector, Novacom, NovacomDebug

jar = 'http://palm.cdnetworks.net/rom/pre2/p210sfr03082011/wrep210rod/webosdoctorp103ueuna-wr.jar'
       
NOVA_WIN32  = 'resources/NovacomInstaller_x86.msi'
NOVA_WIN64  = 'resources/NovacomInstaller_x64.msi'
NOVA_MACOSX = 'resources/NovacomInstaller.pkg.tar.gz'

REMOTE_TEMP = '/media/internal/.developer'

def download_novacom_installer(platform, url, path):
    dl = None
    if platform == 'Windows':
        info = systeminfo()
        if info['System Type'].split('-')[0] == 'x64':
            dl = http_unzip(url, [NOVA_WIN64], path, strip=True)
        else:
            dl = http_unzip(url, [NOVA_WIN32], path, strip=True)
    elif platform == 'Darwin':
        dl = http_unzip(url, [NOVA_MACOSX], path, strip=True)
    return dl[0]

def cmd_getFile(protocol, file):
    
    protocol.file__ = file
    protocol.transport.write('get file://%s\n' % (file))

def cmd_sendFile(protocol, file, dest):
    
    protocol.file__ = file
    protocol.transport.write('put file://%s\n' % (dest))
    
def cmd_memBoot(protocol, file):
    
    protocol.file__ = file
    protocol.transport.write('boot mem://%s\n')

def cmd_run(protocol, parse, command):
    if parse:
        print 'parse'
        args = shlex.split(command)
        for i in range(0,len(args)):
            args[i] = args[i].replace(' ','\\ ').replace('"','\\"')
        command = ' '.join(args)
    else:
        print 'no parse'
    print command
    protocol.transport.write('run file://%s\n' % (command))
    
def cmd_installIPKG(protocol, file):
    f = open(file,'r')
    protocol.data__ = f.read()
    f.close()
    protocol.file__ = file.split('/')[-1]
    protocol.transport.write('put file://%s/%s\n' % (REMOTE_TEMP, protocol.file__))
    
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
        
class NovacomRun(Novacom):

    def __init__(self, gui):
        self.gui = gui

    def cmd_stdout_event(self, data):
        self.gui.output.append(data)
        
    def cmd_stderr_event(self, data):
        self.gui.output.append('<font color=red>%s</font>' %(data))
            

class NovacomInstallIPKG(Novacom):
    
    file__ = None
    data__ = None
    port__ = None
    
    def __init__(self, gui, port):
        self.gui = gui
        self.port = port
        
    def cmd_stderr_event(self, data):
        print data
    
    def cmd_status(self, msg):
        if msg == 'ok 0' and self.port:
            print 'upload'
            datalen = len(self.data__)
            written = 0
            while written < datalen:
                towrite = datalen - written
                if towrite > self.PACKET_MAX:
                    towrite = self.PACKET_MAX
                self.transport.write(struct.pack('<IIII',self.MAGIC,1,towrite,0)+self.data__[written:written+towrite])
                written += towrite
            self.transport.write(struct.pack('<IIII',self.MAGIC,1,20,2))
            self.transport.write(struct.pack('<IIIII',0,0,0,0,0))
            self.transport.write(struct.pack('<IIII',self.MAGIC,1,20,2))
            self.transport.write(struct.pack('<IIIII',2,0,0,0,0))
            self.transport.loseConnection()
            c = ClientCreator(reactor, NovacomInstallIPKG, self.gui, None)
            d = c.connectTCP('localhost', self.port)
            d.addCallback(cmd_run, False, '/usr/bin/luna-send -n 6 luna://com.palm.appinstaller/installNoVerify {\"subscribe\":true,\"target\":\"/media/internal/.developer/%s\",\"uncompressedSize\":0}' % (self.file__))

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
            self.gui.deviceList.setVisible(True)
            self.gui.noDevices.setVisible(False)
            self.gui.deviceList.selectRow(0)
            self.gui.setWidgetsEnabled(True)
        else:
            self.gui.deviceList.setVisible(False)
            self.gui.noDevices.setVisible(True)
            self.gui.setWidgetsEnabled(False)
        
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

class RunDlg(QDialog):
    
    def __init__(self, port, parent=None):
        super(RunDlg, self).__init__(parent)
        self.port = port
        self.setMinimumSize(680, 280)
        buttonBox = QDialogButtonBox()
        closeButton = buttonBox.addButton(buttonBox.Close)
        QObject.connect(closeButton, SIGNAL('clicked()'), self.close)
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        cmdlayout = QHBoxLayout()
        cmdLabel = QLabel('Command:')
        self.cmd = QLineEdit()
        run = QPushButton('Run')
        QObject.connect(run, SIGNAL('clicked()'), self.run)
        cmdlayout.addWidget(cmdLabel)
        cmdlayout.addWidget(self.cmd)
        cmdlayout.addWidget(run)
        layout = QVBoxLayout()
        layout.addLayout(cmdlayout)
        layout.addWidget(self.output)
        layout.addWidget(buttonBox)
        self.setLayout(layout)
        self.setWindowTitle("Run Command")
        
    def run(self):
        text = str(self.cmd.text())
        if text:
            self.output.clear()
            c = ClientCreator(reactor, NovacomRun, self)
            d = c.connectTCP('localhost', self.port)
            d.addCallback(cmd_run, True, text)
        
class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        
        self.platform = platform.system()
        self.tempdir = path = tempfile.mkdtemp()
        
        self.setFixedSize(600, 400)
        self.setWindowIcon(QIcon('novacomInstaller.ico'))
        
        screen = QDesktopWidget().screenGeometry()
        size =  self.geometry()
        self.move((screen.width()-size.width())/2, (screen.height()-size.height())/2)
        
        self.novatool = QWidget(self)
        self.hbox = QVBoxLayout()        
        self.main = QHBoxLayout()
        self.tabs = QTabWidget()
        
        self.noDevices = QLabel('<h1>No Connected Devices</h1>')
        self.noDevices.setAlignment(Qt.AlignCenter)
        self.noDevices.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        self.noDevices.setFixedHeight(208)
        self.noDevices.setStyleSheet('background:white; background-image: url(background.png); background-repeat:no-repeat; background-position:center center;')
        self.main.addWidget(self.noDevices)
        #self.main.setStretch(0,1)
        
        self.deviceList = QTableView()
        #font = QFont()
        #font.setBold(True)
        #self.deviceList.setFont(font)
        self.deviceList.setFixedHeight(208)
        self.deviceListHeader = ['Port','Device','NDUID']
        self.deviceListModel = DeviceTableModel([], self.deviceListHeader, self)
        self.deviceList.setModel(self.deviceListModel)
        self.deviceList.setShowGrid(False)
        self.deviceList.verticalHeader().setVisible(False)
        self.deviceList.horizontalHeader().setStretchLastSection(True)
        self.deviceList.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.deviceList.setSelectionMode(QAbstractItemView.SingleSelection)
        self.deviceList.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.deviceList.setVisible(False)
        self.deviceList.setStyleSheet('background:white; background-image: url(background.png); background-repeat:no-repeat; background-position:center center;')
        self.main.addWidget(self.deviceList)
               
        self.buttons = QHBoxLayout()
        
        self.getFileButton = QToolButton()
        self.getFileButton.setFixedWidth(128)
        self.getFileButton.setIcon(QIcon('document-import.png'))
        self.getFileButton.setText('Get File')
        self.getFileButton.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.getFileButton.setIconSize(QSize(48,48))
        self.getFileButton.setStyleSheet("padding-bottom: 8")
        QObject.connect(self.getFileButton, SIGNAL('clicked()'), self.getFile)
        self.buttons.addWidget(self.getFileButton)
                
        self.sendFileButton = QToolButton()
        self.sendFileButton.setFixedWidth(128)
        self.sendFileButton.setIcon(QIcon('document-export.png'))
        self.sendFileButton.setText('Send File')
        self.sendFileButton.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.sendFileButton.setIconSize(QSize(48,48))
        self.sendFileButton.setStyleSheet("padding-bottom: 8")
        QObject.connect(self.sendFileButton, SIGNAL('clicked()'), self.sendFile)
        self.buttons.addWidget(self.sendFileButton)
        
        self.memBootButton = QToolButton()
        self.memBootButton.setFixedWidth(128)
        self.memBootButton.setIcon(QIcon('media-flash.png'))
        self.memBootButton.setText('Mem Boot')
        self.memBootButton.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.memBootButton.setIconSize(QSize(48,48))
        self.memBootButton.setStyleSheet("padding-bottom: 8")
        QObject.connect(self.memBootButton, SIGNAL('clicked()'), self.memBoot)
        self.buttons.addWidget(self.memBootButton)
        
        self.runCommandButton = QToolButton()
        self.runCommandButton.setFixedWidth(128)
        self.runCommandButton.setIcon(QIcon('application-x-executable-script.png'))
        self.runCommandButton.setText('Run Command')
        self.runCommandButton.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.runCommandButton.setIconSize(QSize(48,48))
        self.runCommandButton.setStyleSheet("padding-bottom: 8")
        QObject.connect(self.runCommandButton, SIGNAL('clicked()'), self.runCommand)
        self.buttons.addWidget(self.runCommandButton)
        
        self.buttonsW = QWidget()
        self.buttonsW.setLayout(self.buttons)
        
        self.basicOptions = QHBoxLayout()
        
        self.driver = QToolButton()
        self.driver.setFixedWidth(128)
        self.driver.setIcon(QIcon('system-software-update.png'))
        self.driver.setText('Novacom Driver')
        self.driver.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.driver.setIconSize(QSize(48,48))
        self.driver.setStyleSheet("padding-bottom: 8")
        self.basicOptions.addWidget(self.driver)
        
        self.preware = QToolButton()
        self.preware.setFixedWidth(128)
        self.preware.setIcon(QIcon('Icon_Preware.png'))
        self.preware.setText('Install Preware')
        self.preware.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.preware.setIconSize(QSize(48,48))
        self.preware.setStyleSheet("padding-bottom: 8")
        self.basicOptions.addWidget(self.preware)
        
        self.ipk = QToolButton()
        self.ipk.setFixedWidth(128)
        self.ipk.setIcon(QIcon('Icon_Box_Arrow.png'))
        self.ipk.setText('Install Package')
        self.ipk.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.ipk.setIconSize(QSize(48,48))
        self.ipk.setStyleSheet("padding-bottom: 8")
        QObject.connect(self.ipk, SIGNAL('clicked()'), self.installIPKG)
        
        self.basicOptions.addWidget(self.ipk)
        self.basics = QWidget()
        self.basics.setLayout(self.basicOptions)
        self.tabs.addTab(self.basics, 'Basic')
        
        self.tabs.addTab(self.buttonsW, 'Advanced')
        
        self.tabs.setMaximumHeight(150)
        
        self.hbox.addLayout(self.main)
        self.hbox.addWidget(self.tabs)
        
        #self.logo = QLabel()
        #self.logo.setPixmap(QPixmap('novacomInstaller.ico').scaled(128,128))
        #self.logo.setFrameStyle(QFrame.Panel | QFrame.Raised)
        #self.main.addWidget(self.logo)
        
        self.novatool.setLayout(self.hbox)
        self.setCentralWidget(self.novatool)
        self.setWindowTitle('Novatool 1.0')
        self.setUnifiedTitleAndToolBarOnMac(True)
        
        self.icon_disconneced = QPixmap('network-disconnect.png')
        self.icon_connected = QPixmap('network-connect.png')
        self.statusBar = QStatusBar()
        self.statusBar.setSizeGripEnabled(False)
        self.statusIcon = QLabel()
        self.statusMsg = QLabel()
        self.updateStatusBar(False, None)
        self.setStatusBar(self.statusBar)
                
        self.menuBar = QMenuBar()
        self.filemenu = QMenu('File')
        if self.platform == 'Darwin' or self.platform == 'Windows':
            self.driverInstallAction = QAction(self)
            self.driverInstallAction.setText('Install Novacom Driver')
            QObject.connect(self.driverInstallAction, SIGNAL('triggered()'), self.installDriver)
            self.filemenu.addAction(self.driverInstallAction)
            self.filemenu.addSeparator()
        self.quitAction = QAction(self)
        self.quitAction.setText('Quit')
        QObject.connect(self.quitAction, SIGNAL('triggered()'), self.quitApp)
        self.filemenu.addAction(self.quitAction)
        self.menuBar.addMenu(self.filemenu)
        self.aboutmenu = QMenu('Help')
        self.aboutmenu.addAction('About')
        self.menuBar.addMenu(self.aboutmenu)
        self.setMenuBar(self.menuBar)
                        
        reactor.connectTCP('localhost', 6970, DebugFactory(self))
        
        self.show()
        
    def setWidgetsEnabled(self, bool):
        #self.driver.setEnabled(bool)
        self.preware.setEnabled(bool)
        self.ipk.setEnabled(bool)
        self.getFileButton.setEnabled(bool)
        self.sendFileButton.setEnabled(bool)
        self.memBootButton.setEnabled(bool)
        self.runCommandButton.setEnabled(bool)
        
    def installDriver(self):
        dl = download_novacom_installer(self.platform, jar, self.tempdir)
        if dl:
            if self.platform == 'Darwin':
                tf = tarfile.open(dl)
                tf.extractall(self.tempdir)
                tf.close() 
                subprocess.call(['open','-W',dl[:-7]])  
            else:
                subprocess.call(['msiexec','/i',dl])
        
    def quitApp(self):
        reactor.stop()
        QApplication.quit()
        
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
                d.addCallback(cmd_getFile, str(filename))
                
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
        selected = self.deviceList.selectedIndexes()
        if selected:
            port = self.deviceListModel.arraydata[selected[0].row()][0]
            dialog = RunDlg(port, self)
            dialog.show()
        
    def installIPKG(self):
        selected = self.deviceList.selectedIndexes()
        if selected:
            infile = QFileDialog.getOpenFileName(self, caption='Install IPKG')
            if infile[0]:
                port = self.deviceListModel.arraydata[selected[0].row()][0]
                c = ClientCreator(reactor, NovacomInstallIPKG, self, port)
                d = c.connectTCP('localhost', port)
                d.addCallback(cmd_installIPKG, str(infile[0]))
        
    def closeEvent(self, event=None):
        reactor.stop()
        
if __name__ == '__main__':
    mainWin = MainWindow()
    ret = reactor.run()
    shutil.rmtree(mainWin.tempdir)
    sys.exit(ret)
