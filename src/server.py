from flask import Flask, request, redirect, abort, render_template, send_file
from PyQt5.QtWidgets import QMainWindow
from gevent.pywsgi import WSGIServer
from PyQt5.QtCore import QThread
import os

from .config import config

class HTTPServer(QThread):
    def __init__(self, *, parent : QMainWindow):
        QThread.__init__(self, parent)
        self.app = Flask(__file__,template_folder='./src/templates',static_folder='./src/static')
        self.app.add_url_rule('/','/',view_func=self.index)
        self.app.add_url_rule('/login','/login',view_func=self.login)
        self.app.add_url_rule('/shared','/shared',view_func=self.shared)
        self.app.add_url_rule('/download','/download',view_func=self.download)
        self.app.before_request(self.before_request)

        # Server and clients
        self.server = None
        self.allowed_ips = []
        self.banned_ips = []    # next feature
        self.connected_ips = []

        # local address and port
        self.address = config.get('http','address')
        self.port = config.get('http','port')

        # Shared Files and Dirs and current Directory
        self.sharesubfolders : bool = False
        self.shareditems = []
        self.dir = '.'
    
    # Utils

    def get_items(self, dir : str):
        items = []
        print([folder for folder in self.shareditems if os.path.commonprefix((dir, folder)) != ''])
        if dir == '.':
            for item in self.shareditems:
                if not os.access(item,os.R_OK): continue
                items.append((item, os.path.basename(item), item))
        elif dir not in self.shareditems and not self.sharesubfolders:
            return []
        else:
            if not os.access(dir,os.R_OK): return []
            
            for item in os.listdir(dir):
                if not os.access(os.path.join(dir, item),os.X_OK): continue
                if os.path.isdir(os.path.join(dir, item)) and not self.sharesubfolders: continue
                
                # [ Local Path ] [ Dir name ] [ Parent Path ]
                items.append((os.path.join(dir,item), item, dir))

        return items

    def get_branch(self, current_dir : str):
        if current_dir == '.':
            return []

        # Trova il percorso base appropriato
        base_dir = None
        for base in self.shareditems:
            if current_dir.startswith(base):
                base_dir = base
                break

        # Se current_dir non inizia con nessuna delle base_dirs, ritorna una lista vuota
        if base_dir is None:
            return []

        dirs = current_dir.split('\\')
        base_dirs_split = base_dir.split('\\')
        branch = []

        # Calcola la lunghezza del percorso base
        base_len = len(base_dirs_split)

        for i in range(base_len - 1, len(dirs)):
            sub_path = '\\'.join(dirs[:i + 1])
            branch.append((dirs[i], sub_path))

        return branch

    def set_mode(self, shareditems : list[str], sharesubfolders : bool = False, allowed_ips : list = []):
        self.sharesubfolders = sharesubfolders
        self.allowed_ips = allowed_ips
        self.shareditems = shareditems

    # Flask

    def before_request(self):
        if request.headers.getlist("X-Forwarded-For"):
            client_ip = request.headers.getlist("X-Forwarded-For")[0]
        else:
            client_ip = request.remote_addr

        if client_ip not in self.connected_ips:
            if self.allowed_ips and client_ip not in self.allowed_ips:
                abort(403)
            
            self.connected_ips.append(client_ip)

    def index(self):
        return redirect('/shared')
    
    def login(self):
        return redirect('/shared')
    
    def shared(self):
        if 'dir' in request.args:
            if not os.path.isdir(request.args['dir']):
                if os.path.isfile(request.args['dir']):
                    return redirect(f'/download?file={request.args['dir']}')
                else:
                    pass #Gestire l'eccezzione in cui non viene inserito un file esistente e scaricabile.
            else:
                if request.args['dir'] == '.':
                    self.dir = '.'
                else:
                    self.dir = request.args['dir']
        else: 
            self.dir = '.'

        return render_template(
            'index.html',
            items=self.get_items(self.dir),
            dirs=self.get_branch(self.dir)
        )
 
    def download(self):
        try:
            response = send_file(request.args['file'], as_attachment=True)
        except PermissionError:
            return redirect('/shared')
        else: return response

    # QThread

    def run(self):
        self.server = WSGIServer(('localhost',8080),self.app)
        self.server.serve_forever()

    def stop(self):
        if self.server and not self.server.closed: 
            self.server.stop()

        self.terminate()

class TCPServer(QThread):
    pass