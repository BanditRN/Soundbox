from PySide6.QtMultimedia import (QMediaPlayer, QMediaDevices, QAudioOutput)
from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import QUrl
from typing import List
import os
from classes.SettingsManager import SettingsManager
from classes.Config import Config

class AudioManager:

    def __init__(self, settings_manager: SettingsManager):
        self.settings_manager = settings_manager

        self.player = QMediaPlayer()
        self.virtual_cable_player = QMediaPlayer()

        self.default_audio_output = None
        self.virtual_cable_output = None

        self.current_input_device_name = ""
        self._sound_list_cache = []
        self._sound_list_cache_dir = None

    VIRTUAL_DEVICE_KEYWORDS = (
        "cable",
        "vb-audio",
        "voicemeeter",
        "virtual",
        "vac",
    )

    def get_audio_input_devices(self) -> List:
        all_outputs = QMediaDevices.audioOutputs()
        virtual_devices = [
            dev for dev in all_outputs
            if any(kw in dev.description().lower() for kw in self.VIRTUAL_DEVICE_KEYWORDS)
        ]
        if not virtual_devices:
            QMessageBox.warning(
                None,
                "No virtual audio devices found",
                "No virtual mic / virtual cable output devices were detected.\n\n"
                "Install something like VB-Audio Virtual Cable or Voicemeeter, "
                "then restart SoundBox."
            )
        return virtual_devices

    def setup_default_audio_output(self) -> None:
        default_device = QMediaDevices.defaultAudioOutput()
        self.default_audio_output = QAudioOutput(default_device)
        volume = int(os.environ.get("VolumeInput", "50")) / 100
        self.default_audio_output.setVolume(volume)
        self.player.setAudioOutput(self.default_audio_output)

    def setup_audio_input(self, device_name: str) -> None:
        all_outputs = QMediaDevices.audioOutputs()
        selected_device = next(
            (dev for dev in all_outputs if dev.description() == device_name), None
        )

        self.current_input_device_name = ""
        self.virtual_cable_output = None

        if selected_device:
            self.virtual_cable_output = QAudioOutput(device=selected_device)
            self.current_input_device_name = device_name
            volume = int(os.environ.get("VolumeInput", "50")) / 100
            self.virtual_cable_output.setVolume(volume)
            self.virtual_cable_player.setAudioOutput(self.virtual_cable_output)

    def set_volume(self, volume_percent: int) -> None:
        vol = max(0, min(100, int(volume_percent))) / 100
        if self.default_audio_output is not None:
            self.default_audio_output.setVolume(vol)
        if self.virtual_cable_output is not None:
            self.virtual_cable_output.setVolume(vol)

    def refresh_sound_list_cache(self) -> None:
        directory = os.environ.get("SOUNDBOARD_DIR")
        self._sound_list_cache_dir = directory
        if not directory or not os.path.exists(directory):
            self._sound_list_cache = []
            return

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
            self._sound_list_cache = sound_files
        except Exception:
            self._sound_list_cache = ["NO MUSIC WAS LOADED"]

    def get_sound_list(self) -> List[str]:
        directory = os.environ.get("SOUNDBOARD_DIR")
        if directory != self._sound_list_cache_dir:
            self.refresh_sound_list_cache()
        return self._sound_list_cache

    def play_sound_file(self, sound_name: str) -> bool:
        if self.default_audio_output is None:
            self.setup_default_audio_output()

        sound_dir = os.environ.get("SOUNDBOARD_DIR", "")
        sound_path = ""
        for ext in Config.SUPPORTED_FORMATS:
            temp_path = os.path.join(sound_dir, sound_name + ext)
            if os.path.exists(temp_path):
                sound_path = temp_path
                break

        if not sound_path:
            return False

        url = QUrl.fromLocalFile(sound_path)

        self.player.setSource(url)
        self.player.play()

        if self.virtual_cable_output is not None:
            self.virtual_cable_player.setSource(url)
            self.virtual_cable_player.play()

        return True
