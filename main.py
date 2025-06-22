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
from mysql_util import save_email_to_db

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

def build_search_criteria():
    today = datetime.today().strftime("%d-%b-%Y")
    if allowed_sender:
        # Build nested ORs for multiple senders
        senders = [f'FROM "{sender}"' for sender in allowed_sender]
        if len(senders) == 1:
            sender_criteria = senders[0]
        else:
            # Nest ORs: OR OR FROM "a" FROM "b" FROM "c"
            sender_criteria = senders[0]
            for s in senders[1:]:
                sender_criteria = f'OR {sender_criteria} {s}'
        criteria = f'UNSEEN SINCE {today} {sender_criteria}'
    else:
        criteria = f'UNSEEN SINCE {today}'
    return criteria

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
        sender = email.utils.parseaddr(msg.get("From"))[1]
        logger.info('Trying to read sender:' + sender)

        body = ''
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == 'text/plain':
                    body = part.get_payload(decode=True).decode()
                    break
        else:
            return False
        
        raw_body = ''
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == 'text/html':
                    raw_body = part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8', errors='replace')
                    break
                elif part.get_content_type() == 'text/plain' and not raw_body:
                    # Fallback to plain text if no HTML found
                    raw_body = part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8', errors='replace')
        
        subject = ''.join([
            part.decode(encoding or 'utf-8') if isinstance(part, bytes) else part
            for part, encoding in decode_header(subject)
        ])
        logger.info(f"Trying to read an email with subject {email_id}: {subject}")

        return {'email_id': int(email_id.decode()),'subject': subject, 'from': from_, 'body': body, 'raw_body': raw_body, 'body_snippet': body[:100] if body else ''}
    except Exception as e:
        logger.error(f"Error fetching email {email_id}: {e}")
        return False

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

def get_body_detail(email_data):
    email_type = get_type(email_data['subject'])
    if (email_type == False):
        return False

    body = get_body(email_type, email_data['body'])
    if (body == False):
        return False
    
    return body

def send_to_telegram(subject, body):
    try:
        logger.info(f"Trying to send email ({subject}) to Telegram")
        response = requests.post(tele_url, data={'chat_id': chat_id, 'text': body, 'parse_mode': 'HTML'})
        logger.info(f"{datetime.now()}: {response}")
        if response.ok:
            logger.info(f"Sent email {subject} to Telegram")
            return True
        else:
            logger.error(f"Failed to send to Telegram: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Error sending to Telegram: {e}")
        return False

def monitor_emails():
    while True:
        try:
            while True:
                mail = connect_imap()
                criteria = build_search_criteria()
                _, email_ids = mail.search(None, criteria)

                for email_id in email_ids[0].split():
                    logger.info(f"Processing email_id: {email_id}")
                    email_data = get_email_details(mail, email_id)
                    if email_data:
                        body = get_body_detail(email_data)
                        if body:
                            send_to_telegram(email_data['subject'], body)
                            save_email_to_db(email_data)
                
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
    logger.info("Starting email monitoring...")
    monitor_emails()