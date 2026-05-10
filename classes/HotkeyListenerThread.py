from PySide6.QtCore import QThread, Signal
from classes.HotkeyConfig import HotkeyConfig
from typing import Optional
from pynput import keyboard


class HotkeyListenerThread(QThread):
    action_triggered = Signal(str)
    key_captured = Signal(str)

    def __init__(self, config: HotkeyConfig):
        super().__init__()
        self.config = config
        self.current_keys = set()
        self.listener: Optional[keyboard.Listener] = None
        self.capture_mode = False
        self._last_executed = None
        self._stopping = False

    def start_capture_mode(self):
        self.capture_mode = True
        self.current_keys.clear()
        self._last_executed = None

    def stop_capture_mode(self):
        self.capture_mode = False
        self.current_keys.clear()
        self._last_executed = None

    def _normalize_key(self, key) -> str:
        try:
            return key.char.lower() if key.char else ""
        except AttributeError:
            return str(key).replace("Key.", "").lower()

    def _on_press(self, key):
        key_name = self._normalize_key(key)
        if not key_name:
            return
        if self.capture_mode:
            if key_name not in self.current_keys and len(self.current_keys) < 2:
                self.current_keys.add(key_name)
                combo = "+".join(sorted(self.current_keys))
                self.key_captured.emit(combo)
            return

        self.current_keys.add(key_name)
        combo = "+".join(sorted(self.current_keys))
        action_name = self.config.get_action(combo)

        if action_name and self._last_executed != combo:
            self.action_triggered.emit(action_name)
            self._last_executed = combo

    def _on_release(self, key):
        key_name = self._normalize_key(key)
        self.current_keys.discard(key_name)
        if len(self.current_keys) == 0:
            self._last_executed = None

    def _run_listener(self):
        with keyboard.Listener(on_press=self._on_press, on_release=self._on_release) as listener:
            self.listener = listener
            listener.join()

    def run(self):
        while not self._stopping:
            self.current_keys.clear()
            self._last_executed = None
            try:
                self._run_listener()
            except Exception:
                if self._stopping:
                    break
            finally:
                self.listener = None
            if not self._stopping:
                self.msleep(200)

    def stop(self):
        self._stopping = True
        self.capture_mode = False
        self.current_keys.clear()
        self._last_executed = None
        if self.listener is not None:
            self.listener.stop()
