import json
import os
from typing import Dict, Any
from src.core.config import Config

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
