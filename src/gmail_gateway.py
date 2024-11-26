import os
import logging

import google.auth.exceptions
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import base64
from src.extractor import Extractor


class GmailGateway:
    def __init__(self, scopes):
        self.scopes = scopes
        self.extractor = Extractor()

    def authenticate_gmail(self):
        logging.info("Authenticating Gmail API...")
        creds = None
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', self.scopes)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except google.auth.exceptions.RefreshError:
                    flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', self.scopes)
                    creds = flow.run_local_server(port=0)
            else:
                flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', self.scopes)
                creds = flow.run_local_server(port=0)

            with open('token.json', 'w') as token:
                token.write(creds.to_json())

        return build('gmail', 'v1', credentials=creds)

    def read_emails(self, max_results=5):
        service = self.authenticate_gmail()
        results = service.users().messages().list(userId='me', maxResults=max_results).execute()
        messages = results.get('messages', [])
        emails = []

        for msg in messages:
            email_data = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
            emails.append(email_data)

        return emails

    def process_mail(self, msg):
        headers = msg['payload']['headers']
        subject = next((header['value'] for header in headers if header['name'] == 'Subject'), 'No Subject')
        logging.info(f"Email Subject: {subject}")

        parts_to_summarize = []
        if 'parts' in msg['payload']:
            for part in msg['payload']['parts']:
                mime_type = part['mimeType']
                body_data = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8') if 'data' in part[
                    'body'] else None

                extracted_text = self.extractor.extract(body_data, mime_type)
                if extracted_text:
                    parts_to_summarize.append(extracted_text)
                    logging.info(f"Extracted text for MIME type: {mime_type}")
                else:
                    logging.warning(f"No text could be extracted for MIME type: {mime_type}")

        return parts_to_summarize
