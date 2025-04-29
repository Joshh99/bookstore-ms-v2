from kafka import KafkaConsumer
import json
import smtplib
from email.mime.text import MIMEText
import os
from dotenv import load_dotenv

load_dotenv()
KAFKA_BROKER = os.getenv("KAFKA_BROKER").split(",")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC")
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
ANDREW_ID = os.getenv("ANDREW_ID")

consumer = KafkaConsumer(
    KAFKA_TOPIC,
    bootstrap_servers=KAFKA_BROKER,
    value_deserializer=lambda x: json.loads(x.decode('utf-8'))
)

def send_email(customer):
    msg = MIMEText(
        f"Dear {customer['name']},\nWelcome to the Book store created by {ANDREW_ID}.\n"
        "Exceptionally this time we won’t ask you to click a link to activate your account."
    )
    msg['Subject'] = "Activate your book store account"
    msg['From'] = SMTP_USER
    msg['To'] = customer['userId']
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)

for message in consumer:
    customer = message.value
    send_email(customer)