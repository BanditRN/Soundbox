# Soundbox
Soundboard written in python using pyside6<br>
Uses [Boppreh's keyboard lib](https://github.com/boppreh/keyboard) for keybinds <br>
Default Qt for python music player is ffmpeg and I only implemented mp3 support for testing purposes<br>
Might not work on 7.1 or 5.1 audio devices<br>
The app will generate 2 files on first start: <br>
<ul>
<li>Settings.json</li>
<li>Keybinds.json</li>
</ul><br>
Key software for routing audio is [VB-Audio Virtual cable](https://vb-audio.com/Cable/)
Default Key for stopping playback at anytime for both input and output devices is "Backspace"
If for any reason the app won't start just delete those 2 files and relaunch the app
