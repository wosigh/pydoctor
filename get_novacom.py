#!/usr/bin/env python

import argparse
from platinfo import PlatInfo
from httpunzip import *

jars = ['http://palm.cdnetworks.net/rom/pre2/p201r0d11242010/wrep201rod/webosdoctorp102ueuna-wr.jar']

NOVA_WIN32  = 'resources/NovacomInstaller_x86.msi'
NOVA_WIN64  = 'resources/NovacomInstaller_x64.msi'
NOVA_MACOSX = 'resources/NovacomInstaller.pkg.tar.gz'

def download_novacom_installer(os, url, path):
    if os == 'win32':
        http_unzip(url, [NOVA_WIN32], path, strip=True)
    elif os == 'win64':
        http_unzip(url, [NOVA_WIN64], path, strip=True)
    elif os == 'macosx':
        http_unzip(url, [NOVA_MACOSX], path, strip=True)

if __name__ == '__main__':
    
    pi = PlatInfo()

    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter,description=jars)
    parser.add_argument('-l', '--list', action="store_true", dest="list", help='List known jar urls.')
    parser.add_argument('-p', '--path', action="store", dest="targetpath", help='Target path for extracted files.')
    group = parser.add_argument_group('required arguments')
    group.add_argument('-u', '--url', action="store", dest="url", help='The URL of the target zip or jar file.', metavar='URL')
    args = parser.parse_args()
    
    if args.list:
        for jar in jars:
            print jar
    elif args.url: 
        download_novacom_installer(pi.os, args.url, args.targetpath)