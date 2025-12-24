import os
from typing import List
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput, QMediaDevices
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QMessageBox
from src.core.config import Config
from src.managers.settings_manager import SettingsManager

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
