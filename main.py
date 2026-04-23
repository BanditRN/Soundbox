import sys
import os
import json
import re
from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtCore import Qt, QSize, Slot, QModelIndex, QMetaObject, QStringListModel
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QListView, QPushButton, QSlider, QLabel, QComboBox,
                               QMessageBox, QFileDialog, QAbstractItemView, QTextEdit)
from PySide6.QtGui import QIcon, QFont
from PySide6.QtMultimedia import QMediaPlayer
from pyqt_loading_button import LoadingButton, AnimationType
import winaccent
import requests

from classes.Config import Config
from classes.Stylesheets import Stylesheets
from classes.SettingsManager import SettingsManager
from classes.AudioManager import AudioManager
from classes.HotkeyConfig import HotkeyConfig
from classes.HoverDelegate import HoverDelegate
from classes.HotkeyListenerThread import HotkeyListenerThread
from classes.KeybindDialog import KeybindDialog

os.environ["QT_LOGGING_RULES"] = "*.ffmpeg.*=false"
class ResourceManager:
    
    @staticmethod
    def get_resource_path(relative_path: str) -> str:
        try:
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath("./resources")
        return os.path.join(base_path, relative_path)


class SoundboardWindow(QMainWindow):
    
    def __init__(self):
        super().__init__()
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
                           QWidget#centralwidget{
                           border-top-left-radius: 0px;
                           border-top-right-radius: 0px;
                           }
                           QPushButton{
                           background: transparent;
                           }
                           QPushButton#reloadBtn:hover:!pressed , QPushButton#stopkeybind_btn:hover:!pressed{
                           background-color: #363637;
                           }
                           QPushButton:hover:pressed{
                           background-color: #141417
                           }
                           QComboBox#audio_input_devices{
                           color: white;
                           background: radial-gradient(circle,rgba(5, 4, 4, 1) 59%, rgba(89, 89, 89, 0.66) 83%);
                           border: 1px solid """+ winaccent.accent_dark_1 +""";
                           height: 20px;
                           }
                           QComboBox#audio_input_devices QListView
                           {
                           border: 0px;
                           background: radial-gradient(circle,rgba(5, 4, 4, 1) 59%, rgba(89, 89, 89, 0.66) 83%);
                           color: white;
                           }
                           QComboBox#audio_input_devices::drop-down:button{
                           background: transparent;
                            border: 0px;
                           }
                           QComboBox#audio_input_devices::down-arrow{
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
                            border: 2px solid """ + winaccent.accent_dark_1 + """
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
                            background: grey;
                            border-radius: 5px;
                            background: """ + winaccent.accent_dark_1 + """;
                            }
                           """)

        self.minimize_animation = None

        QMetaObject.invokeMethod(
            self, "_start_hotkey_listener", Qt.QueuedConnection)
        
    @Slot()
    def _start_hotkey_listener(self):
        self.hotkey_listener = HotkeyListenerThread(self.hotkey_config)
        self.hotkey_listener.action_triggered.connect(self._execute_hotkey_action)
        self.hotkey_listener.key_captured.connect(self._update_keybind_dialog)
        self.hotkey_listener.start()
    
    @Slot(str)
    def _execute_hotkey_action(self, action_name: str):
        if action_name == "stop sound":
            self.stop_sound()
            return
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
        self.reload_button = self._create_icon_button("reload.png", (30, 30), (20, 20))
        self.reload_button.setObjectName("reloadBtn")
        self.stop_button = self._create_icon_button("stop.webp", (70, 50), (50, 50))
        self.stopkeybind_btn = self._create_icon_button("stop_keybind.png", (30, 30), (20, 20))
        self.stopkeybind_btn.setObjectName("stopkeybind_btn")
        self.stopkeybind_btn.setToolTip("Set keybind for Stop action")

    def _create_volume_controls(self) -> None:
        self.volume_input_slider_value = self._create_label(
            str(self.settings_manager.get("VolumeInput", 50)), 12)
        self.volume_slider_input = self._create_volume_slider("VolumeInput")
        self.volume_slider_input.setFocusPolicy(Qt.NoFocus)

    def _create_audio_device_widgets(self) -> None:
        self.audio_input_devices = QComboBox()
        self.audio_input_devices.setObjectName("audio_input_devices")
        input_devices = [dev.description() for dev in self.audio_manager.get_audio_input_devices()]
        self.audio_input_devices.addItems(input_devices)
        self.audio_input_devices.setCurrentText(self.settings_manager.get("DefaultInput", ""))
        self.input_device_label = self._create_label("Select Virtual Cable / Mic Output", 12)

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
        self.list_view.setStyleSheet(Stylesheets.get_scrollbar_style())
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
        self.search_box.setFixedHeight(25)
        self.search_box.setFixedWidth(150)

        self.select_folder_btn = LoadingButton(self)
        self.select_folder_btn.setText("Select Sound Folder")
        self.select_folder_btn.setAnimationType(AnimationType.Circle)
        self.select_folder_btn.setAnimationSpeed(2000)
        self.select_folder_btn.setAnimationColor(QtGui.QColor(0, 0, 0))
        self.select_folder_btn.setAnimationWidth(15)
        self.select_folder_btn.setAnimationStrokeWidth(3)
        self.select_folder_btn.setStyleSheet(Stylesheets.get_button_style())

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
        main_layout.setContentsMargins(0, 0, 0, 0)
        for widget in self.central_widget.children():
            if isinstance(widget, QLabel) or isinstance(widget, QPushButton):
                widget.setStyleSheet("background: transparent;")

        title_bar = QHBoxLayout()
        title_bar.setSpacing(0)
        title_text = QLabel("SoundBox", textFormat=Qt.PlainText)
        title_text.setFont(QFont("Arial", 16, QFont.Bold))
        title_text.setStyleSheet("color: white; border: None;background: transparent;padding-top: 5px;")
        title_bar.addWidget(title_text, alignment=Qt.AlignLeft)
        title_bar.addStretch()
        title_bar.setContentsMargins(10, 0, 0, 10)

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

        input_layout = QVBoxLayout()
        input_layout.setAlignment(Qt.AlignCenter)
        input_layout.addWidget(self.input_device_label, alignment=Qt.AlignCenter)
        input_layout.addWidget(self.audio_input_devices)
        input_layout.addWidget(self.volume_input_slider_value, alignment=Qt.AlignCenter)
        input_layout.addWidget(self.volume_slider_input)

        bottom_layout.addLayout(input_layout)

        hlayout = QHBoxLayout()
        hlayout.addWidget(self.search_box, alignment=Qt.AlignLeft)
        hlayout.addSpacing(170)
        hlayout.addWidget(self.now_playing, alignment=Qt.AlignCenter)
        hlayout.addSpacing(1000)
        hlayout.addWidget(self.stopkeybind_btn, alignment=Qt.AlignRight)
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

        self.setCentralWidget(self.central_widget)
    
    def _connect_signals(self) -> None:
        self.play_button.clicked.connect(self.play_sound)
        self.stop_button.clicked.connect(self.stop_sound)
        self.audio_input_devices.currentTextChanged.connect(self._change_input_device)
        self.volume_slider_input.valueChanged.connect(self._update_volume)
        self.list_view.doubleClicked.connect(self.stop_sound)
        self.list_view.doubleClicked.connect(self.play_sound)
        self.hover_delegate.buttonClicked.connect(self._on_keybind_button_clicked)
        self.stopkeybind_btn.clicked.connect(self._on_keybind_button_clicked)

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

    def _disconnect_slider(self) -> None:
        self.audio_manager.player.positionChanged.disconnect(self._set_seek_slider_value)

    def _set_seek_slider_value(self) -> None:
        self.start_label.setText(self.ms_to_hms(str(self.audio_manager.player.position())))
        self.seek_slider.setValue(self.audio_manager.player.position())

    def _set_players_index(self) -> None:
        pos = self.seek_slider.value()
        self.audio_manager.player.setPosition(pos)
        if self.audio_manager.virtual_cable_output is not None:
            self.audio_manager.virtual_cable_player.setPosition(pos)
        self.audio_manager.player.positionChanged.connect(self._set_seek_slider_value)

    def ms_to_hms(self, ms_str):
        ms = int(re.match(r'^(\d+)$', ms_str).group(1))
        minutes = (ms // (1000 * 60)) % 60
        seconds = (ms // 1000) % 60
        return f"{minutes:02d}:{seconds:02d}"

    def _initialize_audio(self) -> None:
        self.settings_manager.update_environment_variables()
        self.audio_manager.setup_default_audio_output()
        self._change_input_device()
        self.audio_manager.set_volume(int(self.settings_manager.get("VolumeInput", 50)))
    
    def _load_sounds(self) -> None:
        sound_list = self.audio_manager.get_sound_list()
        self.model.setStringList(sound_list)
    
    def _update_volume(self) -> None:
        if self.sender() == self.volume_slider_input:
            input_volume = self.volume_slider_input.value()
            self.settings_manager.set("VolumeInput", input_volume)
            os.environ["VolumeInput"] = str(input_volume)
            self.volume_input_slider_value.setText(str(input_volume))
            self.audio_manager.set_volume(input_volume)
    
    def _change_input_device(self) -> None:
        device_name = self.audio_input_devices.currentText()
        self.audio_manager.setup_audio_input(device_name)
        self.settings_manager.set("DefaultInput", device_name)
        self.audio_manager.set_volume(int(self.settings_manager.get("VolumeInput", 50)))

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
        sender = self.sender()
        if sender == self.stopkeybind_btn:
            action_name = "stop sound"
        else:
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

    def _filter_sound_list(self) -> None:
        filter_text = self.search_box.toPlainText().lower()
        all_sounds = self.audio_manager.get_sound_list()
        
        if filter_text:
            filtered_sounds = [sound for sound in all_sounds if filter_text in sound.lower()]
        else:
            filtered_sounds = all_sounds
        
        self.model.setStringList(filtered_sounds)

    def reload_list(self) -> None:
        self.audio_manager.refresh_sound_list_cache()
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
            if self.audio_manager.virtual_cable_output is not None:
                self.audio_manager.virtual_cable_player.play()
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
            if self.audio_manager.virtual_cable_output is not None:
                self.audio_manager.virtual_cable_player.pause()
    
    def stop_sound(self) -> None:
        current_state = self.audio_manager.player.playbackState()
        if current_state in [QMediaPlayer.PlaybackState.PlayingState, 
                           QMediaPlayer.PlaybackState.PausedState]:
            self.audio_manager.player.stop()
            if self.audio_manager.virtual_cable_output is not None:
                self.audio_manager.virtual_cable_player.stop()
            self.end_label.setText("00:00")
    
    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key_Escape:
            self.close()

class SoundboardApplication:
    
    def __init__(self):
        app.setApplicationName("SoundBox by BanditRN")
        app.setApplicationVersion("0.7.0")
        app.setWindowIcon(QIcon(ResourceManager.get_resource_path("window_icon.png")))

    def run(self) -> int:
        self.window = SoundboardWindow()
        self.window.show()
        return app.exec()
    
if __name__ == "__main__":
    try:
        lockfile = QtCore.QLockFile(QtCore.QDir.tempPath() + '/Soundbox.lock')
        global app
        app = QApplication(sys.argv)
        if lockfile.tryLock(100):
            MainApp = SoundboardApplication()
            try:
                response = requests.get("https://api.github.com/repos/BanditRN/Soundbox/releases", timeout=5)
                latest_version = json.loads(response.text)[0]["tag_name"]
                if latest_version > app.applicationVersion():
                    QMessageBox.information(None, "Update Available", f"A new version of SoundBox is available: {latest_version}. You are using version {app.applicationVersion()}.<br>Please go to <a href = 'https://github.com/BanditRN/Soundbox/releases'>Github Releases</a>")
            except requests.RequestException:
                pass
            app.processEvents()
            sys.exit(MainApp.run())
        else:
            QMessageBox.warning(None, "Warning", "Another instance of SoundBox is already running.")
            sys.exit(0)
    except Exception as e:
        with open(Config.LOG_FILE, "w") as f:
            f.write(f"Application error: {str(e)}")
        print(e)
        sys.exit(1)
