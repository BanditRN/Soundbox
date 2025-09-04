# SoundBox by BanditRN

SoundBox is a feature-rich soundboard application built with Python and PySide6, designed to provide a seamless audio experience with customizable hotkeys and intuitive controls.

## Key Features:

*   **Audio Playback:** Play your favorite sound files with dedicated controls.
*   **Customizable Keybinds:** Assign global hotkeys to individual sounds for instant playback.
*   **Audio Device Management:** Select and manage separate audio output and input devices for your soundboard.
*   **Volume Control:** Independent volume sliders for both output and input audio.
*   **Dynamic Sound Loading:** Easily select a directory to load all supported sound files.
*   **Intuitive User Interface:** A clean, frameless UI with custom styling for a modern look and feel.
*   **Persistent Settings:** Your audio device selections, volumes, and sound directory are saved automatically.

## Supported Formats:

Currently, SoundBox primarily supports `.mp3` `.wav` `.ogg` `.flac` audio files.

## Installation & Setup:

1.  **Dependencies:** Ensure you have Python installed. All required Python libraries are listed in `requirements.txt`. You can install them using pip:
    ```bash
    pip install -r requirements.txt
    ```
    *Note: This project uses `PySide6`, `keyboard`, `pyqt_loading_button`, and `winaccent`.*

2.  **Audio Routing (Recommended):** For advanced audio routing, it is highly recommended to use a virtual audio cable solution like [VB-Audio Virtual Cable](https://vb-audio.com/Cable/).

3.  **Run the Application:**
    ```bash
    python app.py
    ```

## Usage:

1.  **Select Sound Folder:** Upon first launch or to change your sound library, click the "Select Folder" button and choose the directory containing your `.mp3` files.
2.  **Play Sounds:** Double-click a sound in the list to play it, or use the dedicated Play/Stop buttons.
3.  **Set Keybinds:** Hover over a sound in the list and click the "Set Key" button to assign a global hotkey.
4.  **Volume Control:** Adjust the output and input volumes using the sliders.
5.  **Device Selection:** Choose your preferred audio output and input devices from the dropdown menus.

## Configuration Files:

SoundBox generates two configuration files upon its first run:

*   `settings.json`: Stores your selected sound directory, default audio output/input devices, and volume levels.
*   `keybinds.json`: Stores the mappings between your sound files and their assigned global hotkeys.

*Troubleshooting Tip: If the application encounters issues, deleting `settings.json` and `keybinds.json` and relaunching the app can often resolve them.*

## Known Issues & Notes:

*   The default Qt for Python music player uses ffmpeg. While `.mp3` is supported, other formats might not work as expected.
*   The application might not function optimally on 7.1 or 5.1 audio devices.
*   The default global hotkey for stopping playback at any time for both input and output devices is `Backspace`.
