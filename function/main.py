import imaplib
import email
import email.utils
import requests
from datetime import datetime
from dotenv import load_dotenv
import os
import re

# Load variables from .env into environment
load_dotenv()
username = os.getenv("GMAIL_USER")
password = os.getenv("GMAIL_APP_PASSWORD")
tele_token = os.getenv("TELEGRAM_TOKEN")
chat_id = os.getenv("CHAT_ID")
allowed_sender = os.getenv("ALLOWED_SENDER")
tele_url = f'https://api.telegram.org/bot{tele_token}/sendMessage'

def connect_imap():
    try:
        mail = imaplib.IMAP4_SSL('imap.gmail.com')
        mail.login(username, password)
        mail.select('INBOX')
        capabilities = mail.capability()[1][0].decode().split()
        if 'IDLE' not in capabilities:
            print("IMAP server does not support IDLE")
        return mail
    except Exception as e:
        print(f"Error connecting to IMAP: {e}")
        raise

def get_email_details(mail, email_id):
    try:
        _, data = mail.fetch(email_id, '(RFC822)')
        msg = email.message_from_bytes(data[0][1])
        subject = msg['subject'] or '(No Subject)'
        from_ = msg['from'] or '(No Sender)'
        body = ''
        sender = email.utils.parseaddr(msg.get("From"))[1]
        if sender in allowed_sender and msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == 'text/plain':
                    body = part.get_payload(decode=True).decode()
                    break
        
        return {'subject': subject, 'from': from_, 'body': body}
    except Exception as e:
        print(f"Error fetching email {email_id}: {e}")
        return None

def send_to_telegram(email_data):
    try:
        body = email_data['body']
        match = re.search(r"https:\/\/www\.netflix\.com\/account\/travel\/verify[^\s\]]+", body)
        if(match):
            body = match.group()

        text = f"New Email\nFrom: {email_data['from']}\nBody: {body}"
        response = requests.post(tele_url, data={'chat_id': chat_id, 'text': text})
        print(f"{datetime.now()}: {response}")
        if response.ok:
            print(f"Sent email {email_data['subject']} to Telegram")
            return True
        else:
            print(f"Failed to send to Telegram: {response.text}")
            return False
    except Exception as e:
        print(f"Error sending to Telegram: {e}")
        return False

def mark_as_read(mail, email_id):
    try:
        mail.store(email_id, '+FLAGS', '\\Seen')
        print(f"Marked email {email_id} as read")
    except Exception as e:
        print(f"Error marking email {email_id} as read: {e}")

if __name__ == '__main__':
    mail = connect_imap()
    today = datetime.today().strftime("%d-%b-%Y")
    _, email_ids = mail.search(None, f'(UNSEEN SINCE {today})')
                
    print(f"{datetime.now()}: {email_ids}")
    for email_id in email_ids[0].split():
        email_data = get_email_details(mail, email_id)
        if email_data and send_to_telegram(email_data):
            mark_as_read(mail, email_id)

