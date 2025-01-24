import os
from functools import partial
from pathlib import Path
from logging import Logger
from orm import MiniORM

from PySide6.QtCore import (
    QThread,
    Signal,
    QTimer
)

from PySide6.QtGui import (
    QIcon,
)

from PySide6.QtWidgets import (
    QApplication, 
    QWidget, 
    QVBoxLayout, 
    QHBoxLayout, 
    QPushButton, 
    QTextEdit, 
    QLabel, 
    QComboBox, 
    QMessageBox,
    QMainWindow,
    QLineEdit
)
from libretranslatepy import LibreTranslateAPI

from models import libretranslate_languages_from_dict, LibretranslateLanguage


class ApiKeyGui(QWidget):
    def __init__(self, orm: MiniORM):
        super().__init__()
        self.url = None
        self.api_key = None

        self.orm = orm

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.url_label = QLabel("API url:")
        self.url_edit = QLineEdit()
        self.layout.addWidget(self.url_label)
        self.layout.addWidget(self.url_edit)

        self.api_key_label = QLabel("API key:")
        self.api_key_edit = QLineEdit()
        self.layout.addWidget(self.api_key_label)
        self.layout.addWidget(self.api_key_edit)

        self.ok_button = QPushButton("OK")
        self.layout.addWidget(self.ok_button)
        self.ok_button.clicked.connect(self.ok)


    def ok(self):
        self.url = self.url_edit.text()
        self.api_key = self.api_key_edit.text()
        self.orm.save_api_settings(self.url, self.api_key)
        self.close()


class PlainPasteTextEdit(QTextEdit):
    """Forces pasted text to have formatting cleared"""
    def insertFromMimeData(self, source):
        # Get plain text and insert it
        self.insertPlainText(source.text())


class WorkerThread(QThread):
    """Runs a bound function on a thread"""

    def __init__(self, bound_worker_function):
        """Args:
        bound_worker_function (functools.partial)
        """
        super().__init__()
        self.bound_worker_function = bound_worker_function
        self.finished.connect(self.deleteLater)

    def run(self):
        self.bound_worker_function()


class TranslationThread(QThread):
    send_text_update = Signal(str)

    def __init__(self, translation_function, show_loading_message):
        super().__init__()
        self.translation_function = translation_function
        self.show_loading_message = show_loading_message

    def run(self):
        if self.show_loading_message:
            self.send_text_update.emit("Loading...")
        translated_text = self.translation_function()
        self.send_text_update.emit(translated_text)


class GUIWindow(QMainWindow):
    # Above this number of characters in the input text will show a
    # message in the output text while the translation
    # is happening
    SHOW_LOADING_THRESHOLD = 300
    TYPING_DELAY = 500  # In milliseconds

    def __init__(self):
        super().__init__()

        self.loading = True
        self.orm = MiniORM()


        self.translation_timer = QTimer()
        self.translation_timer.setSingleShot(True)
        self.translation_timer.timeout.connect(self.translate)


        
        # Threading
        self.worker_thread = None

        # This is an instance of TranslationThread to run after
        # the currently running TranslationThread finishes.
        # None if there is no waiting TranslationThread.
        self.queued_translation = None

        # Language selection
        self.left_language_combo = QComboBox()
        self.language_swap_button = QPushButton()
        self.language_swap_button.setIcon(QIcon().fromTheme("object-flip-horizontal"))
        self.right_language_combo = QComboBox()
        self.left_language_combo.currentIndexChanged.connect(self.translate)
        self.right_language_combo.currentIndexChanged.connect(self.translate)
        self.language_swap_button.clicked.connect(self.swap_languages_button_clicked)
        self.language_selection_layout = QHBoxLayout()
        self.language_selection_layout.addStretch()
        self.language_selection_layout.addWidget(self.left_language_combo)
        self.language_selection_layout.addStretch()
        self.language_selection_layout.addWidget(self.language_swap_button)
        self.language_selection_layout.addStretch()
        self.language_selection_layout.addWidget(self.right_language_combo)
        self.language_selection_layout.addStretch()
        self.left_language_combo.currentIndexChanged.connect(self.save_language_selected)
        self.right_language_combo.currentIndexChanged.connect(self.save_language_selected)

        # TextEdits
        self.left_textEdit = PlainPasteTextEdit()
        self.left_textEdit.setPlaceholderText("Source")
        self.left_textEdit.textChanged.connect(self.on_text_changed)
        self.right_textEdit = PlainPasteTextEdit()
        self.right_textEdit.setPlaceholderText("Target")
        self.right_textEdit.setReadOnly(True)
        self.textEdit_layout = QHBoxLayout()
        self.textEdit_layout.addWidget(self.left_textEdit)
        self.textEdit_layout.addWidget(self.right_textEdit)

        # Menu
        self.menu = self.menuBar()
        self.manage_packages_action = self.menu.addAction("Edit API URL and Key")
        self.manage_packages_action.triggered.connect(self.manage_packages_action_triggered)


        self.menu = self.menuBar()
        self.manage_packages_action = self.menu.addAction("Refresh Languages")
        self.manage_packages_action.triggered.connect(self.load_languages)

        
        self.about_action = self.menu.addAction("About")
        self.about_action.triggered.connect(self.about_action_triggered)
        self.menu.setNativeMenuBar(False)

        # Final setup
        self.window_layout = QVBoxLayout()
        self.window_layout.addLayout(self.language_selection_layout)
        self.window_layout.addLayout(self.textEdit_layout)
        self.central_widget = QWidget()
        self.central_widget.setLayout(self.window_layout)
        self.setCentralWidget(self.central_widget)
        self.setWindowTitle("LibreTranslate GUI")

        url_key = self.orm.get_api_settings()
        if url_key:
            self.api_window = ApiKeyGui(self.orm)
            self.api_window.url_edit.setText(url_key["api_url"])
            self.api_window.url = url_key["api_url"]
            self.api_window.api_key_edit.setText(url_key["api_key"])
            self.api_window.api_key = url_key["api_key"]
            self.load_languages()

    def on_text_changed(self):
        """Called when the text in the left text edit changes."""
        # Reset the timer to start a new translation
        self.translation_timer.start(self.TYPING_DELAY)

    def save_language_selected(self):  # DONE
        left = self.left_language_combo.currentIndex()
        right = self.right_language_combo.currentIndex()
        if self.loading:
            return
        saved = self.orm.get_language_settings()
        if saved and int(saved["left_language"]) == left and int(saved["right_language"]) == right:
            return
        self.orm.save_language_settings(left, right)

    def swap_languages_button_clicked(self):  # DONE
        left_index = self.left_language_combo.currentIndex()
        right_index = self.right_language_combo.currentIndex()
        if left_index == 0:
            self.right_textEdit.setPlainText(f"Unable to swap Auto with {self.languages[right_index + 1].name}")
        self.left_language_combo.setCurrentIndex(right_index + 1)
        self.right_language_combo.setCurrentIndex(left_index - 1)

    def about_action_triggered(self):
        about_message_box = QMessageBox()
        about_message_box.setWindowTitle("About")
        about_message_box.setText(
            """<p>Only a small GUI for LibreTranslate, using the 
            <a href="https://github.com/argosopentech/argos-translate-gui">Argos Translate Gui</a> 
            as the basis for the GUI.</p>"""
        )
        about_message_box.setIcon(QMessageBox.Information)
        about_message_box.exec()

    def manage_packages_action_triggered(self):  # DONE
        self.api_window = ApiKeyGui(self.orm)
        url_key = self.orm.get_api_settings()
        if url_key:
            self.api_window.url_edit.setText(url_key["api_url"])
            self.api_window.api_key_edit.setText(url_key["api_key"])
        self.api_window.show()

    def load_languages(self):  # DONE
        self.lt = LibreTranslateAPI(self.api_window.url, self.api_window.api_key)
        self.languages: list[LibretranslateLanguage] = []
        self.languages.append(LibretranslateLanguage("auto", "Auto"))
        self.languages.extend(libretranslate_languages_from_dict(self.lt.languages()))
        language_names = tuple([language.name for language in self.languages])
        self.left_language_combo.clear()
        self.left_language_combo.addItems(language_names)
        self.right_language_combo.clear()
        without_auto = tuple([language.name for language in self.languages if language.name != "Auto"])
        self.right_language_combo.addItems(without_auto)
        languages = self.orm.get_language_settings()
        if languages:
            self.left_language_combo.setCurrentIndex(int(languages["left_language"]))
            self.right_language_combo.setCurrentIndex(int(languages["right_language"]))
        else:
            if len(language_names) > 0:
                self.left_language_combo.setCurrentIndex(0)
            if len(language_names) > 1:
                self.right_language_combo.setCurrentIndex(0)
        self.loading = False
        self.translate()

    def update_right_textEdit(self, text):
        self.right_textEdit.setPlainText(text)

    def handle_worker_thread_finished(self):  # DONE
        self.worker_thread = None
        if self.queued_translation is not None:
            self.worker_thread = self.queued_translation
            self.worker_thread.start()
            self.queued_translation = None

    def translate(self):  # DONE MAYBE
        """Try to translate based on languages selected."""
        if len(self.languages) < 1:
            return
        input_text = self.left_textEdit.toPlainText()
        if len(input_text) < 1:
            return
        input_combo_value = self.left_language_combo.currentIndex()
        input_language = self.languages[input_combo_value]
        output_combo_value = self.right_language_combo.currentIndex()
        output_language = self.languages[output_combo_value + 1]
        translation = self.lt.translate(input_text, input_language.code, output_language.code)
        if translation:
            # bound_translation_function = partial(translation.translate, input_text)
            bound_translation_function = partial(lambda: translation)
            show_loading_message = len(input_text) > self.SHOW_LOADING_THRESHOLD
            new_worker_thread = TranslationThread(
                bound_translation_function, show_loading_message
            )
            new_worker_thread.send_text_update.connect(self.update_right_textEdit)
            new_worker_thread.finished.connect(self.handle_worker_thread_finished)
            if self.worker_thread is None:
                self.worker_thread = new_worker_thread
                self.worker_thread.start()
            else:
                self.queued_translation = new_worker_thread
        else:
            Logger.error("No translation available for this language pair")
            self.right_textEdit.setPlainText("No translation available for this language pair")


class GUIApplication:
    def __init__(self):
        self.app = QApplication([])
        self.main_window = GUIWindow()
        self.main_window.resize(650, 315)

        # Icon
        icon_path = Path(os.path.dirname(__file__)) / "img" / "icon.png"
        icon_path = str(icon_path)
        self.app.setWindowIcon(QIcon(icon_path))

        self.main_window.show()
        self.app.exec()

def main():
    app = GUIApplication()


main()