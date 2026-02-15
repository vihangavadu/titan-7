#!/usr/bin/env python3
# LUCID TITAN KYC MODULE :: STANDALONE GUI
# Authority: Dva.12 | Status: TITAN_ACTIVE
# Purpose: Standalone PyQt6 application for KYC operations. Replaces server.py.

import sys
import os
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtWebEngineCore import QWebEngineUrlScheme, QWebEngineUrlSchemeHandler, QWebEngineProfile, QWebEngineUrlRequestJob
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QUrl, QObject, pyqtSlot, QIODevice, QBuffer, pyqtSignal, QFile
from PyQt6.QtWebChannel import QWebChannel

# Add module path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from camera_injector import CameraInjector

class LucidSchemeHandler(QWebEngineUrlSchemeHandler):
    def requestStarted(self, job):
        url = job.requestUrl().toString()
        # Remove scheme and host (lucid://app/)
        path = url.replace("lucid://app/", "")
        
        # Simple path sanitization
        if ".." in path:
            job.fail(QWebEngineUrlRequestJob.Error.UrlInvalid)
            return

        file_path = os.path.join(current_dir, path)
        
        if not os.path.exists(file_path):
             print(f"File not found: {file_path}")
             job.fail(QWebEngineUrlRequestJob.Error.UrlNotFound)
             return

        _, ext = os.path.splitext(file_path)
        mime_types = {
            ".html": "text/html",
            ".js": "application/javascript",
            ".css": "text/css",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".json": "application/json"
        }
        mime = mime_types.get(ext, "application/octet-stream").encode('utf-8')
        
        file = QFile(file_path)
        if file.open(QIODevice.OpenModeFlag.ReadOnly):
             content = file.readAll()
             buf = QBuffer(job)
             buf.setData(content)
             buf.open(QIODevice.OpenModeFlag.ReadOnly)
             job.reply(mime, buf)
        else:
             job.fail(QWebEngineUrlRequestJob.Error.RequestFailed)

class Backend(QObject):
    statusChanged = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.injector = CameraInjector()

    @pyqtSlot()
    def load_module(self):
        try:
            self.injector.load_kernel_module()
            self.statusChanged.emit("Kernel module loaded successfully.")
        except Exception as e:
            self.statusChanged.emit(f"Error loading module: {str(e)}")

    @pyqtSlot()
    def start_stream(self):
        source_file = os.path.join(current_dir, 'assets', 'synthetic_kyc_video.mp4')
        try:
            if not os.path.exists(source_file):
                 self.statusChanged.emit(f"Source file not found: {source_file}")
                 return

            self.injector.start_stream(source_file)
            self.statusChanged.emit(f"Stream started from {source_file}")
        except Exception as e:
            self.statusChanged.emit(f"Error starting stream: {str(e)}")

    @pyqtSlot()
    def stop_stream(self):
        try:
            self.injector.stop_stream()
            self.statusChanged.emit("Stream stopped.")
        except Exception as e:
            self.statusChanged.emit(f"Error stopping stream: {str(e)}")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Lucid TITAN V7.0 :: KYC Module")
        self.resize(1024, 768)

        # Setup Scheme Handler
        self.scheme_handler = LucidSchemeHandler()
        profile = QWebEngineProfile.defaultProfile()
        profile.installUrlSchemeHandler(b"lucid", self.scheme_handler)

        # Setup WebView
        self.view = QWebEngineView()
        self.setCentralWidget(self.view)
        
        # Setup WebChannel
        self.channel = QWebChannel()
        self.backend = Backend()
        self.channel.registerObject("backend", self.backend)
        self.view.page().setWebChannel(self.channel)

        # Load Page
        self.view.setUrl(QUrl("lucid://app/index.html"))

if __name__ == "__main__":
    # Register custom scheme
    scheme = QWebEngineUrlScheme(b"lucid")
    scheme.setSyntax(QWebEngineUrlScheme.Syntax.HostAndPort)
    scheme.setDefaultPort(80)
    scheme.setFlags(QWebEngineUrlScheme.Flag.SecureScheme | QWebEngineUrlScheme.Flag.LocalScheme | QWebEngineUrlScheme.Flag.CorsEnabled)
    QWebEngineUrlScheme.registerScheme(scheme)

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
