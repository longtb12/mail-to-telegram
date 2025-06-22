import mysql.connector
import os

def get_mysql_connection():
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        database=os.getenv("MYSQL_DATABASE", "mail_to_telegram")
    )

def save_email_to_db(email_data):
    conn = get_mysql_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO emails (email_id, subject, sender, body, body_snippet)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            str(email_data.get('email_id')),
            email_data.get('subject'),
            email_data.get('from'),
            email_data.get('raw_body'),
            email_data.get('body_snippet')
        ))
        conn.commit()
    finally:
        cursor.close()
        conn.close()