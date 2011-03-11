#!/usr/bin/env python

import telnetlib, socket, struct, argparse

class Device(object):
    
    def __init__(self, port, hash, connection, type):
        super(Device, self).__init__()
        self.port = port
        self.hash = hash
        self.connection = connection
        self.type = type
        
    def __str__(self):
        return "%d %s %s %s" % (self.port, self.hash, self.connection, self.type)

class Novacom(object):
    
    MAGIC = 0xdecafbad
    
    def __init__(self):
        super(Novacom, self).__init__()
        self.devices = [] 
        self.t = telnetlib.Telnet('localhost', 6968)
        self._get_devices()
        
    def _get_devices(self):
        for d in self.t.read_all()[:-1].split('\n'):
            d = d.split(' ')
            self.devices.append(Device(int(d[0]), d[1], d[2], d[3]))   
            
    def get(self, port, path):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(('localhost', port))
        s.send('get file://%s\n' % (path))
        buf = []
        data = []
        c = s.recv(1)
        header = [0,0,0,0]
        footer = [0,0,0,0]
        while c != '\n':
            buf.append(c)
            c = s.recv(1)
        if "".join(buf).split(' ')[0] == 'ok':
            header = struct.unpack('<IIII', s.recv(16))
            print 'h: %d %d %d %d' % (header[0],header[1],header[2],header[3])
            while header[3] == 0:
                tmp = ''
                while len(tmp) < header[2]:
                    buf = s.recv(header[2])
                    print len(buf)
                    tmp = "".join([tmp,"".join(buf)])
                data.append(tmp)
                header = struct.unpack('<IIII', s.recv(16))
                print 'h: %d %d %d %d' % (header[0],header[1],header[2],header[3])
            print 'h: %d %d %d %d' % (header[0],header[1],header[2],header[3])
        s.close()
        file = "".join(data)
        print len(file)
        return file
    
    def list_devices(self):
        for d in n.devices:
            print d
        
if __name__ == '__main__':
    
    n = Novacom()
    
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-l', '--list', action="store_true", dest="list", default=None, help='list devices')
    parser.add_argument('-g', '--get', dest="get", default=None, help='get file', metavar='FILE')
    args = parser.parse_args()
        
    if args.list:
        n.list_devices()
    elif args.get:
        n.get(n.devices[0].port, args.get)
    else:
        parser.print_help()

    
    #print
    #print n.get(n.devices[0].port, '/etc/palm-build-info')
    #print
    #print n.get(n.devices[0].port, '/tmp/test')
    #print
    #print n.get(n.devices[0].port, '/usr/bin/LunaSysMgr')
    #header = struct.unpack('<IBB', result[1][0:6])
    #print header
    #print result[1][7:header[2]+7]
    
    #print 
    #result = n.get(n.devices[0].port, '/tmp/palm-build-info')
    #print result
    #print
    #header = 
    #print header
    #print
    #print result[1][7:header[2]]
    #print
    #packet = struct.unpack('<IIII', result[1][-16:])
    #print packet
    