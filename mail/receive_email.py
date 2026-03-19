import imaplib
import email
from email.header import decode_header
import os

def receive_email(imap_server, imap_port, username, password):
    mail = imaplib.IMAP4(imap_server, imap_port)
    mail.login(username, password)
    mail.select('INBOX')

    typ, data = mail.search(None, 'ALL')
    mail_ids = data[0].split()

    for mail_id in mail_ids:
        typ, msg_data = mail.fetch(mail_id, '(RFC822)')
        raw_email = msg_data[0][1]
        email_message = email.message_from_bytes(raw_email)

        # Decode email subject
        subject, encoding = decode_header(email_message['Subject'])[0]
        if isinstance(subject, bytes):
            subject = subject.decode(encoding if encoding else 'utf-8')

        # Decode email sender
        from_, encoding = decode_header(email_message.get('From'))[0]
        if isinstance(from_, bytes):
            from_ = from_.decode(encoding if encoding else 'utf-8')

        print(f"From: {from_}")
        print(f"Subject: {subject}")

        # Process email parts
        for part in email_message.walk():
            content_type = part.get_content_type()
            if part.get_content_disposition() == 'attachment':
                filename = part.get_filename()
                if filename:
                    filename = decode_header(filename)[0][0]
                    if isinstance(filename, bytes):
                        filename = filename.decode(encoding if encoding else 'utf-8')
                    filepath = os.path.join('.', filename)
                    with open(filepath, 'wb') as f:
                        f.write(part.get_payload(decode=True))
                    print(f"Attachment saved: {filepath}")
            elif content_type == 'text/plain':
                body = part.get_payload(decode=True).decode(encoding if encoding else 'utf-8')
                print("Body:", body)

    mail.logout()

if __name__ == '__main__':
    imap_server = '192.168.1.15'  # Replace with your server's IP
    imap_port = 8143  # Port used by the IMAP server
    username = 'employee'  # Username without domain
    password = 'password'  # Password is not enforced

    receive_email(imap_server, imap_port, username, password)