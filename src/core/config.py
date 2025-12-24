import os

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

