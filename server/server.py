import socket
import threading
import os
import sys

HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT" ,49500 ))
HEADER_SIZE = 256

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen()

clients = []

print(f"Server running on port {PORT}")



def recv_exact(sock, size):

    data = b""

    while len(data) < size:

        packet = sock.recv(size - len(data))

        if not packet:
            return None

        data += packet

    return data

def broadcast(header, body, sender):

    for client in clients:

        if client != sender:

            try:
                client.sendall(header)
                client.sendall(body)
                sys.stdout.flush()
            except:
                pass



def handle_client(client):

    while True:

        try:
            header = recv_exact(client, HEADER_SIZE)

            if not header:
                break

            header_text = header.decode().strip()

            parts = header_text.split("|")

            msg_type = parts[0]

            if msg_type == "TEXT":

                size = int(parts[1])

                body = recv_exact(client, size)

                broadcast(
                    header,
                    body,
                    client
                )

            elif msg_type == "FILE":

                filesize = int(parts[3])

                body = recv_exact(client, filesize)

                broadcast(
                    header,
                    body,
                    client
                )

        except:
            break

    clients.remove(client)

    client.close()


while True:
    client, addr = server.accept()

    print("Connected:", addr)

    clients.append(client)

    thread = threading.Thread(target=handle_client, args=(client,))
    thread.start()
