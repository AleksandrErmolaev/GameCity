import sys
import socket
import threading
import pickle
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QTextEdit, QLineEdit, QVBoxLayout, QWidget, \
    QComboBox, QLabel, QInputDialog, QMessageBox
from PyQt6.QtCore import pyqtSignal, QObject


class ChatClient(QObject):
    message_received = pyqtSignal(str)

    def __init__(self, host, port):
        super().__init__()
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((host, port))

        threading.Thread(target=self.receive_messages, daemon=True).start()

    def receive_messages(self):
        while True:
            try:
                data = self.client_socket.recv(1024)
                if not data:
                    break
                message = pickle.loads(data)
                if isinstance(message, list):
                    message = "Список комнат:\n" + "\n".join(message)
                self.message_received.emit(message)
            except Exception as e:
                print(f"Ошибка получения данных: {e}")
                break

    def send_message(self, message):
        try:
            self.client_socket.send(pickle.dumps(message))
        except Exception as e:
            print(f"Ошибка отправки сообщения: {e}")

    def close(self):
        self.client_socket.close()


class LoginWindow(QMainWindow):
    def __init__(self, client):
        super().__init__()
        self.client = client
        self.setWindowTitle("Авторизация")
        self.setGeometry(100, 100, 400, 200)
        layout = QVBoxLayout()

        self.username_input = QLineEdit(self)
        self.username_input.setPlaceholderText("Введите ваше имя")
        layout.addWidget(self.username_input)

        self.login_button = QPushButton("Войти", self)
        self.login_button.clicked.connect(self.login)
        layout.addWidget(self.login_button)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def login(self):
        username = self.username_input.text().strip()
        if username:
            self.client.send_message(username)
            main_window.set_username(username)
            self.hide()
            main_window.show()
        else:
            QMessageBox.warning(self, "Ошибка", "Имя не может быть пустым!")


class MainRoomWindow(QMainWindow):
    def __init__(self, client):
        super().__init__()
        self.client = client
        self.setWindowTitle("Выбор комнаты")
        self.setGeometry(100, 100, 400, 300)
        layout = QVBoxLayout()

        self.username_label = QLabel(self)
        layout.addWidget(self.username_label)

        self.rooms_combo_box = QComboBox(self)
        layout.addWidget(self.rooms_combo_box)

        self.refresh_button = QPushButton("Обновить список комнат", self)
        self.refresh_button.clicked.connect(self.refresh_rooms)
        layout.addWidget(self.refresh_button)

        self.join_button = QPushButton("Присоединиться к комнате", self)
        self.join_button.clicked.connect(self.join_room)
        layout.addWidget(self.join_button)

        self.create_button = QPushButton("Создать комнату", self)
        self.create_button.clicked.connect(self.create_room)
        layout.addWidget(self.create_button)

        self.exit_button = QPushButton("Выйти", self)
        self.exit_button.clicked.connect(self.exit_app)
        layout.addWidget(self.exit_button)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def set_username(self, username):
        self.username_label.setText(f"Привет, {username}!")

    def refresh_rooms(self):
        self.client.send_message("список")

    def update_rooms(self, rooms):
        self.rooms_combo_box.clear()
        self.rooms_combo_box.addItems(rooms)

    def join_room(self):
        room_name = self.rooms_combo_box.currentText()
        if room_name:
            self.client.send_message(f"присоединиться {room_name}")
            chat_window.set_room_name(room_name)
            self.hide()
            chat_window.show()

    def create_room(self):
        room_name, ok = QInputDialog.getText(self, "Создать комнату", "Введите название комнаты:")
        if ok and room_name.strip():
            self.client.send_message(f"создать {room_name}")

    def exit_app(self):
        self.client.close()
        self.close()

class ChatWindow(QMainWindow):
    def __init__(self, client):
        super().__init__()
        self.client = client
        self.setWindowTitle("Комната")
        self.setGeometry(100, 100, 600, 400)

        layout = QVBoxLayout()

        self.chat_text_edit = QTextEdit(self)
        self.chat_text_edit.setReadOnly(True)
        layout.addWidget(self.chat_text_edit)

        self.message_line_edit = QLineEdit(self)
        layout.addWidget(self.message_line_edit)

        self.send_button = QPushButton("Отправить", self)
        self.send_button.clicked.connect(self.send_message)
        layout.addWidget(self.send_button)

        self.leave_button = QPushButton("Покинуть комнату", self)
        self.leave_button.clicked.connect(self.leave_room)
        layout.addWidget(self.leave_button)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.client.message_received.connect(self.display_message)

    def set_room_name(self, room_name):
        self.setWindowTitle(f"Комната: {room_name}")

    def send_message(self):
        message = self.message_line_edit.text().strip()
        if message:
            self.client.send_message(message)
            self.message_line_edit.clear()

    def display_message(self, message):
        self.chat_text_edit.append(message)

    def leave_room(self):
        self.client.send_message("exit")
        self.hide()
        main_window.show()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    client = ChatClient("127.0.0.1", 12345)

    login_window = LoginWindow(client)
    main_window = MainRoomWindow(client)
    chat_window = ChatWindow(client)

    client.message_received.connect(
        lambda msg: main_window.update_rooms(msg.split("\n")[1:]) if msg.startswith("Список комнат") else None)

    login_window.show()
    sys.exit(app.exec())