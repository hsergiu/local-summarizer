# Mail summarization tool
- create a .env file by copying .env.default and replacing 
the placeholder mail with yours (only gmail is supported)
- authorize this tool through the OAuth 2 process by checking
the necessary scopes
- install the libraries using `pip install -r requirements.txt` in
the root folder
- run the tool using `python main.py`

> distilbart-cnn-12-6 is used to summarize the supported
> mail parts (check
> [mime types](https://github.com/hsergiu/local-summarizer/blob/master/src/extractor.py#L29))