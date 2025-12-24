import sys
import os
import re
import keyboard
from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtCore import Qt, QSize, QRect, QUrl, Slot, QModelIndex, QMetaObject, QStringListModel, QTimer
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QListView, QPushButton, QSlider, QLabel, QComboBox, QFrame,
                               QInputDialog, QMessageBox, QFileDialog, QAbstractItemView, QTextEdit)
from PySide6.QtGui import QIcon, QFont, QPixmap
from PySide6.QtMultimedia import QMediaPlayer
from pyqt_loading_button import LoadingButton, AnimationType

from src.core.config import Config
from src.utils.resource_manager import ResourceManager
from src.managers.settings_manager import SettingsManager
from src.managers.audio_manager import AudioManager
from src.managers.keybind_manager import KeybindManager
from src.ui.widgets import ResizableFrame, HoverDelegate
from src.ui.style_manager import StyleManager

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
        self.setMouseTracking(True)
        
        # Apply Styles
        self.setStyleSheet(StyleManager.load_styles())

        self.minimize_animation = None
        self.keybind_manager.load_keybinds()
        

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
        self._create_keybind_dialog()
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
        self.close_btn.setObjectName("closeBtn")
        self.close_btn.setFixedSize(30, 25)
        self.minimize_btn = QPushButton('_')
        self.minimize_btn.setObjectName("minimizeBtn")
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
        self.select_folder_btn.setStyleSheet(StyleManager.get_button_style())
    
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
        
        self.frame = ResizableFrame(self.central_widget)
        self.frame.parent_window = self
        self.frame.setFrameShape(QFrame.Shape.Box)
        self.frame.setFrameShadow(QFrame.Shadow.Plain)
        self.frame.setObjectName("mainFrame")
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
        self.dialog.accepted.connect(self._set_hotkey)
        self.dialog.finished.connect(self.unhook_keybind)
        self.dialog.finished.connect(lambda: self.setEnabled(True))
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
        """Set the appropriate cursor for the resize handle"""
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
