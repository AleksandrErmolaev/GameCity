import socket
import threading
from threading import Timer


class GameServer:
    def __init__(self, host='127.0.0.1', port=34567):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((host, port))
        self.server_socket.listen(2)
        self.clients = []
        self.current_city = None
        self.history = []
        self.turn = 0
        self.timer = None
        self.time_limit = 30

    def handle_client(self, client_socket, addr):
        print(f"Подключен: {addr}")
        self.clients.append(client_socket)
        client_socket.sendall(f"Ваш номер: {len(self.clients)}".encode('utf-8'))
        if len(self.clients) == 2:
            self.start_game()

        while True:
            try:
                message = client_socket.recv(1024).decode('utf-8')
                if message:
                    self.process_message(message, client_socket)
                else:
                    break
            except ConnectionResetError:
                break

        client_socket.close()
        self.clients.remove(client_socket)

    def start_game(self):
        self.clients[0].sendall("Ваш ход!".encode('utf-8'))
        for client in self.clients:
            if client == self.clients[-1]:
                client.sendall("\n".encode('utf-8'))
            client.sendall("Игра началась! Город:".encode('utf-8'))

    def process_message(self, message, client_socket):
        if self.turn != self.clients.index(client_socket):
            client_socket.sendall("Не ваш ход! Подождите своей очереди.".encode('utf-8'))
            return
        if message.lower() not in self.history:
            if self.current_city is None or message[0].lower() == self.current_city[-1].lower():
                self.history.append(message.lower())
                self.current_city = message
                self.switch_turn()
            elif self.current_city[-1].lower() in ('ы','ь','ъ'):
                if message[0].lower() == self.current_city[-2].lower():
                    self.history.append(message.lower())
                    self.current_city = message
                    self.switch_turn()
                else:
                    client_socket.sendall("Неправильно: город должен начинаться на букву '{}'. Попробуйте снова.".format(
                        self.current_city[-2]).encode('utf-8'))

            else:
                client_socket.sendall("Неправильно: город должен начинаться на букву '{}'. Попробуйте снова.".format(
                    self.current_city[-1]).encode('utf-8'))
        else:
            client_socket.sendall("Этот город уже был назван. Попробуйте другой.".encode('utf-8'))

    def switch_turn(self):
        self.turn = (self.turn + 1) % 2
        self.clients[self.turn].sendall(f"Ваш ход! Предыдущий город: '{self.current_city}'".encode('utf-8'))
        self.clients[1 - self.turn].sendall(f"Ход игрока: '{self.current_city}'".encode('utf-8'))
        self.reset_timer()

    def reset_timer(self):
        if self.timer is not None:
            self.timer.cancel()
        self.timer = Timer(self.time_limit, self.timeout)
        self.timer.start()

    def timeout(self):
        winner_index = (self.turn + 1) % 2
        for client in self.clients:
            client.sendall(f"Время вышло! Игрок {winner_index + 1} победил.".encode('utf-8'))
        self.server_socket.close()

    def run(self):
        while True:
            client_socket, addr = self.server_socket.accept()
            threading.Thread(target=self.handle_client, args=(client_socket, addr)).start()



server = GameServer()
server.run()
