import socket
import threading
import signal
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

HOST = '127.0.0.1'
PORT = 6668

client_sockets = set()
irc_channels = {}
irc_users = {}

server_socket = None

def start_irc_server():
    global server_socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen()

    logging.info(f'IRC server is listening on {HOST}:{PORT}')

    try:
        while True:
            client_socket, client_address = server_socket.accept()
            client_sockets.add(client_socket)
            logging.info(f'Accepted connection from {client_address}')
            
            client_thread = threading.Thread(target=handle_client, args=(client_socket, client_address), daemon=True)
            client_thread.start()
    finally:
        server_socket.close()
        logging.info("Server socket closed.")

def handle_client(client_socket, client_address):
    with client_socket:  # Ensures closure of the socket
        try:
            client_socket.sendall(b'Welcome to the IRC server!\nPlease register your nickname with NICK <your_nickname>\n')
            nickname_set = False
            client_socket.settimeout(1000)

            while True:
                data = client_socket.recv(1024)
                if not data:
                    break

                messages = data.split(b'\n')
                for message in messages:
                    if not message: continue
                    command, *args = message.decode().split()

                    if not nickname_set and command != 'NICK':
                        request_nickname(client_socket)
                        continue

                    if command == 'NICK':
                        handle_nick_command(client_socket, args)
                        nickname_set = True
                    elif command == 'QUIT':
                        return  # Exits the function cleanly, ending the thread
                    elif command == 'JOIN':
                        handle_join_command(client_socket, args)
                    elif command == 'PART':
                        handle_part_command(client_socket, args)
                    elif command == 'PRIVMSG':
                        handle_privmsg_command(client_socket, args)
                    elif command == 'LIST':
                        handle_list_command(client_socket)
                    elif command == 'NAMES':
                        handle_names_command(client_socket, args)


        except socket.timeout:
            logging.info(f'Client {client_address} timeout, closing connection.')
        except socket.error as e:
            logging.error(f'Error receiving data: {e}')
        finally:
            clean_up_client_data(client_socket)
            logging.info(f'Connection with {client_address} closed.')

def handle_nick_command(client_socket, args):
    nickname = args[0]
    if nickname in irc_users.values():
        client_socket.sendall(b'Nickname already taken, try another one.\n')
    else:
        irc_users[client_socket] = nickname
        client_socket.sendall(f'Nickname registered: {nickname}\n'.encode())

def request_nickname(client_socket):
    client_socket.sendall(b'Please set a nickname using NICK <your_nickname>.\n')

def handle_join_command(client_socket, args):
    # Ensure there's at least a channel name
    if len(args) < 1:
        client_socket.sendall(b"Usage: JOIN <channel>\n")
        return
    
    channel_name = args[0]
    nickname = irc_users.get(client_socket, "unknown")
    
    # If the channel doesn't exist, create it
    if channel_name not in irc_channels:
        irc_channels[channel_name] = []
        
    # Notify all current members that a new user has joined
    join_message = f"{nickname} joined channel {channel_name}\n".encode()
    for user in irc_channels[channel_name]:
        user.sendall(join_message)
    
    # Add the user to the channel
    irc_channels[channel_name].append(client_socket)
    
    # Send confirmation to the joining user
    client_socket.sendall(f'Joined channel {channel_name}\n'.encode())


def handle_part_command(client_socket, args):
    channel_name = args[0]
    if channel_name in irc_channels and client_socket in irc_channels[channel_name]:
        irc_channels[channel_name].remove(client_socket)
    client_socket.sendall(f'Left channel {channel_name}\n'.encode())

def handle_privmsg_command(client_socket, args):
    # Ensure there's at least a channel name and a message to send
    if len(args) < 2:
        client_socket.sendall(b"Usage: PRIVMSG <channel> <message>\n")
        return
    
    channel_name, message = args[0], ' '.join(args[1:])
    
    # Check if the user trying to send a message is part of the channel
    if client_socket not in irc_channels.get(channel_name, []):
        client_socket.sendall(f"You are not in channel {channel_name}. Please JOIN first.\n".encode())
    else:
        # Proceed to send the message to all users in the channel
        for user in irc_channels[channel_name]:
            if user != client_socket:  # Optionally, skip sending the message back to the sender
                user.sendall(f'{irc_users[client_socket]} in {channel_name}: {message}\n'.encode())


def handle_list_command(client_socket):
    if not irc_channels:  # Check if there are no channels
        client_socket.sendall(b'No active channels.\n')
    else:
        for channel, users in irc_channels.items():
            client_socket.sendall(f'Channel: {channel} Users: {len(users)}\n'.encode())

def handle_names_command(client_socket, args):
    if args:  # If a channel is specified
        channel_name = args[0]
        if channel_name in irc_channels:
            nicknames = [irc_users[user] for user in irc_channels[channel_name]]
            client_socket.sendall(f'Users in {channel_name}: {", ".join(nicknames)}\n'.encode())
        else:
            client_socket.sendall(f'Channel {channel_name} not found.\n'.encode())
    else:  # If no channel is specified - handling can vary based on desired behavior
        client_socket.sendall('Nicknames in all channels:\n'.encode())
        for channel, users in irc_channels.items():
            nicknames = [irc_users[user] for user in users]
            client_socket.sendall(f'{channel}: {", ".join(nicknames)}\n'.encode())

def clean_up_client_data(client_socket):
    irc_users.pop(client_socket, None)
    for clients in irc_channels.values():
        if client_socket in clients:
            clients.remove(client_socket)

def signal_handler(sig, frame):
    shutdown_message = "server is shutting down. You've been disconnected.\n".encode()
    logging.info('Shutting down server...')
    for sock in client_sockets:
        try:
            sock.sendall(shutdown_message)
        except Exception as e:
            logging.error(f'Error sending shutdown message: {e}')
        finally:
            sock.close()
        
    server_socket.close()
    logging.info("Server shut down successfully.")
    exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    start_irc_server()
