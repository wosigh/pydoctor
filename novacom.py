#!/usr/bin/env python

import telnetlib, socket, struct, argparse, sys, tty, termios

class Device(object):
    
    def __init__(self, port, nduid, connection, type):
        super(Device, self).__init__()
        self.port = port
        self.nduid = nduid
        self.connection = connection
        self.type = type
        
    def __str__(self):
        return "%d %s %s %s" % (self.port, self.nduid, self.connection, self.type)

class Novacom(object):
    
    MAGIC = 0xdecafbad
    PACKET_MAX = 16384
        
    def __init__(self):
        super(Novacom, self).__init__()
        self.devices = [] 
        self.t = telnetlib.Telnet('localhost', 6968)
        self._get_devices()
        
    def _get_devices(self):
        data = self.t.read_all()
        if data:
            for d in data[:-1].split('\n'):
                d = d.split(' ')
                self.devices.append(Device(int(d[0]), d[1], d[2], d[3]))
            
    def put(self, port, path, data):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(('localhost', port))
        s.send('put file://%s\n' % (path))
        buf = []
        c = s.recv(1)
        while c != '\n':
            buf.append(c)
            c = s.recv(1)
        if "".join(buf).split(' ')[0] == 'ok':
            datalen = len(data)
            written = 0
            while written < datalen:
                towrite = datalen - written
                if towrite > self.PACKET_MAX:
                    towrite = self.PACKET_MAX
                s.send(struct.pack('<IIII',self.MAGIC,1,towrite,0)+data[written:written+towrite])
                written += towrite
        s.close()
            
    def get(self, port, path):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(('localhost', port))
        s.send('get file://%s\n' % (path))
        buf = []
        data = []
        c = s.recv(1)
        header = (0,0,0,0)
        while c != '\n':
            buf.append(c)
            c = s.recv(1)
        if "".join(buf).split(' ')[0] == 'ok':
            header = struct.unpack('<IIII', s.recv(16))
            while header[3] == 0:
                i = 0
                while i < header[2]:
                    data.append(s.recv(1))
                    i += 1
                header = struct.unpack('<IIII', s.recv(16))
        s.close()
        return "".join(data)
    
    def run(self, port, cmd):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(('localhost', port))
        s.send('run file://%s\n' % (cmd))
        buf = []
        data = []
        c = s.recv(1)
        header = (0,0,0,0)
        while c != '\n':
            buf.append(c)
            c = s.recv(1)
        if "".join(buf).split(' ')[0] == 'ok':
            header = struct.unpack('<IIII', s.recv(16))
            while header[3] == 0:
                i = 0
                while i < header[2]:
                    data.append(s.recv(1))
                    i += 1
                header = struct.unpack('<IIII', s.recv(16))
        s.close()
        return "".join(data)
    
    def list_devices(self):
        for d in n.devices:
            print d

    def check_devices(self, args):
        if not len(self.devices) > 0:
            print 'unable to find device'
            sys.exit(1)
        port = self.devices[0].port
        if args.nduid:
            for device in self.devices:
                if device.nduid == args.nduid:
                    port = device.port
        if args.port:
            for device in self.devices:
                if device.port == int(args.port):
                    port = device.port
        return port
    
if __name__ == '__main__':
    
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
    group1 = parser.add_mutually_exclusive_group()
    group1.add_argument('-l','--list', action="store_true", dest="list", help='list devices')
    group1.add_argument('-g','--get', dest="get", help='get a remote FILE from device', metavar='FILE')
    group1.add_argument('-p','--put', dest="put", help='put a local FILE on device', metavar='FILE')
    group1.add_argument('-r','--run', dest="run", help='run a remote PROG with arguments', metavar='PROG')
    group2 = parser.add_mutually_exclusive_group()
    group2.add_argument('-P','--port', dest="port", help='connect to specific device by port', metavar='PORT')
    group2.add_argument('-N','--nduid', dest="nduid", help='connect to specific device by nduid', metavar='ID')
    args = parser.parse_args()

    if args.list or args.get or args.put or args.run:
        try:
            n = Novacom()
            port = n.check_devices(args)
            if args.list:
                n.list_devices()
            elif args.get:
                sys.stdout.write(n.get(port, args.get))
            elif args.put:
                data = sys.stdin.read()
                if data:
                    n.put(port, args.put, data)
            elif args.run:
                sys.stdout.write(n.run(port, args.run))
        except socket.error, msg:
            print msg
    else:
        parser.print_help()

    