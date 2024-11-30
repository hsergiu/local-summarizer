import logging
from src.gmail_gateway import GmailGateway
from src.summarizer import Summarizer
from src.extractor import Extractor
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send'
]


class Main:
    def __init__(self):
        self.gmail_gateway = GmailGateway(SCOPES)
        self.summarizer = Summarizer()
        self.my_email = os.getenv("MY_EMAIL")
        self.nr_emails_read = os.getenv("NR_EMAILS_READ")
        self.debug = os.getenv("DEBUG")
        if not self.my_email and not self.debug:
            logging.error("MY_EMAIL is not set in the environment variables.")
            exit()

    def run(self):
        emails = self.gmail_gateway.read_emails(self.nr_emails_read)
        summaries = []
        for email_data in emails:
            parts_to_summarize = self.gmail_gateway.process_mail(email_data)
            for pts in parts_to_summarize:
                summary = self.summarizer.summarize(pts)
                summaries.append(summary)
            logging.info(f"Summary: {summaries}")

    def run_debug(self):
        test_file_path = "test.txt"
        text = Extractor.extract_local(test_file_path)
        summary = self.summarizer.summarize(text)
        logging.info(f"Summary: {summary}")


if __name__ == "__main__":
    app = Main()
    if app.debug:
        app.run_debug()
    else:
        app.run()
