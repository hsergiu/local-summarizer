import logging
import html2text
import PyPDF2


class Extractor:
    def __init__(self):
        self.html_parser = html2text.HTML2Text()

    @staticmethod
    def extract_local(file_path):
        logging.info(f"Extracting from local text file: {file_path}")
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                text = file.read()

            if not text:
                logging.warning("The file is empty.")
                return None

            logging.info("Text successfully read from file")
            return text
        except FileNotFoundError:
            logging.error(f"File not found: {file_path}. Define a test file to summarize the content")
        except Exception as e:
            logging.error(f"An error occurred while reading the file: {e}")

    def extract_mail(self, part, mime_type):
        if mime_type == 'text/plain':
            return self._extract_text_plain(part)
        elif mime_type == 'text/html':
            return self._extract_text_html(part)
        elif mime_type == 'application/pdf':
            return self._extract_text_pdf(part)
        else:
            logging.warning(f"Unsupported MIME type: {mime_type}")
            return None

    def _extract_text_plain(self, text_data):
        logging.info("Extracting plain text...")
        return text_data.strip()

    def _extract_text_html(self, html_data):
        logging.info("Extracting plain text from HTML...")
        return self.html_parser.handle(html_data)

    def _extract_text_pdf(self, pdf_file_path):
        logging.info(f"Extracting text from PDF file: {pdf_file_path}")
        try:
            with open(pdf_file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                return " ".join([page.extract_text() or '' for page in reader.pages])
        except Exception as e:
            logging.error(f"An error occurred while extracting text from PDF: {e}")
            return None
