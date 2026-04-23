import json
from typing import Dict , Optional
import os
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
