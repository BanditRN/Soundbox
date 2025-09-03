import sys
import os
import json
import keyboard
from typing import List, Optional, Dict, Any

from PySide6 import QtCore, QtWidgets, QtGui, QtMultimedia
from PySide6.QtCore import Qt, QSize, QRect, QUrl, Signal, Slot, QModelIndex, QMetaObject, QStringListModel
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QListView, QPushButton, QSlider, QLabel, QComboBox, QFrame,
                               QStyledItemDelegate, QInputDialog, QMessageBox, QFileDialog,
                               QAbstractItemView, QStyle)
from PySide6.QtGui import QIcon, QFont
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput, QMediaDevices


from pyqt_loading_button import LoadingButton, AnimationType
import winaccent

global pressed_key
class Config:
    """Configuration constants and file management"""
    KEYBINDS_FILE = 'keybinds.json'
    SETTINGS_FILE = 'settings.json'
    
    DEFAULT_SETTINGS = {
        "Directory": "",
        "DefaultOutput": "",
        "DefaultInput": "",
        "VolumeOutput": 50,
        "VolumeInput": 50
    }
    
    WINDOW_SIZE = (800, 600)
    SUPPORTED_FORMATS = ('.mp3',)


class StyleSheets:
    """Centralized style sheets"""
    
    @staticmethod
    def get_scrollbar_style() -> str:
        return """
QScrollBar:vertical {
    border: transparent;
    background: transparent;
    width: 15px;
    margin: 22px 0 22px 0; /* Space for buttons at top and bottom */
}

QScrollBar::handle:vertical {
    background: #a0a0a0;
    min-height: 20px;
    border-radius: 5px;
}

QScrollBar::add-line:vertical {
    border: transparent;
    background: transparent;
    height: 20px;
    subcontrol-position: bottom;
    subcontrol-origin: margin;
}

QScrollBar::sub-line:vertical {
    border: transparent;
    background: transparent;
    height: 20px;
    subcontrol-position: top;
    subcontrol-origin: margin;
}

QScrollBar::add-page:vertical, QScrollBar::sub-:vertical {
    background: none; /* No background for the page area */
}
        """
    
    @staticmethod
    def get_listview_style() -> str:
        return """
        border: 2px solid blue; 
        background-color: transparent;
        QTableView {
            background-color: #f0f0f0;
            gridline-color: #cccccc;
            selection-background-color: #aaddff;
            size-adjust-policy: QAbstractScrollArea.AdjustToContents;
        }
        QHeaderView::section {
            background-color: #e0e0e0;
            padding: 4px;
            border: 1px solid #c0c0c0;
        }
        QTableView::item:selected {
            color: white;
            background-color: blue;
        }
        QTableView::item {
            font-size: 20px;
            size: 20px;
        }
        """
    
    @staticmethod
    def get_frame_style() -> str:
        return f"QFrame#mainFrame: {'{border: 2px solid '+ winaccent.accent_dark_mode + ' ; border-radius: 4px;}'}"
    
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
    """Handles resource path resolution"""
    
    @staticmethod
    def get_resource_path(relative_path: str) -> str:
        """Get the absolute path to a resource file"""
        try:
            # PyInstaller creates a temp folder and stores path in _MEIPASS
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)


class SettingsManager:
    """Manages application settings"""
    
    def __init__(self):
        self.settings = self._load_settings()
        
    
    def _load_settings(self) -> Dict[str, Any]:
        """Load settings from file or create default"""
        try:
            with open(Config.SETTINGS_FILE, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            self._save_settings(Config.DEFAULT_SETTINGS)
            return Config.DEFAULT_SETTINGS.copy()
    
    def _save_settings(self, settings: Dict[str, Any]) -> None:
        """Save settings to file"""
        with open(Config.SETTINGS_FILE, "w") as f:
            json.dump(settings, f, indent=4)
    
    def get(self, key: str, default=None):
        """Get a setting value"""
        return self.settings.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set a setting value and save"""
        self.settings[key] = value
        self._save_settings(self.settings)
    
    def update_environment_variables(self) -> None:
        """Update environment variables from settings"""
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
    """Manages keyboard shortcuts and bindings"""
    
    def __init__(self, parent):
        self.parent = parent
        self.keybinds = {}
        self.keybinds_json = {}
    
    def load_keybinds(self) -> None:
        """Load keybinds from file"""
        try:
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
        """Create default keybinds file"""
        sound_list = self.parent.audio_manager.get_sound_list()
        for item in sound_list:
            self.keybinds_json[item] = ""
        
        with open(Config.KEYBINDS_FILE, 'w') as f:
            json.dump(self.keybinds_json, f, indent=4)
    
    def save_keybinds(self) -> None:
        """Save keybinds to file"""
        with open(Config.KEYBINDS_FILE, 'w') as f:
            json.dump(self.keybinds, f, indent=4)


class AudioManager:
    """Manages audio devices and playback"""
    
    def __init__(self, settings_manager: SettingsManager):
        self.settings_manager = settings_manager
        self.player = QMediaPlayer()
        self.player2 = QMediaPlayer()
        
        
        self.audio_output = None
        self.audio_soundboard = None
        
    def get_audio_output_devices(self) -> List:
        """Get list of audio output devices"""
        devices = QMediaDevices.audioOutputs()
        if not devices:
            QMessageBox.warning(None, "Error", "No audio output devices found.")
        return devices
    
    def get_audio_input_devices(self) -> List:
        """Get list of audio input devices (using output devices for now)"""
        devices = QMediaDevices.audioOutputs()
        if not devices:
            QMessageBox.warning(None, "Error", "No audio input devices found.")
        return devices
    
    def setup_audio_output(self, device_name: str) -> None:
        """Setup audio output device"""
        devices = self.get_audio_output_devices()
        selected_device = next((dev for dev in devices if dev.description() == device_name), None)
        
        if selected_device:
            self.audio_output = QAudioOutput(selected_device)
            
            volume = int(os.environ.get("VolumeOutput", "50")) / 100
            self.audio_output.setVolume(volume)
    
    def setup_audio_input(self, device_name: str) -> None:
        """Setup audio input device"""
        devices = self.get_audio_input_devices()
        selected_device = next((dev for dev in devices if dev.description() == device_name), None)
        
        if selected_device:
            self.audio_soundboard = QAudioOutput(device=selected_device)
            volume = int(os.environ.get("VolumeInput", "50")) / 100
            self.audio_soundboard.setVolume(volume)
    
    def get_sound_list(self) -> List[str]:
        """Get list of available sound files"""
        directory = os.environ.get("SOUNDBOARD_DIR")
        if not directory or not os.path.exists(directory):
            return []
        
        try:
            sound_files = []
            for file in os.listdir(directory):
                if file.endswith(Config.SUPPORTED_FORMATS):
                    full_path = os.path.join(directory, file)
                    if os.path.exists(full_path):
                        name = file.replace(".mp3", "")
                        sound_files.append(name)
            
            # Sort by modification time, newest first
            sound_files.sort(key=lambda x: os.path.getmtime(
                os.path.join(directory, x + ".mp3")), reverse=True)
            return sound_files
        except Exception:
            return ["NO MUSIC WAS LOADED"]
    
    def play_sound_file(self, sound_name: str) -> bool:
        """Play a sound file by name"""
        
        if not self.audio_output or not self.audio_soundboard:
            return False
        
        sound_path = os.path.join(os.environ.get("SOUNDBOARD_DIR", ""), sound_name + ".mp3")
        
        if not os.path.exists(sound_path):
            return False
       
        self.player.setAudioOutput(self.audio_output)
        self.player2.setAudioOutput(self.audio_soundboard)
        
        self.player.setSource(QUrl.fromLocalFile(sound_path))
        self.player2.setSource(QUrl.fromLocalFile(sound_path))


        
        self.player.play()
        self.player2.play()
        
        return True


class HoverDelegate(QStyledItemDelegate):
    """Custom delegate for list items with hover buttons"""
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
        """Calculate button position and size"""
        button_width, button_height = 80, 20
        return QRect(
            option.rect.right() - button_width - 5,
            option.rect.top() + (option.rect.height() - button_height) // 2,
            button_width,
            button_height
        )


class SoundboardWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.set_keybind = ""
        self.old_pos = None
        
        # Initialize managers
        self.settings_manager = SettingsManager()
        self.audio_manager = AudioManager(self.settings_manager)
        self.keybind_manager = KeybindManager(self)
        
        self._setup_window()
        self._setup_global_hotkeys()
        self._create_widgets()
        self._setup_layouts()
        self._connect_signals()
        self._initialize_audio()
        self._load_sounds()
        #self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setStyleSheet(f"background: qlineargradient(x1:0 y1:0, x2:1 y2:1, stop:0 #051c2a stop:1 #44315f);")
        self.minimize_animation = None
        self.keybind_manager.load_keybinds()
        
    def changeEvent(self, event):
        if event.type() == QtCore.QEvent.Type.WindowStateChange:
            if self.isMinimized():
                # Prevent immediate system minimize
                event.ignore() 
                self.start_minimize_animation()
            elif self.isMaximized() or self.isModal():
                # Handle other state changes if needed
                pass
        super().changeEvent(event)
    def start_minimize_animation(self):
        # Store current geometry for restoration
        self._original_geometry = self.geometry()

        # Animate size and opacity
        self.minimize_animation = QtCore.QPropertyAnimation(self, b"geometry")
        self.minimize_animation.setDuration(500) # milliseconds
        self.minimize_animation.setStartValue(self.geometry())
        # Animate to a small size and move to a corner (e.g., bottom-right)
        end_rect = self.geometry().adjusted(self.width() // 2, self.height() // 2, -self.width() // 2, -self.height() // 2)
        end_rect.moveTo(self.screen().geometry().bottomRight() - QSize(50, 50)) # Example target
        self.minimize_animation.setEndValue(end_rect)

        # Connect a slot to hide/minimize after animation completes
        self.minimize_animation.finished.connect(self._finish_minimize)
        self.minimize_animation.start()
    def _finish_minimize(self):
        self.showMinimized()

    def showNormal(self):
        if hasattr(self, '_original_geometry'):
            self.setGeometry(self._original_geometry)
        super().showNormal()

    def _setup_window(self) -> None:
        """Setup window properties"""
        self.setWindowTitle("SoundBox")
        self.setWindowIcon(QIcon(ResourceManager.get_resource_path("window_icon.png")))
        self.setWindowFlags(Qt.FramelessWindowHint)
        
        # Center window on screen
        screen = QApplication.primaryScreen().availableGeometry()
        width, height = Config.WINDOW_SIZE
        x = (screen.width() - width) // 2
        y = (screen.height() - height) // 2
        self.setGeometry(x, y, width, height)
        
        
    
    def _setup_global_hotkeys(self) -> None:
        """Setup global keyboard shortcuts"""
        # keyboard.add_hotkey('space', lambda: QMetaObject.invokeMethod(
        #     self, "_hotkey_play", Qt.QueuedConnection))
        
        keyboard.add_hotkey('backspace', lambda: QMetaObject.invokeMethod(
            self, "_hotkey_stop", Qt.QueuedConnection))
    
    def _create_widgets(self) -> None:
        """Create all UI widgets"""
        self.central_widget = QWidget()
        self.central_widget.setStyleSheet("background: transparent;")

        # Media control buttons
        self._create_media_buttons()
        
        # Volume controls
        self._create_volume_controls()
        
        # Window controls
        self._create_window_controls()
        
        # Audio device selection
        self._create_audio_device_widgets()
        
        # Sound list
        self._create_sound_list_widget()
        
        # Other widgets
        self._create_other_widgets()
        
        # Keybind dialog
        self._create_keybind_dialog()

    def _create_media_buttons(self) -> None:
        """Create play/stop buttons"""
        self.play_button = self._create_icon_button("play.png", (70, 50), (50, 50))
        self.stop_button = self._create_icon_button("stop.webp", (70, 50), (50, 50))
    
    def _create_volume_controls(self) -> None:
        """Create volume sliders and labels"""
        # Output volume
        self.volume_slider_value = self._create_label(
            str(self.settings_manager.get("VolumeOutput")), 12)
        self.volume_slider_output = self._create_volume_slider("VolumeOutput")
        
        # Input volume
        self.volume_input_slider_value = self._create_label(
            str(self.settings_manager.get("VolumeInput")), 12)
        self.volume_slider_input = self._create_volume_slider("VolumeInput")
    
    def _create_window_controls(self) -> None:
        """Create window control buttons"""
        self.close_btn = self._create_window_button("close.png", (30, 25))
        self.maximize_btn = self._create_window_button("maximize.png", (30, 25))
        self.minimize_btn = self._create_window_button("minimize.png", (30, 25))
    
    def _create_audio_device_widgets(self) -> None:
        """Create audio device selection widgets"""
        # Output devices
        self.audio_devices = QComboBox()
        self.audio_devices.setStyleSheet("""QComboBox QListView
{
    
	background: radial-gradient(circle,rgba(5, 4, 4, 1) 59%, rgba(89, 89, 89, 0.66) 83%);
}""")
        devices = [dev.description() for dev in self.audio_manager.get_audio_output_devices()]
        self.audio_devices.addItems(devices)
        self.audio_devices.setCurrentText(self.settings_manager.get("DefaultOutput", ""))
        
        # Input devices
        self.audio_input_devices = QComboBox()
        self.audio_input_devices.setStyleSheet("""QComboBox QListView
{
    
	background: radial-gradient(circle,rgba(5, 4, 4, 1) 59%, rgba(89, 89, 89, 0.66) 83%);
}""")
        input_devices = [dev.description() for dev in self.audio_manager.get_audio_input_devices()]
        self.audio_input_devices.addItems(input_devices)
        self.audio_input_devices.setCurrentText(self.settings_manager.get("DefaultInput", ""))
        
        # Labels
        self.device_label = self._create_label("Select your audio Output device", 12)
        self.device_label.setStyleSheet("border: transparent;")
        
        self.input_device_label = self._create_label("Select your audio Input device", 12)
        self.input_device_label.setStyleSheet("border: transparent;")
    
    def _create_sound_list_widget(self) -> None:
        """Create sound list view"""
        self.list_view = QListView()
        self.model = QStringListModel()
        self.list_view.setModel(self.model)
        
        # Configure list view
        self.list_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.list_view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.list_view.setMouseTracking(True)
        self.list_view.setSpacing(5)
        self.list_view.setUniformItemSizes(True)
        self.list_view.setViewMode(QListView.ListMode)
        self.list_view.setResizeMode(QListView.Adjust)
        self.list_view.setWrapping(False)
        self.list_view.setIconSize(QSize(100, 40))
        self.list_view.setFont(QFont("Arial", 12))
        self.list_view.setStyleSheet(StyleSheets.get_listview_style())
        self.list_view.setStyleSheet(StyleSheets.get_scrollbar_style())
        
        # Set up delegate
        self.hover_delegate = HoverDelegate(self)
        self.list_view.setItemDelegate(self.hover_delegate)
    
    def _create_other_widgets(self) -> None:
        """Create remaining widgets"""
        
        # Now playing
        self.now_playing = QLabel("Now Playing: None")
        self.now_playing.setFont(QFont("Arial", 12))
        self.now_playing.setStyleSheet("border: none;")
        
        # Select folder button
        self.select_folder_btn = LoadingButton("Select Folder")
        self.select_folder_btn.setAnimationType(AnimationType.Circle)
        self.select_folder_btn.setAnimationSpeed(2000)
        self.select_folder_btn.setAnimationColor(QtGui.QColor(0, 0, 0))
        self.select_folder_btn.setAnimationWidth(15)
        self.select_folder_btn.setAnimationStrokeWidth(3)
        self.select_folder_btn.setStyleSheet(StyleSheets.get_button_style())
    
    def _create_keybind_dialog(self) -> None:
        """Create keybind setting dialog"""
        self.dialog = QInputDialog()
        self.dialog.setFixedSize(QSize(150, 100))
        self.dialog.setLabelText('Set your keybind')
        self.dialog.setWindowTitle('Set Keybind')
        self.dialog.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.dialog.setStyleSheet("QLabel: {background: transparent;}")
    def _create_icon_button(self, icon_file: str, size: tuple, icon_size: tuple = None) -> QPushButton:
        """Helper to create icon buttons"""
        button = QPushButton()
        button.setIcon(QIcon(ResourceManager.get_resource_path(icon_file)))
        if icon_size:
            button.setIconSize(QSize(*icon_size))
        button.setStyleSheet("background-color: transparent;border: 0px")
        button.setFlat(True)
        button.setCursor(Qt.PointingHandCursor)
        button.setFixedSize(*size)
        button.setFocusPolicy(Qt.NoFocus)
        
        return button
    def _create_window_button(self, icon_file: str, size: tuple, icon_size: tuple = None) -> QPushButton:
        """Helper to create icon buttons"""
        button = QPushButton()
        button.setIcon(QIcon(ResourceManager.get_resource_path(icon_file)))
        if icon_size:
            button.setIconSize(QSize(*icon_size))
        button.setStyleSheet("background-color: transparent;border: 0px")
        button.setFlat(True)
        
        button.setFixedSize(*size)
        button.setFocusPolicy(Qt.NoFocus)
        
        return button
    
    def _create_label(self, text: str, font_size: int) -> QLabel:
        """Helper to create labels"""
        label = QLabel(text)
        font = QFont()
        font.setPointSize(font_size)
        label.setFont(font)
        label.setStyleSheet("padding-bottom: 5px; border: transparent;")
        return label
    
    def _create_volume_slider(self, env_var: str) -> QSlider:
        """Helper to create volume sliders"""
        slider = QSlider(Qt.Horizontal)
        slider.setCursor(Qt.PointingHandCursor)
        slider.setMaximum(100)
        slider.setMinimum(0)
        slider.setValue(int(self.settings_manager.get(env_var)))
        slider.setStyleSheet("border: 0px")
        return slider
    
    def _setup_layouts(self) -> None:
        """Setup widget layouts"""
        # Main layout
        main_layout = QVBoxLayout(self.central_widget)
        main_layout.setContentsMargins(0,0,0,0)
        
        # Create frame
        
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.Box)
        frame.setFrameShadow(QFrame.Shadow.Plain)
        frame.setObjectName("mainFrame")
        frame.setStyleSheet(StyleSheets.get_frame_style())
        
        #  Title bar layout
        title_bar = QHBoxLayout()
        main_layout.addLayout(title_bar)
        title_bar.setSpacing(0)
        title_text = QLabel("SoundBox", textFormat=Qt.PlainText)
        title_text.setFont(QFont("Arial", 16, QFont.Bold))
        title_bar.addWidget(title_text, alignment=Qt.AlignLeft)
        title_bar.addWidget(self.minimize_btn, alignment=Qt.AlignRight)
        title_bar.addWidget(self.maximize_btn, alignment=Qt.AlignRight)
        title_bar.addWidget(self.close_btn, alignment=Qt.AlignRight)
        title_bar.setContentsMargins(10,10,10,0)


        # Main vertical layout
        v_layout = QVBoxLayout()
        v_layout.setContentsMargins(10, 10, 10, 10)
        v_layout.setSpacing(10)
        main_layout.addLayout(v_layout)

        main_layout.addWidget(frame)

        # Control buttons layout
        controls_layout = QHBoxLayout()
        controls_layout.setAlignment(Qt.AlignCenter | Qt.AlignBottom)
        controls_layout.addWidget(self.play_button)
        controls_layout.addWidget(self.stop_button)
        
        # Bottom layout
        bottom_layout = QHBoxLayout()
        bottom_layout.setAlignment(Qt.AlignCenter | Qt.AlignBottom)
        
        # Audio output layout
        output_layout = QVBoxLayout()
        output_layout.setAlignment(Qt.AlignLeft)
        output_layout.addWidget(self.device_label, alignment=Qt.AlignCenter)
        output_layout.addWidget(self.audio_devices)
        output_layout.addWidget(self.volume_slider_value, alignment=Qt.AlignCenter)
        output_layout.addWidget(self.volume_slider_output)
        
        # Audio input layout
        input_layout = QVBoxLayout()
        input_layout.setAlignment(Qt.AlignRight)
        input_layout.addWidget(self.input_device_label, alignment=Qt.AlignCenter)
        input_layout.addWidget(self.audio_input_devices)
        input_layout.addWidget(self.volume_input_slider_value, alignment=Qt.AlignCenter)
        input_layout.addWidget(self.volume_slider_input)
        
        bottom_layout.addLayout(output_layout)
        bottom_layout.addSpacing(200)
        bottom_layout.addLayout(input_layout)
        
        # Add all layouts to main layout
        #v_layout.addLayout(title_layout)
        v_layout.addWidget(self.now_playing, alignment=Qt.AlignCenter)
        v_layout.addWidget(self.list_view)
        v_layout.addLayout(controls_layout)
        v_layout.addLayout(bottom_layout)
        v_layout.addWidget(self.select_folder_btn)
        
        self.setCentralWidget(self.central_widget)
    
    def _connect_signals(self) -> None:
        """Connect widget signals to slots"""
        # Media controls
        self.play_button.clicked.connect(self.play_sound)
        self.stop_button.clicked.connect(self.stop_sound)
        
        # Window controls
        self.close_btn.clicked.connect(self.close)
        self.maximize_btn.clicked.connect(self._toggle_maximize)
        self.minimize_btn.clicked.connect(self.showNormal)
        self.minimize_btn.clicked.connect(self.showMinimized)
        
        # Audio devices
        self.audio_devices.currentTextChanged.connect(self._change_output_device)
        self.audio_input_devices.currentTextChanged.connect(self._change_input_device)
        
        # Volume controls
        self.volume_slider_output.valueChanged.connect(self._update_volume)
        self.volume_slider_input.valueChanged.connect(self._update_volume)
        
        # List view
        self.list_view.doubleClicked.connect(self.stop_sound)
        self.list_view.doubleClicked.connect(self.play_sound)
        self.hover_delegate.buttonClicked.connect(self._on_keybind_button_clicked)
        
        # Other
        self.select_folder_btn.clicked.connect(self._select_folder)
        self.dialog.accepted.connect(self._set_hotkey)
        self.dialog.finished.connect(self.unhook_keybind)


        # Player state changes
        self.audio_manager.player.playbackStateChanged.connect(self._on_playback_state_changed)
    
    def _initialize_audio(self) -> None:
        """Initialize audio system"""
        self.settings_manager.update_environment_variables()
        self._change_output_device()
        self._change_input_device()
    
    def _load_sounds(self) -> None:
        """Load sound files into the list"""
        sound_list = self.audio_manager.get_sound_list()
        self.model.setStringList(sound_list)
    
    # Event handlers and slots
    @Slot()
    def _hotkey_play(self):
        """Global hotkey handler for play"""
        self.play_sound()
    
    @Slot()
    def _hotkey_stop(self):
        """Global hotkey handler for stop"""
        self.stop_sound()
    
    @Slot(str)
    def _hotkey_play_sound(self, sound: str):
        """Global hotkey handler for specific sound"""
        self._play_sound_by_name(sound)
    
    def _update_volume(self) -> None:
        """Update volume settings"""
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
        """Change audio output device"""
        device_name = self.audio_devices.currentText()
        self.audio_manager.setup_audio_output(device_name)
        self.settings_manager.set("DefaultOutput", device_name)
    
    def _change_input_device(self) -> None:
        """Change audio input device"""
        device_name = self.audio_input_devices.currentText()
        self.audio_manager.setup_audio_input(device_name)
        self.settings_manager.set("DefaultInput", device_name)
    
    def _select_folder(self) -> None:
        """Select sound folder"""
        self.select_folder_btn.isRunning = True
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
    
    @Slot(QModelIndex)
    def _on_keybind_button_clicked(self, index: QModelIndex) -> None:
        """Handle keybind button click"""
        global pressed_key
        self.dialog.show()
        try:
            existing_key = self.keybind_manager.keybinds[self.model.data(self.list_view.currentIndex(), Qt.DisplayRole)]
        except KeyError:
            existing_key= ""
        self.dialog.setTextValue(existing_key)
        pressed_key = []
        self.fkeys = [f"f{i}" for i in range(1, 13)]
        keyboard.hook(self._keyboard_input_hook)

    def _keyboard_input_hook(self, e) -> None:
            """Hook keyboard input for keybind setting"""
            global pressed_key
            if e.event_type == "down":
                match e.name:
                    case 'backspace':
                        return
                    case 'space':
                        return
                pressed_key.append(e.name)
                pressed_key = list(set(pressed_key))
                self.dialog.setTextValue("+".join(str(key) for key in pressed_key))
                if e.name not in self.fkeys:
                    keyboard.send('backspace')                 
                self.set_keybind = self.dialog.textValue()       
            else:
                return
    @Slot()
    def unhook_keybind(self):
        keyboard.unhook(self._keyboard_input_hook)

    @Slot(int)
    def _set_hotkey(self) -> None:
        """Set hotkey for selected sound"""
        index = self.list_view.currentIndex()
        if not index.isValid():
            return 
        action_name = self.model.data(index, Qt.DisplayRole)
        self.keybind_manager.keybinds[action_name] = self.dialog.textValue() 
        self.keybind_manager.save_keybinds()
        self.keybind_manager.load_keybinds()
        
        

    
    def _on_playback_state_changed(self, state) -> None:
        """Handle media player state changes"""
        if state == QMediaPlayer.PlaybackState.StoppedState:
            self.now_playing.setText("Now Playing: None")
            self.now_playing.setStyleSheet("color: white; border: None")
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
            self.maximize_btn.setIcon(QIcon(ResourceManager.get_resource_path("max.svg")))
        else:
            self.showMaximized()
            self.overrideWindowState(Qt.WindowMaximized)
            self.maximize_btn.setIcon(QIcon(ResourceManager.get_resource_path("normal.svg")))
            
    # Public methods for sound playback
    def play_sound(self) -> None:
        """Play selected sound or pause/resume current playback"""
        current_state = self.audio_manager.player.playbackState()
        
        if current_state == QMediaPlayer.PlaybackState.StoppedState:
            selected_item = self.list_view.currentIndex()
            if selected_item.isValid():
                sound_name = self.model.data(selected_item, Qt.DisplayRole)
                if self._play_sound_by_name(sound_name):
                    self.now_playing.setText(f"Now Playing: {sound_name}")
                    self.now_playing.setStyleSheet("color: green; border: None")
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
        """Play sound by name (for keybind triggers)"""
        try:
            if self.audio_manager.play_sound_file(sound_name):
                self.now_playing.setText(f"Now Playing: {sound_name}")
                self.now_playing.setStyleSheet("color: green; border: None")
                return True
            else:
                if sound_name:  # Only show error if sound name is not empty
                    QMessageBox.warning(self, "Error", "Sound file not found.")
                return False
        except Exception:
            return False
    
    def _pause_sound(self) -> None:
        """Pause current playback"""
        if self.audio_manager.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.audio_manager.player.pause()
            self.audio_manager.player2.pause()
    
    def stop_sound(self) -> None:
        """Stop current playback"""
        current_state = self.audio_manager.player.playbackState()
        if current_state in [QMediaPlayer.PlaybackState.PlayingState, 
                           QMediaPlayer.PlaybackState.PausedState]:
            self.audio_manager.player.stop()
            self.audio_manager.player2.stop()
    
    # Window event handlers
    def mousePressEvent(self, event) -> None:
        """Handle mouse press for window dragging"""
        if event.button() == Qt.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event) -> None:
        """Handle mouse move for window dragging"""
        if self.old_pos:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.pos() + delta)
            self.old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event) -> None:
        """Handle mouse release for window dragging"""
        self.old_pos = None
        
    def keyPressEvent(self, event) -> None:
        """Handle key press events"""
        if event.key() == Qt.Key_Escape:
            self.close()


class SoundboardApplication:
    """Main application class"""
    
    def __init__(self):
        self.app = QApplication(sys.argv)
        self._setup_application()
        self.window = SoundboardWindow()
    
    def _setup_application(self) -> None:
        """Setup application properties"""
        self.app.setStyle("Fusion")
        self.app.setApplicationName("SoundBox by BanditRN")
        self.app.setApplicationVersion("1.0.0")
        self.app.setWindowIcon(QIcon(ResourceManager.get_resource_path("window_icon.png")))
    
    def run(self) -> int:
        """Run the application"""
        self.window.show()
        return self.app.exec()


def main():
    """Main entry point"""
    try:
        app = SoundboardApplication()
        sys.exit(app.run())
    except Exception as e:
        print(f"Application error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()