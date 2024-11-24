import logging
from transformers import BartTokenizer, BartForConditionalGeneration
from langchain.text_splitter import RecursiveCharacterTextSplitter
import re


class Summarizer:
    def __init__(self):
        logging.info("Loading summarization model and tokenizer...")
        self.tokenizer = BartTokenizer.from_pretrained('facebook/bart-large-cnn')
        self.model = BartForConditionalGeneration.from_pretrained('facebook/bart-large-cnn')
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1024,
            chunk_overlap=80,
            separators=["\n\n", "\n", ". ", "? ", "! "]
        )

    def _generate(self, tokenized_input):
        summary_ids = self.model.generate(
            tokenized_input['input_ids'],
            max_length=300,
            min_length=100,
            num_beams=6,
            # length_penalty=0.1,
            # no_repeat_ngram_size=3
        )
        return self.tokenizer.decode(summary_ids[0], skip_special_tokens=True)

    def summarize(self, text):
        logging.info("Summarizing text...")
        chunks = self.text_splitter.split_text(text)
        summaries = []
        logging.info(f"Text split into {len(chunks)} chunks")

        tokenized_chunks = [
            self.tokenizer(chunk, return_tensors="pt", max_length=1024, truncation=True)
            for chunk in chunks
        ]

        for i, tokenized_chunk in enumerate(tokenized_chunks):
            logging.info(f"Processing chunk number: {i + 1}/{len(tokenized_chunks)}")
            result = self._generate(tokenized_chunk)
            summaries.append(result)

        logging.info("Processing done. Joining summaries...")
        summary_joined = " ".join(summaries)
        summary_sentences = [sentence.strip() for sentence in re.split(r'(?<=[.!?]) +', summary_joined) if sentence]
        final_summary = "\n".join(summary_sentences)

        return "\n" + final_summary

