import struct, sys

from twisted.internet import reactor, protocol
from twisted.internet.protocol import Factory, Protocol
from twisted.internet.endpoints import TCP4ClientEndpoint

class Novacom(Protocol):
    
    MAGIC = 0xdecafbad
    PACKET_MAX = 16384
    
    stdout_ = ''
    stderr = ''
    buffer = ''
    ret = None
    oob = None
    header = None
    status = False
        
    def dataReceived(self, data):
        self.buffer = ''.join([self.buffer, data])
        while len(self.buffer) > 0:
            if self.status:
                if not self.header and len(self.buffer) > 15:
                    self.header = struct.unpack('<IIII', self.buffer[0:16])
                    self.buffer = self.buffer[16:]
                if self.header: 
                    if len(self.buffer) >= self.header[2]:
                        if self.header[3] == 0:
                            self.stdout = ''.join([self.stdout, self.buffer[:self.header[2]]])
                            self.buffer = self.buffer[self.header[2]:]
                            self.header = None
                        elif self.header[3] == 1:
                            self.stderr = ''.join([self.stderr, self.buffer[:self.header[2]]])
                            self.buffer = self.buffer[self.header[2]:]
                            self.header = None
                        elif self.header[3] == 2:
                            self.oob = struct.unpack('<IIIII', self.buffer[:self.header[2]])
                            self.buffer = self.buffer[self.header[2]:]
                            self.header = None
                    else:
                        break
                if self.oob and self.oob[0] == 0:
                    if self.oob[1] == 1:
                        self.cmd_stdout(self.stdout)
                    elif self.oob[1] == 2:
                        self.cmd_stderr(self.stderr)
                    self.oob = None
                if self.oob and self.oob[0] == 2:
                    self.cmd_return(self.oob[1])
                    self._reset()
            else:
                i = self.buffer.find('\n')
                msg = self.buffer[:i]
                if msg == 'ok 0':
                    self.cmd_status(msg)
                    self.status = True
                    self.buffer = self.buffer[i+1:]
                else:
                    self.error(msg)
                    self._reset()
                    
    def cmd_status(self, msg):
        pass
                
    def cmd_return(self, ret):
        pass
                
    def cmd_stdout(self, data):
        sys.stdout.write(data)
        
    def cmd_stderr(self, data):
        sys.stderr.write(data)
    
    def error(self, error):
        print error
        
    def _reset(self):
        self.stdout = ''
        self.stderr = ''
        self.buffer = ''
        self.oob = None
        self.header = None
        self.status = False
        
class DeviceCollector(Protocol):
    
    devices = []
    
    def dataReceived(self, data):
        for d in data[:-1].split('\n'):
            d = d.split(' ')
            self.devices.append((int(d[0]), d[1], d[2], d[3]))