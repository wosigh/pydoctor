from distutils.core import setup
import py2exe

py2exe_options = dict(
    ascii = True,
    excludes = ['_ssl','pyexpat','bz2'],
    bundle_files = True,
    compressed = True
)

setup(
    #data_files = ['webos-internals.ico'],
    windows = [
        {
            'script': 'installNovacom.py',
            'icon_resources': [(1, 'webos-internals.ico')]
        }
    ],
    options = {'py2exe': py2exe_options},
    zipfile = None,
)
