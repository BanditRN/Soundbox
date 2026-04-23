import winaccent

class Stylesheets:
    
    @staticmethod
    def get_scrollbar_style() -> str:
        return """ 

QScrollBar:vertical {
    background-color: transparent;
    border: transparent;
    background: transparent;
    width: 10px;  
}

QScrollBar::handle:vertical {
    background: #a0a0a0;
    min-height: 20px;
    border-radius: 5px;
}

QScrollBar::add-line {
    border: none;
    background: none;
    height: 0px;
    subcontrol-position: bottom;
    subcontrol-origin: margin;
}

QScrollBar::sub-line {
    border: none;
    background: none;
    height: 0px;
    subcontrol-position: top;
    subcontrol-origin: margin;
}

QScrollBar::add-page,
QScrollBar::sub-page {
    background: none ;
}
        """
    
    @staticmethod
    def get_frame_style() -> str:
        return f"QFrame {'{border: 1px solid '+ winaccent.accent_dark_1 + ' ; border-radius: 10px;}'}"
    
    @staticmethod
    def get_button_style() -> str:
        return """
        color: white;
        background: #122138;
        border: 2px solid transparent;
        border-radius: 5px;
        font-size: 16px;
        """

