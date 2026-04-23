from PySide6.QtWidgets import (QStyledItemDelegate , QStyle,QStyleOptionButton , QApplication)
from PySide6.QtCore import (Signal , QModelIndex ,  QEvent , Qt , QRect)
class HoverDelegate(QStyledItemDelegate):
    buttonClicked = Signal(QModelIndex)

    def paint(self, painter, option, index):
        super().paint(painter, option, index)
        
        if option.state & QStyle.State_MouseOver:
            button_option = QStyleOptionButton()
            button_option.rect = self._get_button_rect(option)
            button_option.text = "Set Key"
            
            button_option.state = QStyle.State_Enabled | QStyle.State_Raised
            QApplication.style().drawControl(QStyle.CE_PushButton, button_option, painter)

    def editorEvent(self, event, model, option, index):
        if (event.type() == QEvent.MouseButtonRelease and 
            event.button() == Qt.LeftButton):
            if self._get_button_rect(option).contains(event.pos()):
                self.buttonClicked.emit(index)
                return True
        return super().editorEvent(event, model, option, index)

    def _get_button_rect(self, option) -> QRect:
        button_width, button_height = 80, 25
        return QRect(
            option.rect.right() - button_width - 5,
            option.rect.top() + (option.rect.height() - button_height) // 2,
            button_width,
            button_height
        )