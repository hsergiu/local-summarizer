import os

import base64
import email
import logging
import PyPDF2
import re
import html2text
from transformers import BartTokenizer, BartForConditionalGeneration
from langchain.text_splitter import CharacterTextSplitter
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from email.mime.text import MIMEText
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.insert',
    'https://www.googleapis.com/auth/gmail.send'
]

tokenizer = BartTokenizer.from_pretrained('facebook/bart-large-cnn')
model = BartForConditionalGeneration.from_pretrained('facebook/bart-large-cnn')
text_splitter = CharacterTextSplitter.from_tiktoken_encoder(
    chunk_size=1024, chunk_overlap=50
)

my_email = os.getenv("MY_EMAIL")

if not my_email:
    logging.error("my_email not set. Please define it in a .env file.")
    exit()

def clean_text(text):
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^\w\s,.!?]', '', text)
    return text.strip()

def authenticate_gmail():
    logging.info("Authenticating Gmail API...")
    creds = None
    if os.path.exists('token.json'):
        logging.info("Found existing credentials file (token.json).")
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logging.info("Refreshing expired credentials...")
            creds.refresh(Request())
        else:
            logging.info("Starting authentication flow for new credentials.")
            flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', SCOPES)
            creds = flow.run_local_server(port=0)

        with open('token.json', 'w') as token:
            logging.info("Saving credentials to token.json")
            token.write(creds.to_json())

    return creds

def read_emails(creds, limit=1):
    try:
        logging.info(f"Reading the last {limit} emails...")
        service = build('gmail', 'v1', credentials=creds)
        results = service.users().messages().list(userId='me', maxResults=limit).execute()
        messages = results.get('messages', [])

        if not messages:
            logging.info("No messages found.")
            return []

        logging.info(f"Found {len(messages)} messages.")
        emails = []
        for message in messages:
            msg = service.users().messages().get(userId='me', id=message['id'], format='full').execute()
            emails.append(msg)
        return emails
    except Exception as e:
        logging.error(f"An error occurred while reading emails: {e}")
        return []

def summarize_text(text):
    logging.info("Splitting text into chunks...")
    cleanedText = clean_text(text)
    chunks = text_splitter.split_text(cleanedText)

    all_summaries = []

    for chunk in chunks:
        logging.info(f"Summarizing chunk of character size {len(chunk)}...")

        tokens = tokenizer.encode(chunk, return_tensors="pt", max_length=1024, truncation=True)
        num_tokens = len(tokens[0])

        logging.info(f"Chunk has {num_tokens} tokens.")

        summary_ids = model.generate(tokens, max_length=150, min_length=40, length_penalty=2.0, num_beams=6,
                                     do_sample=False)
        summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)

        all_summaries.append(summary)

    logging.info("All chunks summarized successfully.")

    final_summary = " ".join(all_summaries)
    return final_summary

def extract_text_from_pdf(pdf_file):
    logging.info(f"Extracting text from PDF file: {pdf_file}")
    text = ''
    try:
        with open(pdf_file, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                text += page.extract_text() or ''
        logging.info("Text extracted successfully from PDF.")
    except Exception as e:
        logging.error(f"An error occurred while extracting text from the PDF: {e}")
    return text

def insert_email(creds, to_email, subject, body):
    try:
        logging.info(f"Inserting email to {to_email} with subject '{subject}'")
        service = build('gmail', 'v1', credentials=creds)

        message = MIMEText(body)
        message['to'] = to_email
        message['subject'] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

        message = {'raw': raw}
        insert_message = service.users().messages().insert(userId="me", body=message).execute()
        logging.info(f"Email inserted successfully: {insert_message['id']}")
        return insert_message
    except Exception as e:
        logging.error(f"An error occurred while inserting email: {e}")
        return None

def send_email(creds, to_email, subject, body):
    try:
        logging.info(f"Sending email to {to_email} with subject '{subject}'")
        service = build('gmail', 'v1', credentials=creds)

        message = MIMEText(body)
        message['to'] = to_email
        message['subject'] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

        message = {'raw': raw}
        send_message = service.users().messages().send(userId="me", body=message).execute()
        logging.info(f"Email sent successfully: {send_message['id']}")
        return send_message
    except Exception as e:
        logging.error(f"An error occurred while sending email: {e}")
        return None

def get_attachment(service, message_id, attachment_id):
    try:
        logging.info(f"Fetching attachment with ID: {attachment_id}")
        attachment = service.users().messages().attachments().get(
            userId='me', messageId=message_id, id=attachment_id
        ).execute()
        return base64.urlsafe_b64decode(attachment['data'])
    except Exception as e:
        logging.error(f"Error fetching attachment: {e}")
        return None

def process_pdf_attachment(service, msg, part, creds, to_email):
    if 'body' in part and 'attachmentId' in part['body']:
        attachment_id = part['body']['attachmentId']
        attachment_data = get_attachment(service, msg['id'], attachment_id)
        if attachment_data:

            with open('temp.pdf', 'wb') as f:
                f.write(attachment_data)
            logging.info("PDF file saved as 'temp.pdf'")
            pdf_text = extract_text_from_pdf('temp.pdf')
            pdf_summary = summarize_text(pdf_text)
            logging.info("Summarized pdf:" + pdf_summary)
            # insert_email(creds, to_email, 'PDF Summary', pdf_summary)
        else:
            logging.warning("Could not retrieve the PDF attachment.")
    else:
        logging.warning("PDF attachment does not contain 'attachmentId'.")

def process_text_html(part, creds, to_email):
    if 'body' in part and 'data' in part['body']:
        logging.info("Extracting HTML content from the email.")
        html_content = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')

        plain_text = html2text.html2text(html_content)
        email_summary = summarize_text(plain_text)
        logging.info("HTML converted to plain text before summarization:" + plain_text)
        logging.info("Summarized text:" + email_summary)
        # insert_email(creds, to_email, 'Text HTML', pdf_summary)
        return email_summary
    else:
        logging.warning("No 'body' or 'data' found in the HTML email part.")
        return None

def process_text_plain(part, creds, to_email):
    if 'body' in part and 'data' in part['body']:
        logging.info("Extracting plain text from the email.")
        body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
        email_summary = summarize_text(body)
        logging.info("Text before:" + body)
        logging.info("Summarized text:" + email_summary)
        # insert_email(creds, to_email, 'Text plain', pdf_summary)
        return email_summary
    else:
        logging.warning("No 'body' or 'data' found in the plain text email part.")
        return None

def main():
    logging.info("Starting the Gmail automation script.")
    creds = authenticate_gmail()

    to_email = my_email

    emails = read_emails(creds)

    if not emails:
        logging.info("No emails to process.")
        return

    service = build('gmail', 'v1', credentials=creds)

    for msg in emails:
        logging.debug('Found message keys: ' + ', '.join(msg.keys()))
        headers = msg['payload']['headers']
        subject = next((header['value'] for header in headers if header['name'] == 'Subject'), 'No Subject')
        logging.info('Current email subject: ' + subject)
        if 'payload' in msg and 'parts' in msg['payload']:
            logging.debug('Found payload keys: ' + ', '.join(msg['payload'].keys()))
            for part in msg['payload']['parts']:
                logging.debug('Found part type: ' + part['mimeType'])
                if part['mimeType'] == 'application/pdf':
                    textPDF = process_pdf_attachment(service, msg, part, creds, to_email)
                if part['mimeType'] == 'text/plain':
                    textPlain = process_text_plain(part, creds, to_email)
                if part['mimeType'] == 'text/html':
                    textHTML = process_text_html(part, creds, to_email)

    logging.info("Script execution completed.")

if __name__ == "__main__":
    main()
