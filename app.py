import sys
import os
import json
from typing import List, Dict, Any
import re
from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtCore import Qt, QSize, QRect, QUrl, Signal, Slot, QModelIndex, QMetaObject, QStringListModel, QThread
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QListView, QPushButton, QSlider, QLabel, QComboBox, QFrame,
                               QStyledItemDelegate, QMessageBox, QFileDialog,
                               QAbstractItemView, QStyle , QTextEdit , QSplashScreen)
from PySide6.QtGui import QIcon, QFont, QPixmap, QMovie,QPainter
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput, QMediaDevices
from multiprocessing import Pool
from pyqt_loading_button import LoadingButton, AnimationType
import winaccent
import requests
from typing import Callable, Dict, Optional
from pynput import keyboard

os.environ["QT_LOGGING_RULES"] = "*.ffmpeg.*=false"

class HotkeyConfig:
    
    def __init__(self, config_file: str):
        self.config_file = config_file
        self.hotkeys: Dict[str, str] = {}
        self.load_config()
    
    def load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    self.hotkeys = json.load(f)
            except json.JSONDecodeError:
                self.hotkeys = {}
        else:
            self.hotkeys = {}
    
    def save_config(self):
        with open(self.config_file, 'w') as f:
            json.dump(self.hotkeys, indent=4, fp=f)
    
    def add_hotkey(self, action_name: str, key_combination: str):
        self.hotkeys[key_combination] = action_name
        self.save_config()
    
    def remove_hotkey(self, key_combination: str):
        if key_combination in self.hotkeys:
            del self.hotkeys[key_combination]
            self.save_config()
    
    def get_action(self, key_combination: str) -> Optional[str]:
        return self.hotkeys.get(key_combination)
    
    def get_hotkey_for_action(self, action_name: str) -> Optional[str]:
        for combo, action in self.hotkeys.items():
            if action == action_name:
                return combo
        return None


class HotkeyListenerThread(QThread):

    action_triggered = Signal(str)  
    key_captured = Signal(str)      
    
    def __init__(self, config: HotkeyConfig):
        super().__init__()
        self.config = config
        self.current_keys = set()
        self.listener: Optional[keyboard.Listener] = None
        self.is_running = True
        self.capture_mode = False
        self._last_executed = None
    
    def start_capture_mode(self):
        self.capture_mode = True
        self.current_keys.clear()
    
    def stop_capture_mode(self):
        self.capture_mode = False
        self.current_keys.clear()
    
    def _normalize_key(self, key) -> str:
        try:
            return key.char.lower() if key.char else ''
        except AttributeError:
            return str(key).replace('Key.', '').lower()
    
    def _on_press(self, key):
        key_name = self._normalize_key(key)
        if not key_name:
            return
        if self.capture_mode:
            if key_name not in self.current_keys and len(self.current_keys) < 2:
                self.current_keys.add(key_name)
                combo = '+'.join(sorted(self.current_keys))
                self.key_captured.emit(combo)
            return
        
        if len(self.current_keys) < 2:
            self.current_keys.add(key_name)
            combo = '+'.join(sorted(self.current_keys))
            action_name = self.config.get_action(combo)
            
            if action_name:
                if not self._last_executed or self._last_executed != combo:
                    self.action_triggered.emit(action_name)
                    self._last_executed = combo
    
    def _on_release(self, key):
        if self.capture_mode:
            return
        
        key_name = self._normalize_key(key)
        if key_name in self.current_keys:
            self.current_keys.remove(key_name)
        
        if len(self.current_keys) == 0:
            self._last_executed = None
    
    def run(self):
        self.listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release
        )
        self.listener.start()
        self.listener.join()
    
    def stop(self):
        self.is_running = False
        if self.listener:
            self.listener.stop()


class KeybindDialog(QtWidgets.QDialog):
    
    def __init__(self, action_name: str, existing_key: str = "", parent=None):
        super().__init__(parent)
        self.action_name = action_name
        self.captured_key = existing_key
        self.accepted_key = None
        self.setWindowTitle("Set Keybind")
        self.setFixedSize(350, 150)
        self.setModal(True)
        
        # Create layout
        layout = QVBoxLayout(self)
        
        # Info label
        info_label = QLabel(f"Set keybind for: {action_name}")
        info_label.setFont(QFont("Arial", 11, QFont.Bold))
        info_label.setStyleSheet("color: white; background: transparent;")
        layout.addWidget(info_label)
        
        # Instruction label
        instruction = QLabel("Press your key combination (max 2 keys)")
        instruction.setStyleSheet("color: #aaaaaa; background: transparent;")
        layout.addWidget(instruction)
        
        # Text box to show captured keys
        self.key_display = QTextEdit()
        self.key_display.setReadOnly(True)
        self.key_display.setFixedHeight(40)
        self.key_display.setPlaceholderText("Press keys...")
        self.key_display.setText(existing_key)
        self.key_display.setStyleSheet("""
            QTextEdit {
                background: #2a2a2a;
                color: white;
                border: 2px solid #444;
                border-radius: 0px;
                padding: 5px;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.key_display)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.accept_btn = QPushButton("Accept")
        self.accept_btn.setStyleSheet("""
            QPushButton {
                background: #28a745;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 5px;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #218838;
            }
            QPushButton:pressed {
                background: #1e7e34;
            }
        """)
        self.accept_btn.clicked.connect(self._accept_keybind)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background: #dc3545;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 5px;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #c82333;
            }
            QPushButton:pressed {
                background: #bd2130;
            }
        """)
        self.cancel_btn.clicked.connect(self.reject)

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background: grey;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 5px;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #c82333;
            }
            QPushButton:pressed {
                background: #bd2130;
            }
        """)
        self.clear_btn.clicked.connect(self.clear_keybind)

        button_layout.addWidget(self.accept_btn)
        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.clear_btn)

        layout.addLayout(button_layout)
        
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0 y1:0, x2:1 y2:1, 
                    stop:0 #051c2a stop:1 #44315f);
                border: 2px solid """ + winaccent.accent_dark_1 + """;
                border-radius: 0px;
            }
            QLabel {
                background: transparent;
            }
        """)
    def clear_keybind(self):
        self.accepted_key = None
        self.accept()

    def update_key_display(self, key_combo: str):
        self.captured_key = key_combo
        self.key_display.setText(key_combo)
    
    def _accept_keybind(self):
        self.accepted_key = self.captured_key
        self.accept()
    
    def get_keybind(self) -> Optional[str]:
        return self.accepted_key

class Config:
    if not os.path.exists(os.getenv('APPDATA')+'\\Soundbox') :
        os.mkdir(os.getenv('APPDATA')+'\\Soundbox')
    KEYBINDS_FILE = os.getenv('APPDATA') + '\\Soundbox\\keybinds.json'
    SETTINGS_FILE = os.getenv('APPDATA') + '\\Soundbox\\settings.json'
    LOG_FILE = os.getenv('APPDATA') + '\\Soundbox\\log.txt'

    DEFAULT_SETTINGS = {
        "Directory": "",
        "DefaultOutput": "",
        "DefaultInput": "",
        "VolumeOutput": 50,
        "VolumeInput": 50
    }
    
    WINDOW_SIZE = (800, 600)
    SUPPORTED_FORMATS = ('.mp3', '.wav', '.ogg', '.flac')



class StyleSheets:
    
    @staticmethod
    def get_scrollbar_style() -> str:
        return """ 

QScrollBar:vertical {
    background-color: transparent;
    border: transparent;
    background: transparent;
    width: 10px;  
}

QScrollBar::handle:vertical {
    background: #a0a0a0;
    min-height: 20px;
    border-radius: 5px;
}

QScrollBar::add-line {
    border: none;
    background: none;
    height: 0px;
    subcontrol-position: bottom;
    subcontrol-origin: margin;
}

QScrollBar::sub-line {
    border: none;
    background: none;
    height: 0px;
    subcontrol-position: top;
    subcontrol-origin: margin;
}

QScrollBar::add-page,
QScrollBar::sub-page {
    background: none ;
}
        """
    
    @staticmethod
    def get_frame_style() -> str:
        return f"QFrame {'{border: 1px solid '+ winaccent.accent_dark_1 + ' ; border-radius: 10px;}'}"
    
    @staticmethod
    def get_button_style() -> str:
        return """
        color: white;
        background: #122138;
        border: 2px solid transparent;
        border-radius: 5px;
        font-size: 16px;
        """


class ResourceManager:
    
    @staticmethod
    def get_resource_path(relative_path: str) -> str:
        try:
                                                                           
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)


class SettingsManager:
    
    def __init__(self):
        self.settings = self._load_settings()
        
    
    def _load_settings(self) -> Dict[str, Any]:
        
        try:
            
            with open(Config.SETTINGS_FILE, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            self._save_settings(Config.DEFAULT_SETTINGS)
            return Config.DEFAULT_SETTINGS.copy()
    
    def _save_settings(self, settings: Dict[str, Any]) -> None:
        
        with open(Config.SETTINGS_FILE, "w") as f:
            json.dump(settings, f, indent=4)
    
    def get(self, key: str, default=None):
        return self.settings.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        self.settings[key] = value
        self._save_settings(self.settings)

    def update_environment_variables(self) -> None:
        env_mappings = {
            "Directory": "SOUNDBOARD_DIR",
            "DefaultOutput": "DefaultOutput",
            "DefaultInput": "DefaultInput",
            "VolumeOutput": "VolumeOutput",
            "VolumeInput": "VolumeInput"
        }
        
        for setting_key, env_key in env_mappings.items():
            value = self.get(setting_key)
            if value:
                os.environ[env_key] = str(value)




class AudioManager:
    
    def __init__(self, settings_manager: SettingsManager):
        self.settings_manager = settings_manager
        self.player = QMediaPlayer()
        self.player2 = QMediaPlayer()
        
        
        self.audio_output = None
        self.audio_soundboard = None
        
    def get_audio_output_devices(self) -> List:
        devices = QMediaDevices.audioOutputs()
        if not devices:
            QMessageBox.warning(None, "Error", "No audio output devices found.")
        return devices
    
    def get_audio_input_devices(self) -> List:
        devices = QMediaDevices.audioOutputs()
        if not devices:
            QMessageBox.warning(None, "Error", "No audio input devices found.")
        return devices
    
    def setup_audio_output(self, device_name: str) -> None:
        devices = self.get_audio_output_devices()
        selected_device = next((dev for dev in devices if dev.description() == device_name), None)
        
        if selected_device:
            self.audio_output = QAudioOutput(selected_device)
            
            volume = int(os.environ.get("VolumeOutput", "50")) / 100
            self.audio_output.setVolume(volume)
    
    def setup_audio_input(self, device_name: str) -> None:
        devices = self.get_audio_input_devices()
        selected_device = next((dev for dev in devices if dev.description() == device_name), None)
        
        if selected_device:
            self.audio_soundboard = QAudioOutput(device=selected_device)
            volume = int(os.environ.get("VolumeInput", "50")) / 100
            self.audio_soundboard.setVolume(volume)
    
    def get_sound_list(self) -> List[str]:
        directory = os.environ.get("SOUNDBOARD_DIR")
        if not directory or not os.path.exists(directory):
            return []
        
        try:
            sound_files_set = set()
            
            for file in os.listdir(directory):

                if file.endswith(Config.SUPPORTED_FORMATS):
                    full_path = os.path.join(directory, file)
                    if os.path.exists(full_path):
                                                                
                        name = os.path.splitext(file)[0]
                        sound_files_set.add(name)
            
            sound_files = list(sound_files_set)                                  
                                                     
            sound_files.sort(key=lambda x: max(
                [os.path.getmtime(os.path.join(directory, x + ext)) 
                 for ext in Config.SUPPORTED_FORMATS if os.path.exists(os.path.join(directory, x + ext))]
            ) if any(os.path.exists(os.path.join(directory, x + ext)) for ext in Config.SUPPORTED_FORMATS) else 0, 
            reverse=True)
            return sound_files
        except Exception:
            return ["NO MUSIC WAS LOADED"]
    
    def play_sound_file(self, sound_name: str) -> bool:

        if not self.audio_output or not self.audio_soundboard:
            return False
        
        sound_dir = os.environ.get("SOUNDBOARD_DIR", "")
        sound_path = ""
        for ext in Config.SUPPORTED_FORMATS:
            temp_path = os.path.join(sound_dir, sound_name + ext)
            if os.path.exists(temp_path):
                sound_path = temp_path
                break

        if not sound_path:                                 
            return False
       
        self.player.setAudioOutput(self.audio_output)
        self.player2.setAudioOutput(self.audio_soundboard)
        
        self.player.setSource(QUrl.fromLocalFile(sound_path))
        self.player2.setSource(QUrl.fromLocalFile(sound_path))


        
        self.player.play()
        self.player2.play()
        
        return True


class HoverDelegate(QStyledItemDelegate):
    buttonClicked = Signal(QModelIndex)

    def paint(self, painter, option, index):
        super().paint(painter, option, index)
        
        if option.state & QStyle.State_MouseOver:
            button_option = QtWidgets.QStyleOptionButton()
            button_option.rect = self._get_button_rect(option)
            button_option.text = "Set Key"
            
            button_option.state = QStyle.State_Enabled | QStyle.State_Raised
            QApplication.style().drawControl(QStyle.CE_PushButton, button_option, painter)

    def editorEvent(self, event, model, option, index):
        if (event.type() == QtCore.QEvent.MouseButtonRelease and 
            event.button() == Qt.LeftButton):
            if self._get_button_rect(option).contains(event.pos()):
                self.buttonClicked.emit(index)
                return True
        return super().editorEvent(event, model, option, index)

    def _get_button_rect(self, option) -> QRect:
        button_width, button_height = 80, 25
        return QRect(
            option.rect.right() - button_width - 5,
            option.rect.top() + (option.rect.height() - button_height) // 2,
            button_width,
            button_height
        )


class ResizableFrame(QFrame):
    """Custom frame that handles resize cursor changes"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setMouseTracking(True)
    
    def mouseMoveEvent(self, event):
        if self.parent_window:
            handle = self.parent_window._get_resize_handle(event.pos())
            if handle:
                self.parent_window._set_resize_cursor(handle)
            else:
                self.setCursor(Qt.ArrowCursor)
        super().mouseMoveEvent(event)
    
    def mousePressEvent(self, event):
        if self.parent_window:
            self.parent_window.mousePressEvent(event)
        super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event):
        if self.parent_window:
            self.parent_window.mouseReleaseEvent(event)
        super().mouseReleaseEvent(event)


class SoundboardWindow(QMainWindow):
    
    def __init__(self):
        super().__init__()

        self.set_keybind = ""
        self.old_pos = None
        self.resizing = False
        self.resize_handle = None
        self.minimum_size = QSize(800, 600)
        self.maximum_size = QSize(1200, 800)         
        self.settings_manager = SettingsManager()
        self.audio_manager = AudioManager(self.settings_manager)
        self.hotkey_config = HotkeyConfig(Config.KEYBINDS_FILE)
        self.hotkey_listener = None
        self.current_capture_action = None
        

        self._setup_window()
        self._create_widgets()
        self._setup_layouts()
        self._connect_signals()
        self._initialize_audio()
        self._load_sounds()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowModality(QtCore.Qt.ApplicationModal)
        self.setMouseTracking(True)
        self.setStyleSheet("""
                           QWidget{
                           background: qlineargradient(x1:0 y1:0, x2:1 y2:1, stop:0 #051c2a stop:1 #44315f);
                           color: transparent;
                           border-radius: 5px;
                           }
                           QPushButton{
                           background: transparent;
                           }
                           QPushButton#reloadBtn:hover:!pressed{
                           background-color: #363637;
                           }
                           QPushButton:hover:pressed{
                           background-color: #141417
                           }
                           QComboBox#audio_devices, QComboBox#audio_input_devices{
                           color: white;
                           background: radial-gradient(circle,rgba(5, 4, 4, 1) 59%, rgba(89, 89, 89, 0.66) 83%);
                           border: 1px solid """+ winaccent.accent_dark_1 +""";
                           height: 18px;
                           }
                           QComboBox#audio_devices QListView, QComboBox#audio_input_devices QListView
                           {
                           border: 0px;
                           background: radial-gradient(circle,rgba(5, 4, 4, 1) 59%, rgba(89, 89, 89, 0.66) 83%);
                           color: white;
                           }
                           QComboBox#audio_devices::drop-down:button, QComboBox#audio_input_devices::drop-down:button{
                           background: transparent;
                            border: 0px;
                           }
                           QComboBox#audio_devices::down-arrow, QComboBox#audio_input_devices::down-arrow{
                           image: url("""+ ResourceManager.get_resource_path("down.png").replace("\\","/") +""");
                           width: 12px;
                           height: 12px;
                           margin-right: 15px;
                           }
                           QLabel
                           {
                            background: transparent;
                            color: white;
                           }
                           QListView{
                            background: transparent;
                            padding-right: 2px;
                            padding-top: 2px;
                            padding-bottom: 2px;
                            color: white;
                            }
                            QListView::item:hover{
                            background: rgba(255, 255, 255, 0.1);
                            border-radius: 5px;
                            border: None;
                            height: 40px;
                            }
                            QListView::item:selected{
                            background: rgba(255, 255, 255, 0.2);
                            border-radius: 5px;
                            
                            }
                            QListView:focus{
                            outline: None;
                            
                            }
                            QTextEdit{
                            color: white;
                            }
                           """)
        

        self.minimize_animation = None
        self._start_hotkey_listener()
        
    def _start_hotkey_listener(self):
        self.hotkey_listener = HotkeyListenerThread(self.hotkey_config)
        
        self.hotkey_listener.action_triggered.connect(self._execute_hotkey_action)
        self.hotkey_listener.key_captured.connect(self._update_keybind_dialog)
        
        self.hotkey_listener.start()
    @Slot(str)
    def _execute_hotkey_action(self, action_name: str):
        self._play_sound_by_name(action_name)

    @Slot(str)
    def _update_keybind_dialog(self, combo: str):
        if self.keybind_dialog and self.keybind_dialog.isVisible():
            self.keybind_dialog.update_key_display(combo)

    def showNormal(self):
        if hasattr(self, '_original_geometry'):
            self.setGeometry(self._original_geometry)
        super().showNormal()

    def _setup_window(self) -> None:
        
        self.setWindowTitle("SoundBox")
        self.setWindowIcon(QIcon(ResourceManager.get_resource_path("window_icon.png")))
        self.setWindowFlags(Qt.FramelessWindowHint)
        
        # Set size constraints
        self.setMinimumSize(self.minimum_size)
        self.setMaximumSize(self.maximum_size)
                                 
        screen = QApplication.primaryScreen().availableGeometry()
        width, height = Config.WINDOW_SIZE
        x = (screen.width() - width) // 2
        y = (screen.height() - height) // 2
        self.setGeometry(x, y, width, height)
        
        
    

    
    def _create_widgets(self) -> None:
        self.central_widget = QWidget()
        self.central_widget.setObjectName("centralwidget")

                               
        self._create_media_buttons()
        
                         
        self._create_volume_controls()
        
                         
        self._create_window_controls()
        
                                
        self._create_audio_device_widgets()
        
                    
        self._create_sound_list_widget()
        
                       
        self._create_other_widgets()


        self._create_seek_slider()

        self._create_start_end_labels()

        
    def _create_seek_slider(self) -> None:
        self.seek_slider = QSlider(Qt.Horizontal)
        self.seek_slider.setValue(0)
        self.seek_slider.setStyleSheet("border: 0px;background: transparent;")
        self.seek_slider.setCursor(Qt.PointingHandCursor)
        self.seek_slider.setFocusPolicy(Qt.NoFocus)
        self.seek_slider.setDisabled(True)

    def _create_start_end_labels(self) -> None:
        self.start_label = QLabel("00:00")
        self.start_label.setFont(QFont("Arial", 10))
        self.start_label.setStyleSheet("border: none;background: transparent;")
        
        self.end_label = QLabel("00:00")
        self.end_label.setFont(QFont("Arial", 10))
        self.end_label.setStyleSheet("border: none;background: transparent;")

    def _create_media_buttons(self) -> None:
        self.play_button = self._create_icon_button("play.png", (70, 50), (50, 50))
        self.stop_button = self._create_icon_button("stop.webp", (70, 50), (50, 50))
        self.reload_button = self._create_icon_button("reload.png", (30, 30), (20, 20))
        self.reload_button.setObjectName("reloadBtn")
    
    def _create_volume_controls(self) -> None:
                       
        self.volume_slider_value = self._create_label(
            str(self.settings_manager.get("VolumeOutput")), 12)
        self.volume_slider_output = self._create_volume_slider("VolumeOutput")
        self.volume_slider_output.setFocusPolicy(Qt.NoFocus)
                      
        self.volume_input_slider_value = self._create_label(
            str(self.settings_manager.get("VolumeInput")), 12)
        self.volume_slider_input = self._create_volume_slider("VolumeInput")
        self.volume_slider_input.setFocusPolicy(Qt.NoFocus)
    
    def _create_window_controls(self) -> None:
                                                                           
        self.close_btn = QPushButton('X')
                                                                                                                                                   
        self.close_btn.setStyleSheet("""
            QPushButton
            {
            background-color: transparent;
            color: black; 
            border: none; 
            font-size: 14px;
            font-weight: bold;
            border-top-left-radius: 0px;
            border-bottom-left-radius: 0px;
            border-bottom-right-radius: 0px;
            border-top-right-radius: 10px;
            }
            QPushButton:hover:!pressed
            {
            background-color: red;
            }""")
        self.close_btn.setFixedSize(30, 25)
                                                                                 
                                                                                 
        self.minimize_btn = QPushButton('_')
        self.minimize_btn.setStyleSheet("""
            QPushButton{text-align: top; background-color: transparent; border-radius: 0px; color: black;  border: none;  font-size: 14px; font-weight: bold;}
                                        QPushButton:hover:!pressed{background-color: grey;}
            """)
        self.minimize_btn.setFixedSize(30, 25)
        self.minimize_btn.setFocusPolicy(Qt.NoFocus)
        self.close_btn.setFocusPolicy(Qt.NoFocus)
    def _create_audio_device_widgets(self) -> None:
                        
        self.audio_devices = QComboBox()
        self.audio_devices.setObjectName("audio_devices")
                                                                 
   
    
                                                                                        
       
        devices = [dev.description() for dev in self.audio_manager.get_audio_output_devices()]
        self.audio_devices.addItems(devices)
        self.audio_devices.setCurrentText(self.settings_manager.get("DefaultOutput", ""))
        
                       
        self.audio_input_devices = QComboBox()
        self.audio_input_devices.setObjectName("audio_input_devices")
                                                                       
   
    
                                                                                        
       
        input_devices = [dev.description() for dev in self.audio_manager.get_audio_input_devices()]
        self.audio_input_devices.addItems(input_devices)
        self.audio_input_devices.setCurrentText(self.settings_manager.get("DefaultInput", ""))
        
                
        self.device_label = self._create_label("Select your audio Output device", 12)
        
        
        self.input_device_label = self._create_label("Select your audio Input device", 12)
        
    
    def _create_sound_list_widget(self) -> None:
        self.list_view = QListView()
        self.model = QStringListModel()
        self.list_view.setModel(self.model)
        
                             
        self.list_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.list_view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.list_view.setMouseTracking(True)
        self.list_view.setSpacing(2)
        self.list_view.setUniformItemSizes(True)
        self.list_view.setViewMode(QListView.ListMode)
        self.list_view.setResizeMode(QListView.Adjust)
        self.list_view.setWrapping(False)
        self.list_view.setIconSize(QSize(100, 40))
        self.list_view.setFont(QFont("Arial", 13))
        self.list_view.setStyleSheet(StyleSheets.get_scrollbar_style())
        self.list_view.setAutoFillBackground(True)
        self.list_view.viewport().setAutoFillBackground(True)
        
        
                         
        self.hover_delegate = HoverDelegate(self)
        self.list_view.setItemDelegate(self.hover_delegate)
    
    def _create_other_widgets(self) -> None:
        
                     
        self.now_playing = QLabel("Now Playing: None")
        self.now_playing.setFont(QFont("Arial", 12))
        self.now_playing.setStyleSheet("border: none;background: transparent;")
                   
        self.search_box = QTextEdit()
        self.search_box.setPlaceholderText("Search...")
        self.search_box.setFixedHeight(30)
        self.search_box.setFixedWidth(200)
        
                              
        self.select_folder_btn = LoadingButton(self)
        self.select_folder_btn.setText("Select Sound Folder")
        self.select_folder_btn.setAnimationType(AnimationType.Circle)
        self.select_folder_btn.setAnimationSpeed(2000)
        self.select_folder_btn.setAnimationColor(QtGui.QColor(0, 0, 0))
        self.select_folder_btn.setAnimationWidth(15)
        self.select_folder_btn.setAnimationStrokeWidth(3)
        self.select_folder_btn.setStyleSheet(StyleSheets.get_button_style())


    def _create_icon_button(self, icon_file: str, size: tuple, icon_size: tuple = None) -> QPushButton:
        button = QPushButton()
        button.setIcon(QIcon(ResourceManager.get_resource_path(icon_file)))
        if icon_size:
            button.setIconSize(QSize(*icon_size))
        button.setStyleSheet("QPushbutton{background-color: transparent;border: 0px;}")
        button.setFlat(True)
        button.setCursor(Qt.PointingHandCursor)
        button.setFixedSize(*size)
        button.setFocusPolicy(Qt.NoFocus)
        
        return button

    
    def _create_label(self, text: str, font_size: int) -> QLabel:
        label = QLabel(text)
        font = QFont()
        font.setPointSize(font_size)
        label.setFont(font)
        label.setStyleSheet("padding-bottom: 5px; border: transparent; background: transparent; color: white;")
        return label
    
    def _create_volume_slider(self, env_var: str) -> QSlider:
        slider = QSlider(Qt.Horizontal)
        slider.setCursor(Qt.PointingHandCursor)
        slider.setMaximum(100)
        slider.setMinimum(0)
        slider.setValue(int(self.settings_manager.get(env_var)))
        slider.setStyleSheet("border: 0px;background: transparent;")
        return slider
    
    def _setup_layouts(self) -> None:
                     
        
        main_layout = QVBoxLayout(self.central_widget)
        main_layout.setContentsMargins(0,0,0,0)
        for widget in self.central_widget.children():
            if isinstance(widget, QLabel) or isinstance(widget, QPushButton):
                widget.setStyleSheet("background: transparent;")
        
                      
        
        self.frame = ResizableFrame(self.central_widget)
        self.frame.parent_window = self
        self.frame.setFrameShape(QFrame.Shape.Box)
        self.frame.setFrameShadow(QFrame.Shadow.Plain)
        self.frame.setObjectName("mainFrame")
        self.frame.setStyleSheet(StyleSheets.get_frame_style())
        self.frame.setLayout(main_layout)
        
                           
        title_bar = QHBoxLayout()
        
        title_bar.setSpacing(0)
        title_text = QLabel("SoundBox", textFormat=Qt.PlainText)
        title_text.setFont(QFont("Arial", 16, QFont.Bold))
        title_text.setStyleSheet("color: white; border: None;background: transparent;padding-top: 5px;")
        title_bar.addWidget(title_text, alignment=Qt.AlignLeft)
        title_bar.addStretch()
        title_bar.addWidget(self.minimize_btn, alignment=Qt.AlignRight | Qt.AlignTop) 
        title_bar.addWidget(self.close_btn, alignment=Qt.AlignRight | Qt.AlignTop)
        title_bar.setContentsMargins(10,0,0,10)

        main_layout.addLayout(title_bar)

                              
        v_layout = QVBoxLayout()
        v_layout.setContentsMargins(10, 10, 10, 10)
        v_layout.setSpacing(10)
        main_layout.addLayout(v_layout)

        

                                
        controls_layout = QHBoxLayout()
        controls_layout.setAlignment(Qt.AlignCenter | Qt.AlignBottom)
        controls_layout.addWidget(self.play_button)
        controls_layout.addWidget(self.stop_button)
        
                       
        bottom_layout = QHBoxLayout()
        bottom_layout.setAlignment(Qt.AlignCenter | Qt.AlignBottom)
        
                             
        output_layout = QVBoxLayout()
        output_layout.setAlignment(Qt.AlignLeft)
        output_layout.addWidget(self.device_label, alignment=Qt.AlignCenter)
        output_layout.addWidget(self.audio_devices)
        output_layout.addWidget(self.volume_slider_value, alignment=Qt.AlignCenter)
        output_layout.addWidget(self.volume_slider_output)
        
                            
        input_layout = QVBoxLayout()
        input_layout.setAlignment(Qt.AlignRight)
        input_layout.addWidget(self.input_device_label, alignment=Qt.AlignCenter)
        input_layout.addWidget(self.audio_input_devices)
        input_layout.addWidget(self.volume_input_slider_value, alignment=Qt.AlignCenter)
        input_layout.addWidget(self.volume_slider_input)
        
        bottom_layout.addLayout(output_layout)
        bottom_layout.addSpacing(200)
        bottom_layout.addLayout(input_layout)
        
        hlayout = QHBoxLayout()
        
        hlayout.addWidget(self.search_box, alignment=Qt.AlignLeft)

        hlayout.addWidget(self.now_playing, alignment=Qt.AlignCenter)
        
        
        hlayout.addWidget(self.reload_button, alignment=Qt.AlignRight)
        

        v_layout.addLayout(hlayout)
        v_layout.addWidget(self.list_view)
        v_layout.addLayout(controls_layout)
        seek_layout = QHBoxLayout()
        
        seek_layout.addWidget(self.start_label, alignment=Qt.AlignLeft)
        seek_layout.addSpacing(10)
        seek_layout.addWidget(self.seek_slider)
        seek_layout.addSpacing(10)
        seek_layout.addWidget(self.end_label, alignment=Qt.AlignRight)
        v_layout.addLayout(seek_layout)
        v_layout.addLayout(bottom_layout)
        v_layout.addWidget(self.select_folder_btn)
        
        self.setCentralWidget(self.frame)
    
    def _connect_signals(self) -> None:
                        
        self.play_button.clicked.connect(self.play_sound)
        self.stop_button.clicked.connect(self.stop_sound)
        
                         
        self.close_btn.clicked.connect(self.close)
                                                                 
        self.minimize_btn.clicked.connect(self.showNormal)
        self.minimize_btn.clicked.connect(self.showMinimized)
        
                       
        self.audio_devices.currentTextChanged.connect(self._change_output_device)
        self.audio_input_devices.currentTextChanged.connect(self._change_input_device)
        
                         
        self.volume_slider_output.valueChanged.connect(self._update_volume)
        self.volume_slider_input.valueChanged.connect(self._update_volume)
        
                   
        self.list_view.doubleClicked.connect(self.stop_sound)
        self.list_view.doubleClicked.connect(self.play_sound)
        self.hover_delegate.buttonClicked.connect(self._on_keybind_button_clicked)
        
               
        self.select_folder_btn.setAction(lambda: QMetaObject.invokeMethod(
            self, "_select_folder", Qt.QueuedConnection))
        self.search_box.textChanged.connect(self._filter_sound_list)
        self.reload_button.clicked.connect(self.reload_list)
        self.audio_manager.player.tracksChanged.connect(self._reset_slider)
        self.audio_manager.player.positionChanged.connect(self._set_seek_slider_value)                    
        self.audio_manager.player.playbackStateChanged.connect(self._on_playback_state_changed)
        self.seek_slider.sliderPressed.connect(self._disconnect_slider)
        self.seek_slider.sliderReleased.connect(self._set_players_index)

    def _reset_slider(self) -> None:
        self.seek_slider.setMaximum(self.audio_manager.player.duration())
        self.end_label.setText(self.ms_to_hms(str(self.audio_manager.player.duration())))
        self.seek_slider.setValue(0)

    def _disconnect_slider(self)-> None:
        self.audio_manager.player.positionChanged.disconnect(self._set_seek_slider_value) 

    def _set_seek_slider_value(self) -> None:
        self.start_label.setText(self.ms_to_hms(str(self.audio_manager.player.position())))
        self.seek_slider.setValue(self.audio_manager.player.position())

    def _set_players_index(self)-> None:

        self.audio_manager.player2.setPosition(self.seek_slider.value())
        self.audio_manager.player.setPosition(self.seek_slider.value())
        self.audio_manager.player.positionChanged.connect(self._set_seek_slider_value)  
        
    def ms_to_hms(self, ms_str):
        ms = int(re.match(r'^(\d+)$', ms_str).group(1))
        hours = ms // (1000 * 60 * 60)
        minutes = (ms // (1000 * 60)) % 60
        seconds = (ms // 1000) % 60
        return f"{minutes:02d}:{seconds:02d}"

    def _initialize_audio(self) -> None:
        self.settings_manager.update_environment_variables()
        self._change_output_device()
        self._change_input_device()
    
    def _load_sounds(self) -> None:
        sound_list = self.audio_manager.get_sound_list()
        self.model.setStringList(sound_list)
    
    def _update_volume(self) -> None:
        output_volume = self.volume_slider_output.value()
        input_volume = self.volume_slider_input.value()
        
        self.settings_manager.set("VolumeOutput", output_volume)
        self.settings_manager.set("VolumeInput", input_volume)
        
        os.environ["VolumeOutput"] = str(output_volume)
        os.environ["VolumeInput"] = str(input_volume)
        
        self.volume_slider_value.setText(str(output_volume))
        self.volume_input_slider_value.setText(str(input_volume))
        
        if self.audio_manager.audio_output:
            self.audio_manager.audio_output.setVolume(output_volume / 100)
        if self.audio_manager.audio_soundboard:
            self.audio_manager.audio_soundboard.setVolume(input_volume / 100)
    
    def _change_output_device(self) -> None:
        device_name = self.audio_devices.currentText()
        self.audio_manager.setup_audio_output(device_name)
        self.settings_manager.set("DefaultOutput", device_name)
    
    def _change_input_device(self) -> None:
        device_name = self.audio_input_devices.currentText()
        self.audio_manager.setup_audio_input(device_name)
        self.settings_manager.set("DefaultInput", device_name)

    @Slot()
    def _select_folder(self) -> None:
        self.select_folder_btn.isRunning = True
        self.select_folder_btn.update()
        selected_directory = QFileDialog.getExistingDirectory(
            self, "Select Audio Directory")
        
        if selected_directory:
            os.environ["SOUNDBOARD_DIR"] = selected_directory
            self.settings_manager.set("Directory", selected_directory)
            self._load_sounds()
        self.select_folder_btn.isRunning = False
        self.select_folder_btn.update()
        
    
    @Slot(QModelIndex)
    def _on_keybind_button_clicked(self, index: QModelIndex) -> None:
        if not index.isValid():
            return
        
        action_name = self.model.data(index, Qt.DisplayRole)
        self.current_capture_action = action_name
        
        existing_key = self.hotkey_config.get_hotkey_for_action(action_name)
        self.keybind_dialog = KeybindDialog(action_name, existing_key or "", self)
        self.hotkey_listener.start_capture_mode()
        result = self.keybind_dialog.exec()
        self.hotkey_listener.stop_capture_mode()
        if result == QtWidgets.QDialog.Accepted:
            new_combo = self.keybind_dialog.get_keybind()
            if new_combo is None:
                old_combo = self.hotkey_config.get_hotkey_for_action(action_name)
                self.hotkey_config.remove_hotkey(old_combo)
            if new_combo:
                old_combo = self.hotkey_config.get_hotkey_for_action(action_name)
                if old_combo:
                    self.hotkey_config.remove_hotkey(old_combo)
                self.hotkey_config.add_hotkey(action_name, new_combo)

        self.keybind_dialog = None
        self.current_capture_action = None
            
    @Slot(str)
    def _on_key_captured(self, combo: str):
        if not combo:
            QMessageBox.information(self, "Cancelled", "Keybind capture cancelled")
            self.current_capture_action = None
            return
        
        if not self.current_capture_action:
            return
        

        old_combo = self.hotkey_config.get_hotkey_for_action(self.current_capture_action)
        if old_combo:
            self.hotkey_config.remove_hotkey(old_combo)
        

        self.hotkey_config.add_hotkey(self.current_capture_action, combo)
        self.current_capture_action = None


    def _filter_sound_list(self) -> None:
        filter_text = self.search_box.toPlainText().lower()
        all_sounds = self.audio_manager.get_sound_list()
        
        if filter_text:
            filtered_sounds = [sound for sound in all_sounds if filter_text in sound.lower()]
        else:
            filtered_sounds = all_sounds
        
        self.model.setStringList(filtered_sounds)   

    def reload_list(self) -> None:
        self._load_sounds()

    def closeEvent(self, event):
        if self.hotkey_listener:
            self.hotkey_listener.stop()
            self.hotkey_listener.wait()
        event.accept()

    def _on_playback_state_changed(self, state) -> None:
        if state == QMediaPlayer.PlaybackState.StoppedState:
            self.now_playing.setText("Now Playing: None")
            self.now_playing.setStyleSheet("color: white; border: None;background: transparent;")
            self.play_button.setIcon(QIcon(ResourceManager.get_resource_path("play.png")))
            self.seek_slider.setDisabled(True)
        elif state == QMediaPlayer.PlaybackState.PausedState:
            self.play_button.setIcon(QIcon(ResourceManager.get_resource_path("play.png")))
            self.seek_slider.setEnabled(True)
        elif state == QMediaPlayer.PlaybackState.PlayingState:
            self.play_button.setIcon(QIcon(ResourceManager.get_resource_path("pause.png")))
            self.seek_slider.setEnabled(True)
    
    def _toggle_maximize(self) -> None:
        current_state = self.windowState() 
        if current_state & Qt.WindowMaximized:
            self.showNormal()
            self.overrideWindowState(Qt.WindowNoState)
                                                                                                
        else:
            self.showMaximized()
            self.overrideWindowState(Qt.WindowMaximized)
                                                                                              
            
                                       
    def play_sound(self) -> None:
        current_state = self.audio_manager.player.playbackState()
        
        if current_state == QMediaPlayer.PlaybackState.StoppedState:
            selected_item = self.list_view.currentIndex()
            if selected_item.isValid():
                sound_name = self.model.data(selected_item, Qt.DisplayRole)
                if self._play_sound_by_name(sound_name):
                    self.now_playing.setText(f"Now Playing: {sound_name}")
                    self.now_playing.setStyleSheet("color: green; border: None;background: transparent;")
                else:
                    QMessageBox.warning(self, "Error", "Sound file not found.")
            else:
                QMessageBox.warning(self, "Error", "No sound selected.")
        elif current_state == QMediaPlayer.PlaybackState.PausedState:
            self.audio_manager.player.play()
            self.audio_manager.player2.play()
        else:
            self._pause_sound()
    
    @Slot(str)
    def _play_sound_by_name(self, sound_name: str) -> bool:
        try:
            if self.audio_manager.play_sound_file(sound_name):
                self.now_playing.setText(f"Now Playing: {sound_name}")
                self.now_playing.setStyleSheet("color: green; border: None")
                return True
            else:
                if sound_name:                                              
                    QMessageBox.warning(self, "Error", "Sound file not found.")
                return False
        except Exception:
            return False
    
    def _pause_sound(self) -> None:
        if self.audio_manager.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.audio_manager.player.pause()
            self.audio_manager.player2.pause()
    
    def stop_sound(self) -> None:
        current_state = self.audio_manager.player.playbackState()
        if current_state in [QMediaPlayer.PlaybackState.PlayingState, 
                           QMediaPlayer.PlaybackState.PausedState]:
            self.audio_manager.player.stop()
            self.audio_manager.player2.stop()
    
                           
    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.old_pos = event.globalPosition().toPoint()
            self.resize_handle = self._get_resize_handle(event.pos())
            self.resizing = self.resize_handle is not None

    def mouseMoveEvent(self, event) -> None:
        if self.resizing and self.resize_handle and self.old_pos:
            self._handle_resize(event)
        elif self.old_pos and not self.resizing:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.pos() + delta)
            self.old_pos = event.globalPosition().toPoint()
        
        
        if not self.old_pos:
            handle = self._get_resize_handle(event.pos())
            if handle:
                self._set_resize_cursor(handle)
            else:
                self.setCursor(Qt.ArrowCursor)
                self.frame.setCursor(Qt.ArrowCursor)

    def mouseReleaseEvent(self, event) -> None:
        self.old_pos = None
        self.resizing = False
        self.resize_handle = None
        self.setCursor(Qt.ArrowCursor)
        if hasattr(self, 'frame'):
            self.frame.setCursor(Qt.ArrowCursor)
        
    def _get_resize_handle(self, pos):
        
        width = self.width()
        height = self.height()
        margin = 8  
        
       
        if pos.x() <= margin and pos.y() <= margin:
            return 'top-left'
        elif pos.x() >= width - margin and pos.y() <= margin:
            return 'top-right'
        elif pos.x() <= margin and pos.y() >= height - margin:
            return 'bottom-left'
        elif pos.x() >= width - margin and pos.y() >= height - margin:
            return 'bottom-right'
        
        elif pos.x() <= margin:
            return 'left'
        elif pos.x() >= width - margin:
            return 'right'
        elif pos.y() <= margin:
            return 'top'
        elif pos.y() >= height - margin:
            return 'bottom'
        return None
    
    def _set_resize_cursor(self, handle):
        cursor_map = {
            'top-left': Qt.SizeFDiagCursor,
            'top-right': Qt.SizeBDiagCursor,
            'bottom-left': Qt.SizeBDiagCursor,
            'bottom-right': Qt.SizeFDiagCursor,
            'left': Qt.SizeHorCursor,
            'right': Qt.SizeHorCursor,
            'top': Qt.SizeVerCursor,
            'bottom': Qt.SizeVerCursor
        }
        cursor = cursor_map.get(handle, Qt.ArrowCursor)
        self.setCursor(cursor)
        if hasattr(self, 'frame'):
            self.frame.setCursor(cursor)
    
    def _handle_resize(self, event):
        
        if not self.old_pos:
            return
            
        delta = event.globalPosition().toPoint() - self.old_pos
        current_geometry = self.geometry()
        new_geometry = current_geometry
        
       
        if self.resize_handle == 'top-left':
            new_geometry.setTopLeft(current_geometry.topLeft() + delta)
        elif self.resize_handle == 'top-right':
            new_geometry.setTopRight(current_geometry.topRight() + delta)
        elif self.resize_handle == 'bottom-left':
            new_geometry.setBottomLeft(current_geometry.bottomLeft() + delta)
        elif self.resize_handle == 'bottom-right':
            new_geometry.setBottomRight(current_geometry.bottomRight() + delta)
        elif self.resize_handle == 'left':
            new_geometry.setLeft(current_geometry.left() + delta.x())
        elif self.resize_handle == 'right':
            new_geometry.setRight(current_geometry.right() + delta.x())
        elif self.resize_handle == 'top':
            new_geometry.setTop(current_geometry.top() + delta.y())
        elif self.resize_handle == 'bottom':
            new_geometry.setBottom(current_geometry.bottom() + delta.y())
        
       
        new_size = new_geometry.size()
        new_size = new_size.expandedTo(self.minimum_size)
        new_size = new_size.boundedTo(self.maximum_size)
   
        if new_size != new_geometry.size():
            if new_size.width() != new_geometry.width():
                if self.resize_handle in ['left', 'top-left', 'bottom-left']:
                    new_geometry.setLeft(new_geometry.right() - new_size.width())
                else:
                    new_geometry.setRight(new_geometry.left() + new_size.width())
            if new_size.height() != new_geometry.height():
                if self.resize_handle in ['top', 'top-left', 'top-right']:
                    new_geometry.setTop(new_geometry.bottom() - new_size.height())
                else:
                    new_geometry.setBottom(new_geometry.top() + new_size.height())
        
        self.setGeometry(new_geometry)
        self.old_pos = event.globalPosition().toPoint()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key_Escape:
            self.close()
    
    @Slot(str,str)
    def global_listener(self,key,binding) -> None:
        pass
     

# class TrayIcon(QtWidgets.QSystemTrayIcon):
#     def __init__(self, icon, parent=None):
#         super().__init__(icon, parent)
#         self.setToolTip('SoundBox')
#         menu = QtWidgets.QMenu(parent)
        
#         show_action = menu.addAction("Show")
#         quit_action = menu.addAction("Quit")
        
#         show_action.triggered.connect(parent.showNormal)
#         quit_action.triggered.connect(QApplication.instance().quit)
        
#         self.setContextMenu(menu)
#         self.activated.connect(self.onTrayIconActivated)

class LoadingScreen(QSplashScreen):
    def __init__(self, movie, parent = None):
        
        movie.jumpToFrame(0)
        pixmap = QPixmap(movie.frameRect().size())
           
        QSplashScreen.__init__(self, pixmap)
        self.movie = movie
        self.movie.frameChanged.connect(self.repaint)
        
        self.setStyleSheet("border-radius: 10px;")
    def showEvent(self, event):
         self.movie.start()
      
    def hideEvent(self, event):
        self.movie.stop()
    
    def paintEvent(self, event):
    
        painter = QPainter(self)
        pixmap = self.movie.currentPixmap()
        self.setMask(pixmap.mask())
        painter.drawPixmap(0, 0, pixmap)

    def sizeHint(self):
    
        return self.movie.scaledSize()
  

    @Slot()
    def onNextFrame(self):
        pixmap = self.movie.currentPixmap()
        self.setPixmap(pixmap)
        self.setMask(pixmap.mask())

class SoundboardApplication:
    
    def __init__(self):
        app.setApplicationName("SoundBox by BanditRN")
        app.setApplicationVersion("0.5.0")
        app.setWindowIcon(QIcon(ResourceManager.get_resource_path("window_icon.png")))                        

    def run(self) -> int:
        self.window = SoundboardWindow()
        self.window.show()
        splash.finish(self.window)
        return app.exec()
    
if __name__ == "__main__":
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
            response = requests.get("https://api.github.com/repos/BanditRN/Soundbox/releases")
            latest_version = json.loads(response.text)[0]["tag_name"]
            if latest_version != app.applicationVersion():
                QMessageBox.information(None, "Update Available", f"A new version of SoundBox is available: {latest_version}. You are using version {app.applicationVersion()}.")
            
            sys.exit(MainApp.run())
        else:
            QMessageBox.warning(None, "Warning", "Another instance of SoundBox is already running.")
            sys.exit(0)
    except Exception as e:
        
        with open(Config.LOG_FILE,"w") as f:
            f.write(f"Application error: {str(e)}")
        print(e)
        sys.exit(1)