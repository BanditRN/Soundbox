from PySide6 import QtWidgets, QtCore
from PySide6.QtWidgets import QStyledItemDelegate, QApplication, QFrame, QStyle, QSplashScreen
from PySide6.QtCore import Signal, QModelIndex, QRect, Qt, Slot
from PySide6.QtGui import QPixmap, QPainter

class HoverDelegate(QStyledItemDelegate):
    buttonClicked = Signal(QModelIndex)

    def paint(self, painter, option, index):
        super().paint(painter, option, index)
        
        if option.state & QStyle.State_MouseOver:
            button_option = QtWidgets.QStyleOptionButton()
            button_option.rect = self._get_button_rect(option)
            button_option.text = "Set Key"
            
            button_option.state = QStyle.State_Enabled | QStyle.State_Raised
            QApplication.style().drawControl(QStyle.CE_PushButton, button_option, painter)

    def editorEvent(self, event, model, option, index):
        if (event.type() == QtCore.QEvent.MouseButtonRelease and 
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


class ResizableFrame(QFrame):
    """Custom frame that handles resize cursor changes"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.parent_window = parent
        self.setMouseTracking(True)
    
    def mouseMoveEvent(self, event):
        if self.parent_window:
            handle = self.parent_window._get_resize_handle(event.pos())
            if handle:
                self.parent_window._set_resize_cursor(handle)
            else:
                self.setCursor(Qt.ArrowCursor)
        super().mouseMoveEvent(event)
    
    def mousePressEvent(self, event):
        if self.parent_window:
            self.parent_window.mousePressEvent(event)
        super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event):
        if self.parent_window:
            self.parent_window.mouseReleaseEvent(event)
        super().mouseReleaseEvent(event)


class LoadingScreen(QSplashScreen):
    def __init__(self, movie, parent = None):
        
        movie.jumpToFrame(0)
        pixmap = QPixmap(movie.frameRect().size())
           
        QSplashScreen.__init__(self, pixmap)
        self.movie = movie
        self.movie.frameChanged.connect(self.repaint)
        
        self.setStyleSheet("border-radius: 10px;")
    def showEvent(self, event):
         self.movie.start()
      
    def hideEvent(self, event):
        self.movie.stop()
    
    def paintEvent(self, event):
    
        painter = QPainter(self)
        pixmap = self.movie.currentPixmap()
        self.setMask(pixmap.mask())
        painter.drawPixmap(0, 0, pixmap)

    def sizeHint(self):
    
        return self.movie.scaledSize()
  

    @Slot()
    def onNextFrame(self):
        pixmap = self.movie.currentPixmap()
        self.setPixmap(pixmap)
        self.setMask(pixmap.mask())
