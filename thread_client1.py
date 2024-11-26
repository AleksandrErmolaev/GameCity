import sys
import socket
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QTextEdit, QLineEdit
from threading import Thread


class GameClient(QWidget):
    def __init__(self, host='127.0.0.1', port=34567):
        super().__init__()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((host, port))
        self.initUI()
        self.receive_thread = Thread(target=self.receive_messages, daemon=True)
        self.receive_thread.start()

    def initUI(self):
        self.setWindowTitle("Чат")
        self.setGeometry(200, 200, 800, 600)

        self.layout = QVBoxLayout()
        self.text_edit = QTextEdit(self)
        self.text_edit.setReadOnly(True)
        self.input_line = QLineEdit(self)
        self.input_line.setPlaceholderText('Введите город...')
        self.input_line.returnPressed.connect(self.send_message)

        self.button = QPushButton("Отправить")
        self.button.clicked.connect(self.send_message)

        self.layout.addWidget(self.input_line)
        self.layout.addWidget(self.button)
        self.layout.addWidget(self.text_edit)
        self.setLayout(self.layout)

    def send_message(self):
        city = self.input_line.text()
        self.input_line.clear()
        self.socket.sendall(city.encode('utf-8'))

    def receive_messages(self):
        while True:
            try:
                message = self.socket.recv(1024).decode('utf-8')
                self.text_edit.append(message)
            except:
                break


if __name__ == "__main__":
    app = QApplication(sys.argv)
    client = GameClient()
    client.show()
    sys.exit(app.exec())