from PyQt5.QtCore import QProcess, QThread, pyqtSignal, QUrl, Qt
from PyQt5.QtWidgets import QMainWindow
from typing import Literal
import requests
import os

from .config import config
from .auth import gettoken

class Tunnel(QProcess):
    def __init__(self, mode : Literal['http','tcp'], *, parent : QMainWindow):
        QProcess.__init__(self, parent)
        self.args = [
            'http',config.get(mode,'port'),
            '--authtoken', gettoken(),
        ]
        if (subdomain:=config.get(mode,'subdomain')):
            self.args.append('--subdomain')
            self.args.append(subdomain)

        self.exe = config.get('paths','ngrok-path')
        self.setWorkingDirectory(os.path.dirname(self.exe))

    def start(self):
        print(self.args)
        QProcess.start(self,os.path.basename(self.exe),self.args)

class TunnelApi(QThread):
    publicurlsignal = pyqtSignal(dict)
    def __init__(self, *, parent : QMainWindow):
        QThread.__init__(self, parent)
        self.public_url = None

    def run(self):
        try:
            response = requests.get('http://127.0.0.1:4040/api/tunnels',timeout=3).json()
            self.public_url = response['tunnels'][0]['public_url']
            self.publicurlsignal.emit({"status" : "success", "url" : self.public_url})
        except requests.exceptions.RequestException as e:

            self.publicurlsignal.emit({"status" : "error", "message" : f"Errore nel recuperare l'URL del tunnel: {e}"})
            self.public_url = None