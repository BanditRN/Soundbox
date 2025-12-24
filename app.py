import sys
import os
import json
import requests
from PySide6 import QtCore
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QIcon, QMovie, QSize

from src.core.config import Config
from src.utils.resource_manager import ResourceManager
from src.ui.main_window import SoundboardWindow
from src.ui.widgets import LoadingScreen

os.environ["QT_LOGGING_RULES"] = "*.ffmpeg.*=false"

class SoundboardApplication:
    
    def __init__(self):
        app.setApplicationName("SoundBox by BanditRN")
        app.setApplicationVersion("0.4.0")
        app.setWindowIcon(QIcon(ResourceManager.get_resource_path("window_icon.png")))                        

    def run(self) -> int:
        self.window = SoundboardWindow()
        self.window.show()
        if 'splash' in globals() and splash:
             splash.finish(self.window)
        return app.exec()


def main():
    try:
        lockfile = QtCore.QLockFile(QtCore.QDir.tempPath() + '/Soundbox.lock')
        global app
        app = QApplication(sys.argv)
        if lockfile.tryLock(100):
            movie = QMovie(ResourceManager.get_resource_path("splashscreen.gif"))
            movie.setScaledSize(QSize(400, 400))
            movie.setCacheMode(QMovie.CacheMode.CacheAll)

            global splash
            splash = LoadingScreen(movie)
            splash.setEnabled(False)
            splash.show()
            while movie.state() == QMovie.Running and movie.currentFrameNumber() < movie.frameCount() - 1:
                app.processEvents()
            
            MainApp = SoundboardApplication()
            
            # Check for updates
            try:
                response = requests.get("https://api.github.com/repos/BanditRN/Soundbox/releases")
                if response.status_code == 200:
                    latest_version = json.loads(response.text)[0]["tag_name"]
                    if latest_version != app.applicationVersion():
                        QMessageBox.information(None, "Update Available", f"A new version of SoundBox is available: {latest_version}. You are using version {app.applicationVersion()}.")
            except Exception:
                pass # Fail silently on update check

            sys.exit(MainApp.run())
        else:
            QMessageBox.warning(None, "Warning", "Another instance of SoundBox is already running.")
            sys.exit(0)
    except Exception as e:
        with open(Config.LOG_FILE,"w") as f:
            f.write(f"Application error: {str(e)}")
        print(e)
        sys.exit(1)


if __name__ == "__main__":
    main()
