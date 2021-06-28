import requests

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.130 Safari/537.36'


class YoutubeCommentScraper:
    def __init__(self):
        self.session = requests.session()
        self.session.headers['User-Agent'] = USER_AGENT
