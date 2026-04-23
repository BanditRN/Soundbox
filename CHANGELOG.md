# Changelog

## 0.7.0

### Changed
- Removed the in-app audio output device selector. The playback output is now controlled exclusively from Windows (the system default audio output device).
- Reduced the player count from **three to two**, eliminating the redundant player that previously caused doubled audio:
  - `player` → Windows default audio output (always active, so the user always hears playback on whatever device Windows is currently set to).
  - `virtual_cable_player` → user-selected virtual cable output device (only active when a virtual cable is selected, so apps like Discord/OBS pick up the sound through the corresponding "CABLE Output" recording device).
- The virtual mic ComboBox now lists **virtual cable / virtual audio output devices only** (e.g. *CABLE Input*, *VB-Audio*, *Voicemeeter*, *VAC*). VB-Audio's CABLE Input is exposed by Windows as an audio **output** device — that's the sink the soundboard writes into. Real microphones and unrelated input devices are no longer shown.
- Pause / resume / stop / seek now apply to both players in sync.

### Removed
- `audio_devices` ComboBox and "Select your audio Output device" label from the UI.
- Output volume slider and its label. The remaining (input) volume slider now applies to **both** active outputs.
- `get_audio_output_devices()` and `setup_audio_output()` from `AudioManager`.
- The previous redundant third `QMediaPlayer` (`default_output_player`) that duplicated the user-selected output and caused doubled audio.
- `DefaultOutput`, `DefaultWindowsOutput`, `VolumeWindowsOutput`, and `VolumeOutput` settings (no longer needed).

### Notes
- Users must change the audio output device through the Windows sound settings.
- App version bumped from `0.6.0` → `0.7.0`.

## 1.0.1 - 2025-09-04

### Added
- Expanded audio format support (WAV, OGG, FLAC).
- Ensured unique sound names in the sound list, preventing duplicates for different file extensions.

### Changed
- Updated README.md with detailed information about features, installation, usage, and configuration.
