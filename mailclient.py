import socket
import os

def main():
    HOST = '192.168.1.15'  # IP address of the server
    PORT = 65432  # Port number used by the server

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
        client_socket.connect((HOST, PORT))
        while True:
            data = client_socket.recv(4096).decode()
            if not data:
                break
            print(data, end='')
            # Check if input is expected from the user
            prompts = [
                "Enter choice", "Please enter your username", "Enter recipient username",
                "Enter your message", "Do you want to attach a PDF file?",
                "Enter the number of the message", "Waiting for the PDF file",
                "Inbox cleared.", "Invalid selection.", "File sent.", "File received."
            ]
            if any(prompt in data for prompt in prompts):
                user_input = input()
                client_socket.sendall(user_input.encode())
                if "Do you want to attach a PDF file?" in data and user_input.lower() == 'yes':
                    # Send the file
                    filepath = input("Enter the path to the PDF file: ")
                    if not os.path.isfile(filepath):
                        print("File does not exist.")
                        client_socket.sendall(b"")  # Send empty data to avoid blocking
                        continue
                    filename = os.path.basename(filepath)
                    filesize = os.path.getsize(filepath)
                    # Send file metadata
                    file_info = f"{filename}|{filesize}"
                    client_socket.sendall(file_info.encode())
                    ack = client_socket.recv(1024)
                    # Send file data
                    with open(filepath, 'rb') as f:
                        while True:
                            bytes_read = f.read(4096)
                            if not bytes_read:
                                break
                            client_socket.sendall(bytes_read)
                    data = client_socket.recv(4096).decode()
                    print(data, end='')
            elif "Sending PDF file..." in data:
                # Receive file metadata
                file_info = client_socket.recv(1024).decode()
                filename, filesize = file_info.split('|')
                filesize = int(filesize)
                client_socket.sendall(b"ACK")
                # Receive file data
                file_data = b''
                remaining = filesize
                while remaining > 0:
                    bytes_read = client_socket.recv(min(4096, remaining))
                    if not bytes_read:
                        break
                    file_data += bytes_read
                    remaining -= len(bytes_read)
                # Save the file
                save_path = os.path.join('.', f"received_{filename}")
                with open(save_path, 'wb') as f:
                    f.write(file_data)
                print(f"File '{filename}' received and saved as '{save_path}'.")
            elif "Goodbye!" in data:
                break

if __name__ == '__main__':
        main()
