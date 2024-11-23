import socket

def main():
    HOST = '192.168.1.15'  #address of server
    PORT = 65432  #port

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
        client_socket.connect((HOST, PORT))
        while True:
            data = client_socket.recv(4096).decode()
            if not data:
                break
            print(data, end='')
            # Check if input is expected from the user
            if any(prompt in data for prompt in ["Enter choice", "Please enter your username", "Enter recipient username", "Enter your message"]):
                user_input = input()
                client_socket.sendall(user_input.encode())
            if "Goodbye!" in data:
                break

if __name__ == '__main__':
    main()
