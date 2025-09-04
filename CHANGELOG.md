# Changelog

## 1.0.1 - 2025-09-04

### Added
- Expanded audio format support (WAV, OGG, FLAC).
- Ensured unique sound names in the sound list, preventing duplicates for different file extensions.

### Changed
- Updated README.md with detailed information about features, installation, usage, and configuration.

### Improved
- Keybind input validation: Implemented robust validation for keybind strings using `keyboard.parse_hotkey()` to prevent invalid key combinations.
- Keybind input capture: Removed problematic `keyboard.send('backspace')` and added validation for individual keys during keybind setting, leading to cleaner input.