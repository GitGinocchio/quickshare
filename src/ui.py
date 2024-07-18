from PyQt5.QtWidgets import QApplication, QMainWindow, QDialog, QFileDialog, QMessageBox, QListWidget, QMenu, QAction
from PyQt5.QtGui import QPixmap, QDesktopServices
from PyQt5.QtCore import QUrl, Qt
from PIL import Image, ImageFilter
from PyQt5.uic import loadUi
import qrcode
import sys
import io
import os
import re

from .server import HTTPServer
from .tunnel import Tunnel, TunnelApi
from .auth import *

class AuthDialog(QDialog):
    def __init__(self, parent : QMainWindow):
        QDialog.__init__(self,parent)
        loadUi('./src/ui/authdialog.ui',self)
        self.exit.clicked.connect(self.onExitClicked)

        if not tokenexist(): 
            self.show()
        else:
            self.parent().show()

    def onExitClicked(self):
        sys.exit(1)

class MainWindow(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        loadUi('./src/ui/mainwindow.ui',self)
        self.server = HTTPServer(parent=self)

        self.tunnel_api = TunnelApi(parent=self)
        self.tunnel_api.publicurlsignal.connect(self.onTunnelReady)
        
        self.tunnel = Tunnel(mode='http',parent=self)
        self.tunnel.started.connect(lambda: self.tunnel_api.start(0))

        self.qrcode.setPixmap(self.createQrCode("https://0000-00-000-000-00.ngrok-free.app",4))

        self.allowed_addresses.setEditTriggers(QListWidget.AllEditTriggers)

        self.add_files.clicked.connect(self.onAddFilesButtonClicked)
        self.add_dir.clicked.connect(self.onAddDirButtonClicked)
        self.del_item.clicked.connect(self.onDelDirButtonClicked)
        self.add_address.clicked.connect(self.onAddAddrButtonClicked)
        self.del_address.clicked.connect(self.onDelAddrButtonClicked)
        self.includesubfolders.clicked.connect(self.onIncludeSubfoldersClicked)
        self.qrcode.setContextMenuPolicy(Qt.CustomContextMenu)
        self.qrcode.customContextMenuRequested.connect(self.onQrCodeRightClick)
        self.sharebutton.clicked.connect(self.onShareButtonClicked)

    # Folders & Files

    def onIncludeSubfoldersClicked(self):
        if not self.includesubfolders.isChecked(): return 
        if self.shared_items.count() <= 1: return

        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning)
        msg.setText("Changes will be applied to avoid duplication, do you want to continue?")
        msg.setWindowTitle("Duplicate File: ")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.exec_()

        self.shared_items : QListWidget

        if msg.clickedButton().text().replace('&','') == 'Yes':
            dirs = [(i, self.shared_items.item(i).text()) for i in range(self.shared_items.count())]
            dirs.sort(key=lambda dir: len(dir[1]))

            for dir in dirs:
                filtered = list(filter(lambda dir: dir[1].startswith(dir[1].split(':',1)[0]),dirs))
                common = os.path.commonprefix([dir for row, dir in filtered])

                if common in [dir for row, dir in filtered]:
                    for fd in filtered:
                        if fd[1] != common: dirs.remove(fd)

            self.shared_items.clear()
            for dir in dirs: self.shared_items.addItem(dir[1])
        else:
            self.includesubfolders.setChecked(False)

    def onAddFilesButtonClicked(self):
        files, types = QFileDialog.getOpenFileNames(self,"Browse files you want to share: ",filter="Documents (*.pdf *.docx *.rtf *.csv);;Images (*.png *.jpg *.jpeg);;All Files (*.*)",initialFilter="All Files (*.*)",options=QFileDialog.Options())
        already_included = []
        for file in files:
            for i in range(self.shared_items.count()):
                if os.path.isdir(dir:=self.shared_items.item(i).text()) and \
                (dir == os.path.dirname(file) if not self.includesubfolders.isChecked() else dir in os.path.dirname(file)):
                    already_included.append(file)
                    break
                elif os.path.isfile(saved_file:=self.shared_items.item(i).text()) and saved_file == file:
                    msg = QMessageBox(self)
                    msg.setIcon(QMessageBox.Warning)
                    msg.setText(f"The file {os.path.basename(file)} is already included")
                    msg.setWindowTitle("Duplicate File:")
                    msg.setStandardButtons(QMessageBox.Ok)
                    msg.exec_()
                    break
            else:
                self.shared_items.addItem(file)
        
        if len(already_included) <= 3:
            for file in already_included:
                msg = QMessageBox(self)
                msg.setIcon(QMessageBox.Warning)
                msg.setText(f"The file {os.path.basename(file)} is already included do you want to include it again?")
                msg.setWindowTitle("Duplicate File:")
                msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                msg.exec_()

                if msg.clickedButton().text().replace('&','') == 'Yes':
                    self.shared_items.addItem(file)
        else:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Warning)
            msg.setText(f"There are {len(already_included)} files already included, do you want to include them again?")
            msg.setWindowTitle("Duplicate File:")
            msg.setStandardButtons(QMessageBox.YesToAll | QMessageBox.No)
            msg.exec_()

            if msg.clickedButton().text().replace('&','') == 'Yes to All':
                for file in already_included: 
                    self.shared_items.addItem(file)

    def onAddDirButtonClicked(self):
        dir = QFileDialog.getExistingDirectory(self,"Browse a folder you want to share:",options=QFileDialog.Options())
        if dir == '': return #self.shared_items.addItem(dir)

        for row in range(self.shared_items.count()):
            if os.path.isfile(file:=self.shared_items.item(row).text()) and \
                (dir == os.path.dirname(file) if not self.includesubfolders.isChecked() else dir in os.path.dirname(file)):
                msg = QMessageBox(self)
                msg.setIcon(QMessageBox.Warning)
                msg.setText(f"The file {os.path.basename(file)} is already included, do you want to keep only the folder?")
                msg.setWindowTitle("Duplicate File:")
                msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                msg.exec_()

                if msg.clickedButton().text().replace('&','') == 'Yes':
                    self.shared_items.takeItem(row)
                
                self.shared_items.addItem(dir)
                break
            elif os.path.isdir(saved_dir:=self.shared_items.item(row).text()) and saved_dir == dir:
                msg = QMessageBox(self)
                msg.setIcon(QMessageBox.Warning)
                msg.setText(f"The directory {dir} is already included")
                msg.setWindowTitle("Duplicate Directory:")
                msg.setStandardButtons(QMessageBox.Ok)
                msg.exec_()
                break
        else:
            self.shared_items.addItem(dir)

    def onDelDirButtonClicked(self):
        if (current_row:=self.shared_items.currentRow()) >= 0:
            self.shared_items.takeItem(current_row)
        else:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Warning)
            msg.setText("You must first Select a folder or file to remove!")
            msg.setWindowTitle("Error: ")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec_()

    # Security Measures

    def onAddAddrButtonClicked(self):
        address = self.address_line_edit.text().strip()
        ip_regex = re.compile(
            r'^(?!10\.)(?!172\.(?:1[6-9]|2[0-9]|3[0-1])\.)(?!192\.168\.)'
            r'(?!127\.)(?!169\.254\.)'
            r'(?!224\.|239\.)(?!240\.)'
            r'(?:[1-9][0-9]?\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}|'
            r'2[0-4][0-9]\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}|'
            r'25[0-5]\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})$'
        )

        if ip_regex.match(address):
            self.allowed_addresses.addItem(address)
        else:
            QMessageBox.warning(self, "Error", "Please enter a valid public IP address.")
        
        self.address_line_edit.clear()
    
    def onDelAddrButtonClicked(self):
        selected_items = self.allowed_addresses.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Error", "No items selected for deletion.")
            return

        for item in selected_items:
            self.allowed_addresses.takeItem(self.allowed_addresses.row(item))

    # Qr Codes Methods

    def createQrCode(self, url : str, blur : int = 0):
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=7,
            border=1,
        )

        qr.add_data(url)
        qr.make(fit=True)
        img : Image.Image = qr.make_image().convert('RGB')

        if blur > 0:
            img = img.filter(ImageFilter.GaussianBlur(blur))

        imgbytes = io.BytesIO()
        img.save(imgbytes,format='png')
        pixmap = QPixmap()
        pixmap.loadFromData(imgbytes.getvalue())
        return pixmap

    def onQrCodeRightClick(self, pos):
        if self.sharebutton.text() != 'Share':
            contextMenu = QMenu(self)

            copyAction = QAction('Copy', self)
            copyAction.triggered.connect(lambda: QApplication.clipboard().setText(self.tunnel_api.public_url))
            contextMenu.addAction(copyAction)

            visitAction = QAction('Visit', self)
            visitAction.triggered.connect(lambda: QDesktopServices.openUrl(QUrl(self.tunnel_api.public_url)))
            contextMenu.addAction(visitAction)
        
            global_pos = self.qrcode.mapToGlobal(pos)
            contextMenu.exec_(global_pos)
        else:
            icon = QMessageBox.Warning
            text = "You need to start a share first!"
            title = "Error: "

            msg = QMessageBox(self)
            msg.setIcon(icon)
            msg.setText(text)
            msg.setWindowTitle(title)
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec_()

    # Share Methods

    def onTunnelReady(self, signal : dict):
        if signal['status'] == 'success':
            self.qrcode.setPixmap(self.createQrCode(signal['url']))
        else:
            self.statusbar.showMessage(f'Error: {signal['message']}')

    def onShareButtonClicked(self):
        if self.sharebutton.text() == 'Share':
            try:
                assert self.shared_items.count() > 0, 'You must share at least one file or directory'

                includesubfolders = self.includesubfolders.isChecked()

                if self.securitymeasures_group.isChecked():
                    
                    if self.password_checkbox.isChecked():
                        assert len((password:=str(self.password.text()).strip())) > 8, 'You must enter a password of at least 8 characters'
                    else: 
                        password = None

                    if self.addressfilter_checkbox.isChecked():
                        assert self.allowed_addresses.count() > 0, 'You must add at least one address to the filter'

                        allowed_ips = []
                        for index in range(self.allowed_addresses.count()):
                            ip = self.allowed_addresses.item(index).text()
                            allowed_ips.append(ip)
                    else:
                        allowed_ips = []
                    
                if self.limits_group.isChecked():

                    if self.downloadlimit_checkbox.isChecked():
                        limit = int(self.downloadlimit.value())
                    else:
                        limit = -1

            except Exception as e:
                msg = QMessageBox(self)
                msg.setIcon(QMessageBox.Warning)
                msg.setText(f"Unable to create a share: {e}")
                msg.setWindowTitle("Warning:")
                msg.setStandardButtons(QMessageBox.Ok)
                msg.exec_()
            else:
                self.statusbar.showMessage('')
                self.sharebutton.setText("Stop")
                self.server.set_mode([os.path.normpath(self.shared_items.item(i).text()) for i in range(self.shared_items.count())],includesubfolders,allowed_ips)
                self.server.start(0)
                self.tunnel.start()
        else:
            self.sharebutton.setText("Share")
            if self.server.isRunning(): 
                self.server.stop()
            self.tunnel.close()
            self.qrcode.setPixmap(self.createQrCode("https://0000-00-000-000-00.ngrok-free.app",4))

    # Assert Safe Close

    def closeEvent(self, event):
        self.server.stop()
        self.server.wait()
        self.tunnel.close()
        self.tunnel.waitForFinished(3000)
        super().closeEvent(event)

