import imaplib
import email
import email.utils
import requests
import logging
import time
from datetime import datetime
from dotenv import load_dotenv
import os

# Load variables from .env into environment
load_dotenv()
username = os.getenv("GMAIL_USER")
password = os.getenv("GMAIL_APP_PASSWORD")
tele_token = os.getenv("TELEGRAM_TOKEN")
chat_id = os.getenv("CHAT_ID")
sleep_time = int(os.getenv("SLEEPTIME"))
allowed_sender = os.getenv("ALLOWED_SENDER")
tele_url = 'https://api.telegram.org/bot{tele_token}/sendMessage'

# Set up logging
logging.basicConfig(filename='gmail_to_telegram.log', level=logging.INFO)

def connect_imap():
    try:
        mail = imaplib.IMAP4_SSL('imap.gmail.com')
        mail.login(username, password)
        mail.select('INBOX')
        capabilities = mail.capability()[1][0].decode().split()
        logging.info(f"Server capabilities: {capabilities}")
        if 'IDLE' not in capabilities:
            logging.error("IMAP server does not support IDLE")
        return mail
    except Exception as e:
        logging.error(f"Error connecting to IMAP: {e}")
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
                    body = part.get_payload(decode=True).decode()[:500]
                    break
        
        return {'subject': subject, 'from': from_, 'body': body}
    except Exception as e:
        logging.error(f"Error fetching email {email_id}: {e}")
        return None

def send_to_telegram(email_data):
    try:
        text = f"New Email\nFrom: {email_data['from']}\nSubject: {email_data['subject']}\nBody: {email_data['body']}"
        response = requests.post(tele_url, data={'chat_id': chat_id, 'text': text})
        if response.ok:
            logging.info(f"Sent email {email_data['subject']} to Telegram")
            return True
        else:
            logging.error(f"Failed to send to Telegram: {response.text}")
            return False
    except Exception as e:
        logging.error(f"Error sending to Telegram: {e}")
        return False

def mark_as_read(mail, email_id):
    try:
        mail.store(email_id, '+FLAGS', '\\Seen')
        logging.info(f"Marked email {email_id} as read")
    except Exception as e:
        logging.error(f"Error marking email {email_id} as read: {e}")

def monitor_emails():
    while True:
        try:
            logging.info("Starting IMAP IDLE monitoring")
            while True:
                mail = connect_imap()
                today = datetime.today().strftime("%d-%b-%Y")
                _, email_ids = mail.search(None, f'(UNSEEN SINCE {today})')
                print(email_ids)
                for email_id in email_ids[0].split():
                    email_data = get_email_details(mail, email_id)
                    if email_data and send_to_telegram(email_data):
                        mark_as_read(mail, email_id)
                
                time.sleep(sleep_time)        
        except Exception as e:
            logging.error(f"Error in IMAP IDLE: {e}")
            time.sleep(sleep_time)  
        finally:
            try:
                mail.logout()
            except:
                pass
            time.sleep(1)  

if __name__ == '__main__':
    logging.info("Starting Gmail to Telegram forwarder (IMAP IDLE)")
    monitor_emails()

