#!/usr/bin/env python

from PySide.QtCore import *
from PySide.QtGui import *
import qt4reactor
import sys, tempfile, shutil, subprocess, os, platform, struct, tarfile, shlex, urllib2
from systeminfo import *
from httpunzip import *
from config import *

app = QApplication(sys.argv)
qt4reactor.install()

from twisted.internet import reactor
from twisted.internet.protocol import ClientCreator, ReconnectingClientFactory
from twisted.internet.error import ConnectionRefusedError
from novacom2 import DeviceCollector, Novacom, NovacomDebug

DEVICE_ICONS = {
                'castle-linux':'icons/devices/Icon_Device_Pre1_128.png',
                'roadrunner-linux':'icons/devices/Icon_Device_Pre2_128.png',
                'pixie-linux':'icons/devices/Icon_Device_Pixi1_128.png'
                }

jar = 'http://palm.cdnetworks.net/rom/pre2/p210sfr03082011/wrep210rod/webosdoctorp103ueuna-wr.jar'

PREWARE = 'http://get.preware.org/org.webosinternals.preware.ipk'
       
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

def cmd_installIPKG_URL(protocol, url):
    req = urllib2.Request(url)
    f = urllib2.urlopen(req)
    protocol.data__ = f.read()
    f.close()
    protocol.file__ = url.split('/')[-1]
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
        self.gui.debugProto = self
        
    def connectionMade(self):
        self.gui.updateStatusBar(True, 'Connected to novacomd.')
        ClientCreator(reactor, DeviceCollectorClient, self.gui).connectTCP('localhost', 6968)

    def connectionLost(self, reason):
        self.gui.updateStatusBar(False, 'Connection to novacomd lost.')
        for device in self.gui.deviceButtons:
            device.hide()
            self.gui.deviceBoxLayout.removeWidget(device)
            del device
            
        self.gui.activeDevice = None
        b = QLabel('<h2>No Connected Devices</h2>')
        b.setAlignment(Qt.AlignCenter)
        self.gui.deviceButtons = [b]
        self.gui.deviceBoxLayout.addWidget(self.gui.deviceButtons[0])

        
    def devicesChanged(self):
        ClientCreator(reactor, DeviceCollectorClient, self.gui).connectTCP('localhost', 6968)

class deviceEvent(QObject):
    def __init__(self, parent):
        super(deviceEvent, self).__init__(parent)
        self.gui = parent
    def eventFilter(self, object, event):
        if event.type() == QEvent.MouseButtonPress:
            print self.gui
            if object.frameStyle() == QFrame.Panel | QFrame.Sunken:
                object.setFrameStyle(QFrame.Panel | QFrame.Raised)
            else:
                object.setFrameStyle(QFrame.Panel | QFrame.Sunken)
            return True
        return False

class deviceLabelEvent(QObject):
    def __init__(self, parent):
        super(deviceLabelEvent, self).__init__(parent)
    def eventFilter(self, object, event):
        if event.type() == QEvent.MouseButtonPress:
            object.setReadOnly(False)
            return True
        return False
        
class DeviceCollectorClient(DeviceCollector):
    
    def __init__(self, gui):
        self.gui = gui
        
    def connectionLost(self, reason):
        self.gui.devices = self.devices        
        ndev = len(self.devices)
        for device in self.gui.deviceButtons:
            device.hide()
            self.gui.deviceBoxLayout.removeWidget(device)
            del device
            
        if not ndev and self.gui.activeDevice == None:
            self.gui.deviceButtons = [QLabel('<h2>No Connected Devices</h2>')]
            self.gui.deviceButtons[0].setAlignment(Qt.AlignCenter)
            self.gui.deviceBoxLayout.addWidget(self.gui.deviceButtons[0])
        else:
            self.gui.deviceButtons = [None] * ndev 
            for i in range(0,ndev):
                self.gui.deviceButtons[i] = QFrame()
                self.gui.deviceButtons[i].setLineWidth(4)
                self.gui.deviceButtons[i].installEventFilter(deviceEvent(self.gui))
                self.gui.deviceButtons[i].setFrameStyle(QFrame.Panel | QFrame.Raised)
                self.gui.deviceButtons[i].setFixedSize(196,196)
                layout = QVBoxLayout()
                icon = QLabel()
                icon.setPixmap(QPixmap(DEVICE_ICONS[self.devices[i][3]]))
                icon.setAlignment(Qt.AlignCenter)
                layout.addWidget(icon)
                label = QLineEdit()
                if self.gui.config['device_aliases'] and self.gui.config['device_aliases'][self.devices[i][1]]:
                    label.setText(self.gui.config['device_aliases'][self.devices[i][1]])
                else:
                    label.setText(self.devices[i][3])
                label.devid = i
                label.installEventFilter(deviceLabelEvent(self.gui))
                label.setReadOnly(True)
                label.setStyleSheet('background: transparent;')
                label.setFrame(False)
                label.setAlignment(Qt.AlignCenter)
                QObject.connect(label, SIGNAL('returnPressed()'), (lambda x=label : self.editLabel(x)))
                layout.addWidget(label)
                self.gui.deviceButtons[i].setLayout(layout)
                self.gui.deviceBoxLayout.addWidget(self.gui.deviceButtons[i])

    def editLabel(self, label):
        label.setReadOnly(True)
        print (label.text(),self.gui.devices[label.devid][3])
        if label.text() == self.gui.devices[label.devid][3]:
            if self.gui.config['device_aliases'][self.gui.devices[label.devid][1]]:
                del self.gui.config['device_aliases'][self.gui.devices[label.devid][1]]
        else:
            self.gui.config['device_aliases'][self.gui.devices[label.devid][1]] = label.text()
        self.gui.save_config()

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

class InstallDlg(QDialog):
    
    def __init__(self, port, parent=None):
        super(InstallDlg, self).__init__(parent)
        self.port = port
        self.setMinimumWidth(600)
        buttonBox = QDialogButtonBox()
        closeButton = buttonBox.addButton(buttonBox.Cancel)
        installButton = buttonBox.addButton(buttonBox.Ok)
        installButton.setText('Install')
        QObject.connect(installButton, SIGNAL('clicked()'), self.install)
        QObject.connect(closeButton, SIGNAL('clicked()'), self.close)
        cmdlayout = QHBoxLayout()
        cmdLabel = QLabel('File or URL:')
        self.cmd = QLineEdit()
        dir = QPushButton()
        dir.setIcon(QIcon('folder.png'))
        QObject.connect(dir, SIGNAL('clicked()'), self.pickfile)
        cmdlayout.addWidget(cmdLabel)
        cmdlayout.addWidget(self.cmd)
        cmdlayout.addWidget(dir)
        layout = QVBoxLayout()
        layout.addLayout(cmdlayout)
        layout.addWidget(buttonBox)
        self.setLayout(layout)
        self.setWindowTitle("Install IPKG")
        
    def install(self):
        text = str(self.cmd.text())
        if text:
            c = ClientCreator(reactor, NovacomInstallIPKG, self, self.port)
            d = c.connectTCP('localhost', self.port)
            if text[:7] == 'http://':
                d.addCallback(cmd_installIPKG_URL, text)
            else:
                d.addCallback(cmd_installIPKG, text)
        self.close()
        
    def pickfile(self):
        self.cmd.setText(str(QFileDialog.getOpenFileName(self, caption='IPKG', filter='IPKG (*.ipk)')[0]))

class RunDlg(QDialog):
    
    def __init__(self, port, parent=None):
        super(RunDlg, self).__init__(parent)
        self.port = port
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
    def __init__(self, config_file, config, platform, tempdir):
        super(MainWindow, self).__init__()
        
        self.config_file = config_file
        self.config = config
        
        self.debugProto = None
        
        self.platform = platform
        self.tempdir = tempdir
        
        self.devices = []
        self.activeDevice = None
        
        self.deviceButtons = []
        
        self.setWindowIcon(QIcon('novacomInstaller.ico'))
        
        screen = QDesktopWidget().screenGeometry()
        size =  self.geometry()
        self.move((screen.width()-size.width())/2, (screen.height()-size.height())/2)
        
        self.novatool = QWidget(self)
        self.hbox = QVBoxLayout()        
        self.main = QHBoxLayout()
        self.tabs = QTabWidget()
        
        self.deviceBox = QGroupBox('Devices')
        self.deviceBoxLayout = QHBoxLayout()
        self.deviceBox.setLayout(self.deviceBoxLayout)
                       
        self.buttons = QHBoxLayout()
        
        self.getFileButton = QToolButton()
        self.getFileButton.setFixedWidth(96)
        self.getFileButton.setIcon(QIcon('document-import.png'))
        self.getFileButton.setText('Get\nFile')
        self.getFileButton.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.getFileButton.setIconSize(QSize(48,48))
        self.getFileButton.setStyleSheet("padding-bottom: 8")
        QObject.connect(self.getFileButton, SIGNAL('clicked()'), self.getFile)
        self.buttons.addWidget(self.getFileButton)
                
        self.sendFileButton = QToolButton()
        self.sendFileButton.setFixedWidth(96)
        self.sendFileButton.setIcon(QIcon('document-export.png'))
        self.sendFileButton.setText('Send\nFile')
        self.sendFileButton.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.sendFileButton.setIconSize(QSize(48,48))
        self.sendFileButton.setStyleSheet("padding-bottom: 8")
        QObject.connect(self.sendFileButton, SIGNAL('clicked()'), self.sendFile)
        self.buttons.addWidget(self.sendFileButton)
        
        self.memBootButton = QToolButton()
        self.memBootButton.setFixedWidth(96)
        self.memBootButton.setIcon(QIcon('media-flash.png'))
        self.memBootButton.setText('Mem\nBoot')
        self.memBootButton.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.memBootButton.setIconSize(QSize(48,48))
        self.memBootButton.setStyleSheet("padding-bottom: 8")
        QObject.connect(self.memBootButton, SIGNAL('clicked()'), self.memBoot)
        self.buttons.addWidget(self.memBootButton)
        
        self.runCommandButton = QToolButton()
        self.runCommandButton.setFixedWidth(96)
        self.runCommandButton.setIcon(QIcon('application-x-executable-script.png'))
        self.runCommandButton.setText('Run\nCommand')
        self.runCommandButton.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.runCommandButton.setIconSize(QSize(48,48))
        self.runCommandButton.setStyleSheet("padding-bottom: 8")
        QObject.connect(self.runCommandButton, SIGNAL('clicked()'), self.runCommand)
        self.buttons.addWidget(self.runCommandButton)
        
        self.termButton = QToolButton()
        self.termButton.setFixedWidth(96)
        self.termButton.setIcon(QIcon('utilities-terminal.png'))
        self.termButton.setText('Open\nTerminal')
        self.termButton.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.termButton.setIconSize(QSize(48,48))
        self.termButton.setStyleSheet("padding-bottom: 8")
        #QObject.connect(self.termButton, SIGNAL('clicked()'), self.runCommand)
        self.buttons.addWidget(self.termButton)
        
        self.buttonsW = QWidget()
        self.buttonsW.setLayout(self.buttons)
        
        self.basicOptions = QHBoxLayout()
        
        self.driver = QToolButton()
        self.driver.setFixedWidth(96)
        self.driver.setIcon(QIcon('system-software-update.png'))
        self.driver.setText('Novacom\nDriver')
        self.driver.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.driver.setIconSize(QSize(48,48))
        self.driver.setStyleSheet("padding-bottom: 8")
        self.basicOptions.addWidget(self.driver)
        
        self.preware = QToolButton()
        self.preware.setFixedWidth(96)
        self.preware.setIcon(QIcon('Icon_Preware.png'))
        self.preware.setText('Install\nPreware')
        self.preware.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.preware.setIconSize(QSize(48,48))
        self.preware.setStyleSheet("padding-bottom: 8")
        self.basicOptions.addWidget(self.preware)
        QObject.connect(self.preware, SIGNAL('clicked()'), self.installPreware)
        
        self.ipk = QToolButton()
        self.ipk.setFixedWidth(96)
        self.ipk.setIcon(QIcon('Icon_Box_Arrow.png'))
        self.ipk.setText('Install\nPackage')
        self.ipk.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.ipk.setIconSize(QSize(48,48))
        self.ipk.setStyleSheet("padding-bottom: 8")
        QObject.connect(self.ipk, SIGNAL('clicked()'), self.installIPKG)
        
        self.basicOptions.addWidget(self.ipk)
        self.basics = QWidget()
        self.basics.setLayout(self.basicOptions)
        self.tabs.addTab(self.basics, 'Installers')
        
        self.tabs.addTab(self.buttonsW, 'Advanced')
        
        self.tabs.setMaximumHeight(150)
        
        self.hbox.addWidget(self.deviceBox)
        self.hbox.setStretch(0,1)
        self.hbox.addWidget(self.tabs)
                
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

    def save_config(self):
        save_config(self.config_file, self.config)
        
    def setActiveDevice(self, index):
        for i in range(0,len(self.deviceButtons)):
            if i == index:
                self.activeDevice = self.devices[i][1]
                self.deviceButtons[i].setChecked(True)
            else:
                self.deviceButtons[i].setChecked(False)
        
    def setWidgetsEnabled(self, bool):
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
        if self.debugProto:
            self.debugProto.transport.loseConnection()
        shutil.rmtree(self.tempdir)
        self.save_config()
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
            port = self.deviceListModel.arraydata[selected[0].row()][0]
            dialog = InstallDlg(port, self)
            dialog.show()
    
    def installPreware(self):
        print 'Install preware'
        selected = self.deviceList.selectedIndexes()
        if selected:
            port = self.deviceListModel.arraydata[selected[0].row()][0]
            c = ClientCreator(reactor, NovacomInstallIPKG, self, port)
            d = c.connectTCP('localhost', port)
            d.addCallback(cmd_installIPKG_URL, PREWARE)
            
    def closeEvent(self, event=None):
        reactor.stop()
        
if __name__ == '__main__':
    
    platform = platform.system()
    tempdir = path = tempfile.mkdtemp()
    
    if platform == 'Windows':
        appdata = os.environ['APPDATA']
    else:
        _home = os.environ.get('HOME', '/')
        appdata = os.environ.get('XDG_CONFIG_HOME', os.path.join(_home, '.config'))
    novatool_config_home = os.path.join(appdata, 'novatool')    
    if not os.path.exists(novatool_config_home):
        os.mkdir(novatool_config_home)        
    config_file = os.path.join(novatool_config_home,"config")
    config = load_config(config_file)
    
    mainWin = MainWindow(config_file, config, platform, tempdir)
    sys.exit(reactor.run())
