# Step 1: Create the GUI Layout

import tkinter as tk
from tkinter import scrolledtext, messagebox
from threading import Thread
import socket
import ssl
import re

class IRCClient(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Simple IRC Client")

        self.server = ''
        self.port = 0
        self.nickname = ''
        self.channel = ''

        self.setup_connection_frame()
        self.setup_chat_interface()

    def setup_connection_frame(self):
        self.connection_frame = tk.Frame(self)
        self.connection_frame.pack(padx=10, pady=10)

        self.server_entry_label = tk.Label(self.connection_frame, text="Server:")
        self.server_entry_label.grid(row=0, column=0)

        self.server_entry = tk.Entry(self.connection_frame)
        self.server_entry.grid(row=0, column=1)

        self.port_entry_label = tk.Label(self.connection_frame, text="Port:")
        self.port_entry_label.grid(row=1, column=0)

        self.port_entry = tk.Entry(self.connection_frame)
        self.port_entry.grid(row=1, column=1)

        self.nickname_entry_label = tk.Label(self.connection_frame, text="Nickname:")
        self.nickname_entry_label.grid(row=2, column=0)

        self.nickname_entry = tk.Entry(self.connection_frame)
        self.nickname_entry.grid(row=2, column=1)

        self.channel_entry_label = tk.Label(self.connection_frame, text="Channel:")
        self.channel_entry_label.grid(row=3, column=0)

        self.channel_entry = tk.Entry(self.connection_frame)
        self.channel_entry.grid(row=3, column=1)

        self.connect_button = tk.Button(self.connection_frame, text="Connect", command=self.attempt_connection)
        self.connect_button.grid(row=4, column=0, columnspan=2)

    def setup_chat_interface(self):
        self.chat_frame = tk.Frame(self)

        self.user_list_box = tk.Listbox(self.chat_frame, width=30)
        self.user_list_box.pack(side=tk.RIGHT, fill=tk.Y)

        self.chat_display = scrolledtext.ScrolledText(self.chat_frame)
        self.chat_display.pack()

        self.msg_entry = tk.Entry(self.chat_frame)
        self.msg_entry.pack(side=tk.LEFT, expand=True, fill=tk.X)

        self.send_btn = tk.Button(self.chat_frame, text="Send", command=self.send_message)
        self.send_btn.pack(side=tk.RIGHT)
    
    def display_chat_components(self):
        self.chat_frame.pack(padx=10, pady=10)

    def attempt_connection(self):
        self.server = self.server_entry.get()
        try:
            self.port = int(self.port_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Port must be an integer")
            return

        self.nickname = self.nickname_entry.get()
        self.channel = self.channel_entry.get()
        
        if self.server and self.port and self.nickname and self.channel:
            # Hide connection frame and show chat components
            self.connection_frame.pack_forget()
            self.display_chat_components()
            self.connect_to_irc()
        else:
            messagebox.showerror("Error", "All fields must be completed")

    
    def send_message(self):
        input_text = self.msg_entry.get()
        if input_text:
            if input_text.startswith("/"):
                # It's a command, remove the leading "/" and send
                self.send_command(input_text[1:])
            else:
                # It's a regular message, format and send to the channel
                self.secure_irc_server.send(f"PRIVMSG {self.channel} :{input_text}\n".encode('utf-8'))
                self.chat_display.insert(tk.END, f"{self.nickname}: {input_text}\n")
            self.msg_entry.delete(0, tk.END)

    def send_command(self, command):
    # Assuming command does not include the leading "/"
    # Send the command as is to the IRC server
        self.secure_irc_server.send(f"{command}\n".encode('utf-8'))


    # Implementing the IRC Connection

    def connect_to_irc(self):
        
        # Create an SSL context
        ssl_context = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH)

        ssl_context.check_hostname = True
        ssl_context.verify_mode = ssl.CERT_REQUIRED

        # Create a regular socket
        self.irc_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # Wrap the socket with SSL
        self.secure_irc_server = ssl_context.wrap_socket(self.irc_server, server_hostname=self.server)
        
        # Connect using the secure socket
        self.secure_irc_server.connect((self.server, self.port))
        
        # Use secure_irc_server for the rest of your communication
        self.secure_irc_server.send(f"USER {self.nickname} 0 * :{self.nickname}\n".encode('utf-8'))
        self.secure_irc_server.send(f"NICK {self.nickname}\n".encode('utf-8'))
        self.secure_irc_server.send(f"JOIN {self.channel}\n".encode('utf-8'))
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

                # If messages contain user list update information, update the user_list_box
                # You'll need to adjust the following regex according to your IRC server's responses and test carefully
                user_list_pattern = re.compile(r':\S+ 353 \S+ = \S+ :(.*)') # Adjust this based on actual server response format
                match = user_list_pattern.match(messages)
                if match:
                    users = match.group(1).split('m| ')  # Assuming space-separated list
                    self.update_user_list(users)
                    continue  # Skip the rest of the loop to not display this in main chat window

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

    def update_user_list(self, users):
        # Safely update the user list from another thread
        self.user_list_box.delete(0, tk.END)
        for user in users:
            self.user_list_box.insert(tk.END, user)




# Running the Client

if __name__ == "__main__":
    app = IRCClient()
    app.mainloop()