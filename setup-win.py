from distutils.core import setup
import py2exe

py2exe_options = dict(
    ascii = True,
    excludes = ['_ssl','pyexpat','bz2'],
    bundle_files = True,
    compressed = True
)

setup(
    windows = [
        {
            'script': 'installNovacom.py',
            'icon_resources': [(1, 'novacomInstaller.ico')]
        }
    ],
    options = {'py2exe': py2exe_options},
    zipfile = None,
)
