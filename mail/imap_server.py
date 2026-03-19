import asyncio
import os
import re

class IMAPServerProtocol(asyncio.Protocol):
    def __init__(self, mail_dir):
        self.mail_dir = mail_dir
        self.transport = None
        self.username = None
        self.state = 'NOT_AUTHENTICATED'

    def connection_made(self, transport):
        self.transport = transport
        self.transport.write(b'* OK IMAP4rev1 Service Ready\r\n')

    def data_received(self, data):
        lines = data.decode().split('\r\n')
        for line in lines:
            if line:
                try:
                    self.handle_command(line.strip())
                except Exception as e:
                    print(f"Error handling command '{line.strip()}': {e}")
                    self.transport.write(f'BAD Internal Server Error\r\n'.encode())
                    self.transport.close()
                    break

    def handle_command(self, line):
        print(f"Client: {line}")
        if not line:
            return

        parts = line.split(' ')
        tag = parts[0]
        command = parts[1].upper()
        args = parts[2:] if len(parts) > 2 else []

        if command == 'CAPABILITY':
            self.handle_capability(tag)
        elif command == 'LOGIN':
            self.handle_login(tag, args)
        elif command == 'LIST':
            self.handle_list(tag)
        elif command == 'SELECT':
            self.handle_select(tag, args)
        elif command == 'SEARCH':
            self.handle_search(tag, args)
        elif command == 'FETCH':
            self.handle_fetch(tag, args)
        elif command == 'NOOP':
            self.handle_noop(tag)
        elif command == 'LOGOUT':
            self.handle_logout(tag)
        else:
            self.transport.write(f'{tag} BAD Unknown command\r\n'.encode())

    def handle_capability(self, tag):
        capabilities = 'IMAP4rev1'
        self.transport.write(f'* CAPABILITY {capabilities}\r\n'.encode())
        self.transport.write(f'{tag} OK CAPABILITY completed\r\n'.encode())

    def handle_login(self, tag, args):
        if len(args) >= 2:
            self.username = args[0].strip('"')
            self.state = 'AUTHENTICATED'
            self.transport.write(f'{tag} OK LOGIN completed\r\n'.encode())
        else:
            self.transport.write(f'{tag} BAD LOGIN requires username and password\r\n'.encode())

    def handle_list(self, tag):
        if self.state == 'AUTHENTICATED':
            self.transport.write(b'* LIST (\\Inbox) "/" "INBOX"\r\n')
            self.transport.write(f'{tag} OK LIST completed\r\n'.encode())
        else:
            self.transport.write(f'{tag} BAD Not authenticated\r\n'.encode())

    def handle_select(self, tag, args):
        try:
            if self.state == 'AUTHENTICATED':
                # Count the number of messages
                num_messages = len(self.get_user_emails())
                self.transport.write(b'* FLAGS (\\Seen \\Answered \\Flagged \\Deleted \\Draft)\r\n')
                self.transport.write(f'* {num_messages} EXISTS\r\n'.encode())
                self.transport.write(f'{tag} OK [READ-WRITE] SELECT completed\r\n'.encode())
            else:
                self.transport.write(f'{tag} BAD Not authenticated\r\n'.encode())
        except Exception as e:
            print(f"Error in handle_select: {e}")
            self.transport.write(f'{tag} BAD Internal Server Error\r\n'.encode())
            self.transport.close()

    def handle_search(self, tag, args):
        try:
            if self.state == 'AUTHENTICATED':
                mail_files = self.get_user_emails()
                if mail_files:
                    # IMAP message sequence numbers start at 1
                    message_nums = [str(i+1) for i in range(len(mail_files))]
                    response = ' '.join(message_nums)
                    self.transport.write(f'* SEARCH {response}\r\n'.encode())
                else:
                    self.transport.write(b'* SEARCH\r\n')
                self.transport.write(f'{tag} OK SEARCH completed\r\n'.encode())
            else:
                self.transport.write(f'{tag} BAD Not authenticated\r\n'.encode())
        except Exception as e:
            print(f"Error in handle_search: {e}")
            self.transport.write(f'{tag} BAD Internal Server Error\r\n'.encode())
            self.transport.close()

    def handle_fetch(self, tag, args):
        try:
            if self.state == 'AUTHENTICATED':
                if not args:
                    self.transport.write(f'{tag} BAD Missing arguments in FETCH command\r\n'.encode())
                    return

                # Parse the message numbers and fetch attributes
                msg_nums = args[0]
                fetch_attrs = args[1:] if len(args) > 1 else []

                mail_files = self.get_user_emails()
                total_messages = len(mail_files)

                # Handle ranges and specific message numbers
                for num in msg_nums.split(','):
                    if ':' in num:
                        start, end = num.split(':')
                        start = int(start)
                        end = int(end) if end != '*' else total_messages
                        indices = range(start-1, end)
                    else:
                        indices = [int(num)-1]

                    for idx in indices:
                        if 0 <= idx < total_messages:
                            mail_file = mail_files[idx]
                            with open(mail_file, 'rb') as f:
                                data = f.read()
                            size = len(data)
                            # Send the FETCH response
                            self.transport.write(f'* {idx+1} FETCH (RFC822 {{{size}}}\r\n'.encode())
                            self.transport.write(data)
                            self.transport.write(b')\r\n')
                self.transport.write(f'{tag} OK FETCH completed\r\n'.encode())
            else:
                self.transport.write(f'{tag} BAD Not authenticated\r\n'.encode())
        except Exception as e:
            print(f"Error in handle_fetch: {e}")
            self.transport.write(f'{tag} BAD Internal Server Error\r\n'.encode())
            self.transport.close()

    def handle_noop(self, tag):
        self.transport.write(f'{tag} OK NOOP completed\r\n'.encode())

    def handle_logout(self, tag):
        self.transport.write(b'* BYE IMAP4rev1 Server logging out\r\n')
        self.transport.write(f'{tag} OK LOGOUT completed\r\n'.encode())
        self.transport.close()

    def get_user_emails(self):
        try:
            escaped_username = re.escape(self.username)
            pattern = re.compile(f'^{escaped_username}_.*\\.eml$')
            files = [os.path.join(self.mail_dir, f) for f in sorted(os.listdir(self.mail_dir))]
            user_files = [f for f in files if pattern.match(os.path.basename(f))]
            return user_files
        except Exception as e:
            print(f"Error in get_user_emails: {e}")
            return []

def run_imap_server(host='0.0.0.0', port=8143, mail_dir='./mails'):
    loop = asyncio.get_event_loop()
    coro = loop.create_server(lambda: IMAPServerProtocol(mail_dir), host, port)
    server = loop.run_until_complete(coro)
    print(f"IMAP server running at {host}:{port}")
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        print("\nIMAP server stopped.")
    finally:
        server.close()
        loop.run_until_complete(server.wait_closed())
        loop.close()

if __name__ == '__main__':
    run_imap_server()
