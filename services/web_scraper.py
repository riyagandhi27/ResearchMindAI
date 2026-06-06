import requests
from bs4 import BeautifulSoup


class WebScraper:

    def extract_text(self, url):

        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.text, "html.parser")

        # remove unwanted tags
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        # extract clean text
        text = soup.get_text(separator=" ")

        # clean extra spaces
        cleaned_text = " ".join(text.split())

        return cleaned_text