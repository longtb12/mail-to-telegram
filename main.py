import imaplib
import email
import email.utils
import requests
import time
from datetime import datetime
from dotenv import load_dotenv
import os
import re
from email.header import decode_header
import unicodedata
import ast
from log_util import get_logger
from email_type import EmailType
from ttl_int_array import TTLIntArray

# Load variables from .env into environment
load_dotenv()
username = os.getenv("GMAIL_USER")
password = os.getenv("GMAIL_APP_PASSWORD")
tele_token = os.getenv("TELEGRAM_TOKEN")
chat_id = os.getenv("CHAT_ID")
sleep_time = int(os.getenv("SLEEPTIME"))
allowed_sender = ast.literal_eval(os.getenv("ALLOWED_SENDER", "[]"))
tele_url = f'https://api.telegram.org/bot{tele_token}/sendMessage'

logger = get_logger()
already_read = TTLIntArray()

def strip_accents(s):
    s = unicodedata.normalize('NFD', s)
    return ''.join(c for c in s if not unicodedata.combining(c))

def normalize(s, remove_accents=True):
    s = s.casefold()
    s = unicodedata.normalize('NFC', s)
    if remove_accents:
        s = strip_accents(s)
    return s

def connect_imap():
    try:
        mail = imaplib.IMAP4_SSL('imap.gmail.com')
        mail.login(username, password)
        mail.select('INBOX')
        capabilities = mail.capability()[1][0].decode().split()
        if 'IDLE' not in capabilities:
            logger.error("IMAP server does not support IDLE")
        return mail
    except Exception as e:
        logger.error(f"Error connecting to IMAP: {e}")
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
        else:
            return False
        
        subject = ''.join([
            part.decode(encoding or 'utf-8') if isinstance(part, bytes) else part
            for part, encoding in decode_header(subject)
        ])

        return {'email_id': email_id,'subject': subject, 'from': from_, 'body': body}
    except Exception as e:
        logger.error(f"Error fetching email {email_id}: {e}")
        return None

def get_type(subject):
    for type in EmailType:
        if(normalize(type.value) in normalize(subject)):
            return type.name
    return False

def get_body(email_type, body):
    match = ""
    match email_type:
        case EmailType.TRAVEL_CODE.name:
            match = re.search(r"https:\/\/www\.netflix\.com\/account\/travel\/verify[^\s\]]+", body)
            return f"""<b>Subject:</b> {EmailType.TRAVEL_CODE.value}
<b>Body:</b>
Click vào <a href="{match.group()}">Link</a> để xác nhận\n
<i>***Mọi người cứ bấm vào link, rồi lấy mã 4 số là được</i>"""
        case EmailType.UPDATE_FAMILY.name:
            match = re.search(r"https:\/\/www\.netflix\.com\/account\/update-primary-location\?[^)\]\s]+", body)
            return f"""<b>Subject:</b> {EmailType.UPDATE_FAMILY.value}
<b>Body:</b>
Click vào <a href="{match.group()}">Link</a> để xác nhận\n
<i>***Mọi người cứ bấm vào link, rồi chọn Xác Nhận là được</i>"""
    
    return False

def send_to_telegram(email_data):
    try:
        email_type = get_type(email_data['subject'])
        if (email_type == False):
            return False

        body = get_body(email_type, email_data['body'])
        if (body == False):
            return False
        
        response = requests.post(tele_url, data={'chat_id': chat_id, 'text': body, 'parse_mode': 'HTML'})
        logger.info(f"{datetime.now()}: {response}")
        if response.ok:
            logger.info(f"Sent email {email_data['subject']} to Telegram")
            return True
        else:
            logger.error(f"Failed to send to Telegram: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Error sending to Telegram: {e}")
        return False

def mark_as_unread(mail, email_id):
    try:
        mail.store(email_id, '-FLAGS', '\\Seen')
    except Exception as e:
        logger.error(f"Error marking email {email_id} as unread: {e}")

def monitor_emails():
    while True:
        try:
            while True:
                mail = connect_imap()
                today = datetime.today().strftime("%d-%b-%Y")
                _, email_ids = mail.search(None, f'(UNSEEN SINCE {today})')

                ids = []
                for email_id in email_ids[0].split():
                    if (already_read.exists(email_id) == False):
                        ids.append(email_id)

                logger.info(f"{datetime.now()}: {ids}")
                
                for email_id in ids:
                    already_read.add(email_id)
                    email_data = get_email_details(mail, email_id)
                    if email_data == False or send_to_telegram(email_data) == False:
                        mark_as_unread(mail, email_id)
                
                time.sleep(sleep_time)        
        except Exception as e:
            logger.error(f"Error: {e}")
            time.sleep(sleep_time)  
        finally:
            try:
                mail.logout()
            except:
                pass
            time.sleep(1)  

if __name__ == '__main__':
    logger.info("Starting Gmail to Telegram forwarder")
    monitor_emails()