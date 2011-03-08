#!/usr/bin/env python

import tempfile, tarfile, subprocess, shutil
from platinfo2 import PlatInfo
from httpunzip import *

jar = 'http://palm.cdnetworks.net/rom/pre2/p201r0d11242010/wrep201rod/webosdoctorp102ueuna-wr.jar'
       
NOVA_WIN32  = 'resources/NovacomInstaller_x86.msi'
NOVA_WIN64  = 'resources/NovacomInstaller_x64.msi'
NOVA_MACOSX = 'resources/NovacomInstaller.pkg.tar.gz'

def download_novacom_installer(os, url, path):
    dl = None
    if os == 'win32':
        dl = http_unzip(url, [NOVA_WIN32], path, strip=True)
    elif os == 'win64':
        dl = http_unzip(url, [NOVA_WIN64], path, strip=True)
    elif os == 'macosx':
        dl = http_unzip(url, [NOVA_MACOSX], path, strip=True)
    return dl[0]

if __name__ == '__main__':
    
    pi = PlatInfo()
    
    path = tempfile.mkdtemp()
    
    dl = download_novacom_installer(pi.os, jar, path)
    
    if dl:
        
        if pi.os == 'macosx':
            tf = tarfile.open(dl)
            tf.extractall(path)
            tf.close() 
            subprocess.call(['open','-W',dl[:-7]])
            
        else:
            subprocess.call(['msiexec','/i',dl])
            
    shutil.rmtree(path)
        