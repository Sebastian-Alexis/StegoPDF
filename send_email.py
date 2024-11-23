import smtplib
from email.message import EmailMessage
import os

def send_email(smtp_server, smtp_port, sender_email, recipient_email, subject, body, attachment_path=None):
    msg = EmailMessage()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = subject
    msg.set_content(body)

    # Attach PDF if provided
    if attachment_path and os.path.isfile(attachment_path):
        with open(attachment_path, 'rb') as f:
            file_data = f.read()
            file_name = os.path.basename(attachment_path)
        msg.add_attachment(file_data, maintype='application', subtype='pdf', filename=file_name)

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.send_message(msg)
        print("Email sent successfully.")

if __name__ == '__main__':
    smtp_server = '192.168.1.15'  # Replace with your server's IP
    smtp_port = 8025  # Port used by the SMTP server
    sender_email = 'user1@example.com'
    recipient_email = 'employee'
    subject = 'Test Email with PDF Attachment'
    body = 'This email contains a PDF attachment.'
    attachment_path = 'path/to/your/file.pdf'  # Replace with your PDF file path

    send_email(smtp_server, smtp_port, sender_email, recipient_email, subject, body, attachment_path)
