import json
import keyboard
from PySide6 import QtCore
from PySide6.QtCore import Qt, QMetaObject
from src.core.config import Config

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
