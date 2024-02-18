# Step 1: Create the GUI Layout

import tkinter as tk
from tkinter import scrolledtext
from threading import Thread
import socket
import ssl

class IRCClient(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Simple IRC Client")

        self.main_frame = tk.Frame(self)
        self.main_frame.pack(padx=10, pady=10)

        self.chat_display = scrolledtext.ScrolledText(self.main_frame)
        self.chat_display.pack()

        self.msg_entry = tk.Entry(self.main_frame)
        self.msg_entry.pack(side=tk.LEFT, expand=True, fill=tk.X)

        self.send_btn = tk.Button(self.main_frame, text="Send", command=self.send_message)
        self.send_btn.pack(side=tk.RIGHT)
    
    def send_message(self):
        input_text = self.msg_entry.get()
        if input_text:
            if input_text.startswith("/"):
                # It's a command, remove the leading "/" and send
                self.send_command(input_text[1:])
            else:
                # It's a regular message, format and send to the channel
                self.secure_irc_server.send(f"PRIVMSG #channelname :{input_text}\n".encode('utf-8'))
                self.chat_display.insert(tk.END, f"{self.nickname}: {input_text}\n")
            self.msg_entry.delete(0, tk.END)

    def send_command(self, command):
    # Assuming command does not include the leading "/"
    # Send the command as is to the IRC server
        self.secure_irc_server.send(f"{command}\n".encode('utf-8'))


    # Implementing the IRC Connection

    def connect_to_irc(self, server, port, nickname, channel):
        self.nickname = nickname
        # Create an SSL context
        ssl_context = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH)

        ssl_context.check_hostname = True
        ssl_context.verify_mode = ssl.CERT_REQUIRED

        # Create a regular socket
        self.irc_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # Wrap the socket with SSL
        self.secure_irc_server = ssl_context.wrap_socket(self.irc_server, server_hostname=server)
        
        # Connect using the secure socket
        self.secure_irc_server.connect((server, port))
        
        # Use secure_irc_server for the rest of your communication
        self.secure_irc_server.send(f"USER {nickname} 0 * :{nickname}\n".encode('utf-8'))
        self.secure_irc_server.send(f"NICK {nickname}\n".encode('utf-8'))
        self.secure_irc_server.send(f"JOIN {channel}\n".encode('utf-8'))
        self.listen_for_messages_in_thread()



    def listen_for_messages_in_thread(self):
        thread = Thread(target=self.receive_messages)
        thread.start()

    def receive_messages(self):
        while True:
            try:
                messages = self.secure_irc_server.recv(2048).decode('utf-8').strip()
                
                # Check for PING request and respond with PONG
                if messages.startswith("PING"):
                    self.secure_irc_server.send(f"PONG {messages.split()[1]}\n".encode('utf-8'))
                    continue  # Skip the rest of the loop
                
                # Debug: print messages to console
                print(messages)
                
                # Safely update the GUI from another thread
                self.chat_display.insert(tk.END, messages + '\n')
                self.chat_display.see(tk.END)
            except socket.error as e:
                print(f"Socket Error: {e}")
                break
            except Exception as e:
                print(f"Error: {e}")
                break




# Running the Client

if __name__ == "__main__":
    app = IRCClient()
    app.connect_to_irc('irc.hackint.org', 6697, 'student', '#hackint')
    app.mainloop()