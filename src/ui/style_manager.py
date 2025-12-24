import winaccent
import os
from src.utils.resource_manager import ResourceManager

class StyleManager:
    @staticmethod
    def load_styles() -> str:
        """Loads the QSS file and injects dynamic values."""
        try:
            with open("resources/styles.qss", "r") as f:
                style_content = f.read()
            
            down_arrow_path = ResourceManager.get_resource_path("down.png").replace("\\", "/")
            
            # Inject dynamic accent color
            style_content += f"""
            /* Dynamic Frame Style */
            QFrame#mainFrame {{
                border: 1px solid {winaccent.accent_dark_1};
                border-radius: 10px;
            }}
            
            /* Dynamic ComboBox Border */
            QComboBox#audio_devices, QComboBox#audio_input_devices {{
                border: 1px solid {winaccent.accent_dark_1};
            }}
            
            /* Down Arrow Icon */
            QComboBox#audio_devices::down-arrow, QComboBox#audio_input_devices::down-arrow {{
                image: url({down_arrow_path});
            }}
            """
            return style_content
        except FileNotFoundError:
            return ""

    @staticmethod
    def get_button_style() -> str:
         return """
        color: white;
        background: #122138;
        border: 2px solid transparent;
        border-radius: 5px;
        font-size: 16px;
        """
