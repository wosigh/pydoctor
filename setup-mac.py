from setuptools import setup

APP = ['novacomInstaller.py']
OPTIONS = {
           'argv_emulation': True,
           'iconfile': 'novacomInstaller.icns',
           }

setup(
    app=APP,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
