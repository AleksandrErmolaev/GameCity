import socket
import threading
import pickle

rooms = {}

class Room:
    def __init__(self, name):
        self.name = name
        self.clients = []
        self.banned = set()
        self.cities = set()
        self.last_city = None
        self.points = {}
        self.lock = threading.Lock()
        self.condition = threading.Condition(self.lock)

    def broadcast(self, message):
        for client, _ in self.clients:
            try:
                client.send(pickle.dumps(message))
            except:
                pass

    def add_client(self, client, name):
        with self.lock:
            self.clients.append((client, name))
            self.points[name] = 0
            self.broadcast(f"{name} присоединился к комнате {self.name}.")
            self.condition.notify_all()

    def remove_client(self, client, name):
        with self.lock:
            self.clients = [(c, n) for c, n in self.clients if c != client]
            if name in self.points:
                del self.points[name]
            self.broadcast(f"{name} покинул комнату {self.name}.")
            self.condition.notify_all()

    def game_over(self):
        self.broadcast("Игра завершена.")
        scores = "\n".join([f"{name}: {score} очков" for name, score in self.points.items()])
        self.broadcast(f"Результаты игры:\n{scores}")
        self.cities.clear()
        self.last_city = None

    def next_turn(self):
        if self.clients:
            self.clients.append(self.clients.pop(0))

    def get_current_player(self):
        if self.clients:
            return self.clients[0]
        return None, None

def play_game(room):
    with room.lock:
        while len(room.clients) < 2:
            room.broadcast("Ожидаем второго игрока...")
            room.condition.wait()

        room.broadcast("Игра начинается!")

    while True:
        with room.lock:
            if len(room.clients) < 2:
                room.broadcast("Недостаточно игроков для продолжения игры. Игра завершена.")
                room.game_over()
                break

            client, name = room.get_current_player()
            client.send(pickle.dumps("Ваш ход: "))

        try:
            msg = pickle.loads(client.recv(1024)).strip()

            if msg.lower() == "exit":
                room.remove_client(client, name)
                client.close()
                break
            elif msg.lower() not in room.cities:
                if room.last_city is None or msg.lower()[0] == room.last_city[-1]:
                    room.cities.add(msg.lower())
                    room.last_city = msg.lower()
                    room.points[name] += 1
                    room.broadcast(f"{name} назвал город: {msg}. Очки: {room.points[name]}")
                    room.next_turn()
                else:
                    client.send(pickle.dumps("Город должен начинаться на последнюю букву предыдущего!"))
            else:
                client.send(pickle.dumps("Этот город уже был назван!"))

        except Exception as e:
            print(f"Ошибка: {e}")
            room.remove_client(client, name)
            break


def handle_client(client):
    try:
        name = pickle.loads(client.recv(1024)).strip()
        client.send(pickle.dumps("Добро пожаловать! Вы можете создавать комнаты, присоединяться или переходить между ними."))
        while True:
            msg = pickle.loads(client.recv(1024)).strip()
            if msg.lower() == "список":
                client.send(pickle.dumps(list(rooms.keys())))
            elif msg.lower().startswith("создать "):
                room_name = msg.split(" ", 1)[1].strip()
                if room_name not in rooms:
                    rooms[room_name] = Room(room_name)
                    client.send(pickle.dumps(f"Комната {room_name} создана."))
                else:
                    client.send(pickle.dumps(f"Комната {room_name} уже существует."))
            elif msg.lower().startswith("присоединиться "):
                room_name = msg.split(" ", 1)[1].strip()
                if room_name in rooms:
                    room = rooms[room_name]
                    if name in room.banned:
                        client.send(pickle.dumps(f"Вы заблокированы в комнате {room_name}."))
                    else:
                        room.add_client(client, name)
                        client.send(pickle.dumps(f"Вы присоединились к комнате {room_name}. Ожидаем второго игрока..."))
                        threading.Thread(target=play_game, args=(room,), daemon=True).start()
                else:
                    client.send(pickle.dumps(f"Комната {room_name} не найдена."))

            elif msg.lower().startswith("перейти "):
                new_room_name = msg.split(" ", 1)[1].strip()
                current_room = None
                for room in rooms.values():
                    if (client, name) in room.clients:
                        current_room = room
                        break
                if current_room:
                    current_room.remove_client(client, name)
                    if len(current_room.clients) < 2:
                        current_room.game_over()

                if new_room_name in rooms:
                    new_room = rooms[new_room_name]
                    if name in new_room.banned:
                        client.send(pickle.dumps(f"Вы заблокированы в комнате {new_room_name}."))
                    else:
                        new_room.add_client(client, name)
                        client.send(pickle.dumps(f"Вы перешли в комнату {new_room_name}. Ожидаем второго игрока..."))
                        with new_room.lock:
                            if len(new_room.clients) > 1:
                                threading.Thread(target=play_game, args=(new_room,), daemon=True).start()
                else:
                    client.send(pickle.dumps(f"Комната {new_room_name} не найдена."))

            elif msg.lower().startswith("ban "):
                player_name = msg.split(" ", 1)[1].strip()
                for room in rooms.values():
                    if (client, name) in room.clients:
                        room.banned.add(player_name)
                        client.send(pickle.dumps(f"Игрок {player_name} забанен в комнате {room.name}."))
                        break

            elif msg.lower() == "exit":
                client.close()
                break
    except Exception as e:
        print(f"Ошибка: {e}")

    finally:
        client.close()


def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("127.0.0.1", 12345))
    server.listen(5)
    print("Сервер запущен.")

    while True:
        client, addr = server.accept()
        print(f"Подключился клиент {addr}.")
        threading.Thread(target=handle_client, args=(client,), daemon=True).start()


if __name__ == "__main__":
    main()