import sys
import os
import json
import keyboard
from typing import List, Dict, Any

from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtCore import Qt, QSize, QRect, QUrl, Signal, Slot, QModelIndex, QMetaObject, QStringListModel,QTimer, SLOT,SIGNAL,QEventLoop
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QListView, QPushButton, QSlider, QLabel, QComboBox, QFrame,
                               QStyledItemDelegate, QInputDialog, QMessageBox, QFileDialog,
                               QAbstractItemView, QStyle , QTextEdit , QSplashScreen)
from PySide6.QtGui import QIcon, QFont, QPixmap, QMovie,QPainter
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput, QMediaDevices
from multiprocessing import Pool
from pyqt_loading_button import LoadingButton, AnimationType
import winaccent

os.environ["QT_LOGGING_RULES"] = "*.ffmpeg.*=false"
global pressed_key
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


class KeybindManager:
    
    def __init__(self, parent):
        self.parent = parent
        self.keybinds = {}
        self.keybinds_json = {}

    def _setup_fixed_stop(self) -> None:
        keyboard.add_hotkey('backspace', lambda: QMetaObject.invokeMethod(
            self.parent, "_hotkey_stop", Qt.QueuedConnection))
        
    def load_keybinds(self) -> None:
        try:
            keyboard.unhook_all()
            self._setup_fixed_stop()
            with open(Config.KEYBINDS_FILE, 'r') as f:
                self.keybinds_json = json.load(f)
            
            for key, binding in self.keybinds_json.items():
                if binding:
                    self.keybinds[key] = binding
                    keyboard.add_hotkey(
                        binding, 
                        lambda sound=key: QMetaObject.invokeMethod(
                            self.parent, "_hotkey_play_sound", 
                            Qt.QueuedConnection, 
                            QtCore.Q_ARG(str, str(sound))
                        )
                    )
        except FileNotFoundError:
            self._create_default_keybinds()
    
    def _create_default_keybinds(self) -> None:
        self._setup_fixed_stop()
        sound_list = self.parent.audio_manager.get_sound_list()
        for item in sound_list:
            self.keybinds_json[item] = ""
        
        with open(Config.KEYBINDS_FILE, 'w') as f:
            json.dump(self.keybinds_json, f, indent=4)
    
    def save_keybinds(self) -> None:
        with open(Config.KEYBINDS_FILE, 'w') as f:
            json.dump(self.keybinds, f, indent=4)


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
        button_width, button_height = 80, 20
        return QRect(
            option.rect.right() - button_width - 5,
            option.rect.top() + (option.rect.height() - button_height) // 2,
            button_width,
            button_height
        )


class SoundboardWindow(QMainWindow):
    
    def __init__(self):
        super().__init__()
        self.set_keybind = ""
        self.old_pos = None
        
                             
        self.settings_manager = SettingsManager()
        self.audio_manager = AudioManager(self.settings_manager)
        self.keybind_manager = KeybindManager(self)
        
        self._setup_window()
        self._create_widgets()
        self._setup_layouts()
        self._connect_signals()
        self._initialize_audio()
        self._load_sounds()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowModality(QtCore.Qt.ApplicationModal)
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
                            QTextEdit{
                            color: white;
                            }
                           """)
        

        self.minimize_animation = None
        self.keybind_manager.load_keybinds()
        
    def changeEvent(self, event):
        if event.type() == QtCore.QEvent.Type.WindowStateChange:
            if self.isMinimized():
                                                   
                event.ignore() 
                self.start_minimize_animation()
            elif self.isMaximized() or self.isModal():
                                                      
                pass
        super().changeEvent(event)
    def start_minimize_animation(self):
                                                
        self._original_geometry = self.geometry()

                                  
        self.minimize_animation = QtCore.QPropertyAnimation(self, b"geometry")
        self.minimize_animation.setDuration(500)               
        self.minimize_animation.setStartValue(self.geometry())
                                                                           
        end_rect = self.geometry().adjusted(self.width() // 2, self.height() // 2, -self.width() // 2, -self.height() // 2)
        end_rect.moveTo(self.screen().geometry().bottomRight() - QSize(50, 50))                 
        self.minimize_animation.setEndValue(end_rect)

                                                                   
        self.minimize_animation.finished.connect(self._finish_minimize)
        self.minimize_animation.start()
    def _finish_minimize(self):
        self.showMinimized()

    def showNormal(self):
        if hasattr(self, '_original_geometry'):
            self.setGeometry(self._original_geometry)
        super().showNormal()

    def _setup_window(self) -> None:
        self.setWindowTitle("SoundBox")
        self.setWindowIcon(QIcon(ResourceManager.get_resource_path("window_icon.png")))
        self.setWindowFlags(Qt.FramelessWindowHint)
        
                                 
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
        
                        
        self._create_keybind_dialog()

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
    
    def _create_keybind_dialog(self) -> None:
        self.dialog = QInputDialog()
        self.dialog.setFixedSize(QSize(150, 100))
        self.dialog.setLabelText('Set your keybind')
        self.dialog.setWindowTitle('Set Keybind')
        self.dialog.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.dialog.setStyleSheet("QLabel: {background: transparent;}")
        self.dialog.setModal(True)

    def make_readonly(self) -> None:
        if self.dialog.isVisible():
            self.line_edit = self.dialog.findChild(QtWidgets.QLineEdit)
            self.line_edit
            self.line_edit.setReadOnly(True)

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
        
                      
        
        self.frame = QFrame(self.central_widget)
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
        self.dialog.accepted.connect(self._set_hotkey)
        self.dialog.finished.connect(self.unhook_keybind)
        self.dialog.finished.connect(lambda: self.setEnabled(True))
        self.reload_button.clicked.connect(self.reload_list)
        
                              
        self.audio_manager.player.playbackStateChanged.connect(self._on_playback_state_changed)
    
    def _initialize_audio(self) -> None:
        self.settings_manager.update_environment_variables()
        self._change_output_device()
        self._change_input_device()
    
    def _load_sounds(self) -> None:
        sound_list = self.audio_manager.get_sound_list()
        self.model.setStringList(sound_list)
    
                              
    @Slot()
    def _hotkey_play(self):
        self.play_sound()
    
    @Slot()
    def _hotkey_stop(self):
        self.stop_sound()
    
    @Slot(str)
    def _hotkey_play_sound(self, sound: str):
        self._play_sound_by_name(sound)
    
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
            self.keybind_manager.keybinds.clear() 
            self.keybind_manager.keybinds_json.clear()
            self.keybind_manager.save_keybinds()
            self._load_sounds()
            self.keybind_manager.load_keybinds()
        self.select_folder_btn.isRunning = False
        self.select_folder_btn.update()
        
    
    @Slot(QModelIndex)
    def _on_keybind_button_clicked(self, index: QModelIndex) -> None:
        global pressed_key
        QTimer.singleShot(0, self.make_readonly)
        self.dialog.show()
        self.setEnabled(False)
        try:
            existing_key = self.keybind_manager.keybinds[self.model.data(self.list_view.currentIndex(), Qt.DisplayRole)]
        except KeyError:
            existing_key= ""
        self.dialog.setTextValue(existing_key)
        pressed_key = []
        self.fkeys = [f"f{i}" for i in range(1, 13)]
        keyboard.hook(self._keyboard_input_hook)

    def _keyboard_input_hook(self, e) -> None:
        global pressed_key
        if e.event_type == "down":
            match e.name:
                case 'backspace':
                    self.line_edit.backspace()
                    if pressed_key:
                        pressed_key.pop()
                    return
                case 'space':
                    return
                case 'enter':
                    return

            pressed_key.append(e.name)
            pressed_key = list(set(pressed_key))
            self.dialog.setTextValue('+'.join(str(key) for key in pressed_key))    
            self.set_keybind = self.dialog.textValue()       
        else:
            return
    @Slot()
    def unhook_keybind(self):
        keyboard.unhook(self._keyboard_input_hook)

    @Slot(int)
    def _set_hotkey(self) -> None:
        index = self.list_view.currentIndex()
        if not index.isValid():
            return 
        action_name = self.model.data(index, Qt.DisplayRole)
        try:
            if self.dialog.textValue() == "":
                keyboard.remove_hotkey(self.keybind_manager.keybinds[action_name])
        except:
            self.reload_list()
            return

        self.keybind_manager.keybinds[action_name] = self.dialog.textValue() 
        self.reload_list()
        
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
        self.keybind_manager.save_keybinds()
        self.keybind_manager.load_keybinds()
    
    def _on_playback_state_changed(self, state) -> None:
        if state == QMediaPlayer.PlaybackState.StoppedState:
            self.now_playing.setText("Now Playing: None")
            self.now_playing.setStyleSheet("color: white; border: None;background: transparent;")
            self.play_button.setIcon(QIcon(ResourceManager.get_resource_path("play.png")))
        elif state == QMediaPlayer.PlaybackState.PausedState:
            self.play_button.setIcon(QIcon(ResourceManager.get_resource_path("play.png")))
        elif state == QMediaPlayer.PlaybackState.PlayingState:
            self.play_button.setIcon(QIcon(ResourceManager.get_resource_path("pause.png")))
    
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

    def mouseMoveEvent(self, event) -> None:
        if self.old_pos:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.pos() + delta)
            self.old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event) -> None:
        self.old_pos = None
        
    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key_Escape:
            self.close()

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
        app.setApplicationVersion("0.2.1")
        app.setWindowIcon(QIcon(ResourceManager.get_resource_path("window_icon.png")))                        

    def run(self) -> int:
        self.window = SoundboardWindow()
        self.window.show()
        splash.finish(self.window)
        return app.exec()


def main():
    try:
        lockfile = QtCore.QLockFile(QtCore.QDir.tempPath() + '/Soundbox.lock')
        if lockfile.tryLock(100):
            global app
            app = QApplication(sys.argv)
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