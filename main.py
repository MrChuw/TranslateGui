import os
import platform
import urllib.request
from functools import partial
from pathlib import Path
from logging import Logger
from orm import MiniORM
from datetime import datetime, timezone
from PySide6.QtCore import (
    QThread,
    Signal,
    QTimer,
    Qt,
    QSize,
)

from PySide6.QtGui import (
    QIcon,
    QAction,
    QColor,
    
    
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
    QLineEdit,
    QSystemTrayIcon,
    QMenu,
    QListWidget,
    QListWidgetItem,
    
    
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


class HistoryWindow(QMainWindow):
    def __init__(self, history, orm: MiniORM):
        super().__init__()
        self.history = history
        self.orm = orm
        self.setWindowIcon(QIcon(str(Path(__file__).parent / "icon.png")))
        self.resize(460, 350)


        # Menu
        self.menu = self.menuBar()
        self.refresh_action = self.menu.addAction("Refresh")
        self.refresh_action.triggered.connect(self.refresh)

        self.clean_history_action = self.menu.addAction("Clean History")
        self.clean_history_action.triggered.connect(self.are_you_sure)
        self.clean_history_action.toolTip = "This will delete all history entries."


        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Create layout for central widget
        self.layout = QVBoxLayout()
        central_widget.setLayout(self.layout)

        # History list widget
        self.history_list = QListWidget()
        
        # Add items to the list widget
        for entry in self.history:
            item = f"From: {entry['source_language']} To: {entry['target_language']}\n" \
                   f"Input: {entry['input_text']}\nOutput: {entry['output_text']}\n" \
                   f"Timestamp: {self._convert_timestamp(entry['timestamp'])}"
            self.history_list.addItem(item)
            self.add_separator()

        self.layout.addWidget(self.history_list)

        # Close button
        self.close_button = QPushButton("Close")
        self.layout.addWidget(self.close_button)
        self.close_button.clicked.connect(self.close)

        # Set window title
        self.setWindowTitle("History")

        # Add context menu to the list widget
        self.history_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.history_list.customContextMenuRequested.connect(self.show_context_menu)

    def show_context_menu(self, position):
        # Create context menu
        context_menu = QMenu()

        # Add actions to copy input or output
        copy_input_action = QAction("Copy Input", self)
        copy_input_action.triggered.connect(self.copy_input_text)
        context_menu.addAction(copy_input_action)

        copy_output_action = QAction("Copy Output", self)
        copy_output_action.triggered.connect(self.copy_output_text)
        context_menu.addAction(copy_output_action)

        # Show context menu at the current position
        context_menu.exec(self.history_list.mapToGlobal(position))

    def copy_input_text(self):
        # Get the selected item from the list
        selected_item = self.history_list.currentItem()
        if selected_item:
            # Extract the input text from the item and copy it to the clipboard
            input_text = self.extract_input_output_text(selected_item.text(), "Input")
            if input_text:
                clipboard = QApplication.clipboard()
                clipboard.setText(input_text)
            else:
                self.show_message("Error", "Input text not found.")

    def copy_output_text(self):
        # Get the selected item from the list
        selected_item = self.history_list.currentItem()
        if selected_item:
            # Extract the output text from the item and copy it to the clipboard
            output_text = self.extract_input_output_text(selected_item.text(), "Output")
            if output_text:
                clipboard = QApplication.clipboard()
                clipboard.setText(output_text)
            else:
                self.show_message("Error", "Output text not found.")

    def extract_input_output_text(self, item_text, text_type):
        # Extract either input or output text from the item text based on the type
        lines = item_text.split("\n")
        for line in lines:
            if line.startswith(f"{text_type}:"):
                # Return the part after "Input:" or "Output:"
                return line.split(":")[1].strip()
        return None

    def show_message(self, title, message):
        # Show a message box with the provided title and message
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.exec()

    def add_separator(self):
        # Create a separator item (no text, but can style it)
        separator_item = QListWidgetItem("")
        separator_item.setFlags(Qt.ItemFlags())  # Disable selection of the separator item
        separator_item.setBackground(QColor(220, 220, 220, 100))  # Light grey color for separator
        separator_item.setSizeHint(QSize(0, 5))
        self.history_list.addItem(separator_item)

    def refresh(self):
        history = self.orm.get_translation_history()
        self.history_list.clear()
        for entry in history:
            item = f"From: {entry['source_language']} To: {entry['target_language']}\n" \
                   f"Input: {entry['input_text']}\nOutput: {entry['output_text']}\n" \
                   f"Timestamp: {self._convert_timestamp(entry['timestamp'])}"
            self.history_list.addItem(item)
            self.add_separator()

    def are_you_sure(self):
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Are you sure?")
        msg_box.setText("Are you sure you want to clear the history?")
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg_box.setDefaultButton(QMessageBox.No)
        result = msg_box.exec()
        if result == QMessageBox.Yes:
            self.orm.clear_translation_history()
            self.refresh()
        return result

    def _convert_timestamp(self, timestamp):
        utc_datetime = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
        utc_datetime = utc_datetime.replace(tzinfo=timezone.utc)  # Make sure it's timezone-aware
        local_datetime = utc_datetime.astimezone(None)  # Convert UTC to local time
        return local_datetime.strftime('%Y-%m-%d %H:%M:%S')


class GUIWindow(QMainWindow):
    # Above this number of characters in the input text will show a
    # message in the output text while the translation
    # is happening
    SHOW_LOADING_THRESHOLD = 300
    TYPING_DELAY = 500  # In milliseconds

    def __init__(self, data_dir: Path):
        super().__init__()
        self.setWindowIcon(QIcon(str(data_dir / "icon.png")))  # Set the window icon

        # Set the tray icon attribute
        self.tray_icon = None

        self.loading = True
        self.orm = MiniORM(data_dir=data_dir)


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

        # Initialize the text edits
        self.left_textEdit = PlainPasteTextEdit()
        self.left_textEdit.setPlaceholderText("Source")
        self.left_textEdit.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.left_textEdit.textChanged.connect(self.on_text_changed)

        self.right_textEdit = PlainPasteTextEdit()
        self.right_textEdit.setPlaceholderText("Target")
        self.right_textEdit.setReadOnly(True)

        # Layout for text edits
        self.textEdit_layout = QHBoxLayout()
        self.textEdit_layout.addWidget(self.left_textEdit)
        self.textEdit_layout.addWidget(self.right_textEdit)

        # Menu
        self.menu = self.menuBar()
        self.manage_packages_action = self.menu.addAction("Edit API and Key")
        self.manage_packages_action.triggered.connect(self.manage_packages_action_triggered)

        self.manage_packages_action = self.menu.addAction("Refresh Languages")
        self.manage_packages_action.triggered.connect(self.load_languages)

        self.history_action = self.menu.addAction("History")
        self.history_action.triggered.connect(self.history_action_triggered)

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

        # Set focus to the left_textEdit when the window opens
        self.left_textEdit.setFocus()

        if url_key := self.orm.get_api_settings():
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
        left_text = self.left_textEdit.toPlainText()
        right_index = self.right_language_combo.currentIndex()
        right_text = self.right_textEdit.toPlainText()
        if left_index == 0:
            self.right_textEdit.setPlainText(f"Unable to swap Auto with {self.languages[right_index + 1].name}")

        self.left_textEdit.setPlainText(right_text)
        self.left_language_combo.setCurrentIndex(right_index + 1)
        self.right_textEdit.setPlainText(left_text)
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

    def translate(self):    # DONE
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
        if translation := self.lt.translate(input_text, input_language.code, output_language.code):
            bound_translation_function = partial(lambda: translation)
            show_loading_message = len(input_text) > self.SHOW_LOADING_THRESHOLD
            new_worker_thread = TranslationThread(bound_translation_function, show_loading_message)
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
        # Save History
        if translation:
            self.orm.add_translation_history(input_language.name, output_language.name, input_text, translation)

    def history_action_triggered(self):
        history = self.orm.get_translation_history()
        self.history_window = HistoryWindow(history, self.orm)
        self.history_window.show()


class GUIApplication:
    def __init__(self):
        system = platform.system()
        if system == "Linux" or system != "Windows":
            data_dir = os.path.expanduser("~/.local/share/LibreTranslateGUI/")
        else:
            data_dir = os.path.join(os.getenv("APPDATA"), "LibreTranslateGUI")
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)

        data_dir = Path(data_dir)
        self.guarantee_icon(data_dir)

        self.app = QApplication([])

        # Icon
        icon_path = Path(data_dir) / "icon.png"
        qicon = QIcon(str(icon_path))

        self.main_window = GUIWindow(data_dir=data_dir)
        self.main_window.resize(650, 315)
        self.main_window.setWindowIcon(qicon)
        self.app.setWindowIcon(qicon)
        self.app.setDesktopFileName("LibreTranslateGUI")


        # Create the tray
        self.tray_icon = QSystemTrayIcon()
        self.tray_icon.setIcon(qicon)
        self.tray_icon.setVisible(True)

        # Create Show action
        menu = QMenu()
        action = QAction("Show")
        action.triggered.connect(self.show)
        menu.addAction(action)

        # Create Hide action
        hide_action = QAction("Hide")
        hide_action.triggered.connect(self.hide)
        menu.addAction(hide_action)

        # Add a Quit option to the menu.
        quit_action = QAction("Quit")
        quit_action.triggered.connect(self.app.quit)
        menu.addAction(quit_action)

        # Add the menu to the tray
        self.tray_icon.setContextMenu(menu)

        # Set the tray icon attribute in the main window
        self.main_window.tray_icon = self.tray_icon

        self.main_window.show()
        self.app.exec()

    def show(self):
        self.main_window.show()
        self.main_window.move(self.position)  # Dont work on wayland.

    def hide(self):
        self.position = self.main_window.pos()
        self.main_window.hide()

    def guarantee_icon(self, data_path: Path):
        if not (data_path / "icon.png").exists():
            ICON_URL="https://raw.githubusercontent.com/MrChuw/TranslateGui/refs/heads/main/img/icon.png"
            urllib.request.urlretrieve(ICON_URL, data_path / "icon.png")
        if not (data_path / "icon.png").exists():
            Logger.error("Unable to download icon from GitHub")
            exit(1)



def main():
    app = GUIApplication()


main()

