#!/usr/bin/env python

import tempfile, tarfile, subprocess, shutil, platform
from systeminfo import *
from httpunzip import *

jar = 'http://palm.cdnetworks.net/rom/pre2/p201r0d11242010/wrep201rod/webosdoctorp102ueuna-wr.jar'
       
NOVA_WIN32  = 'resources/NovacomInstaller_x86.msi'
NOVA_WIN64  = 'resources/NovacomInstaller_x64.msi'
NOVA_MACOSX = 'resources/NovacomInstaller.pkg.tar.gz'

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

if __name__ == '__main__':
    
    platform = platform.system()
    
    path = tempfile.mkdtemp()
    
    dl = download_novacom_installer(platform, jar, path)
    
    if dl:
        
        if platform == 'Darwin':
            tf = tarfile.open(dl)
            tf.extractall(path)
            tf.close() 
            subprocess.call(['open','-W',dl[:-7]])
            
        else:
            subprocess.call(['msiexec','/i',dl])
            
    shutil.rmtree(path)
        