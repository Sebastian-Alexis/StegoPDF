import smtpd
import asyncore
import email
import os
import datetime

class CustomSMTPServer(smtpd.SMTPServer):
    def __init__(self, localaddr, remoteaddr, save_directory):
        super().__init__(localaddr, remoteaddr)
        self.save_directory = save_directory
        if not os.path.exists(self.save_directory):
            os.makedirs(self.save_directory)

    def process_message(self, peer, mailfrom, rcpttos, data, **kwargs):
        print(f'Received message from: {peer}')
        print(f'Message addressed from: {mailfrom}')
        print(f'Message addressed to  : {rcpttos}')
        print(f'Message length        : {len(data)}')


        msg = email.message_from_bytes(data)

        for part in msg.walk():
            if part.get_content_disposition() == 'attachment':
                filename = part.get_filename()
                if filename and filename.lower().endswith('.pdf'):
                    safe_filename = self.sanitize_filename(filename)
                    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
                    unique_filename = f"{timestamp}_{safe_filename}"
                    file_path = os.path.join(self.save_directory, unique_filename)
                    with open(file_path, 'wb') as f:
                        f.write(part.get_payload(decode=True))
                    print(f"Saved PDF attachment to: {file_path}")

    def sanitize_filename(self, filename):
        return "".join(c for c in filename if c.isalnum() or c in (' ', '.', '_')).rstrip()

if __name__ == '__main__':
    save_directory = 'saved_pdfs' 
    server = CustomSMTPServer(('127.0.0.1', 1025), None, save_directory)
    print('SMTP server is running on port 1025...')
    try:
        asyncore.loop()
    except KeyboardInterrupt:
        print('SMTP server has been stopped.')
