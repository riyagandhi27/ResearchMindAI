import re


class TextCleaner:

    def clean(self, text):

        if not text:
            return ""

        # 1. Remove HTML leftovers
        text = re.sub(r"<.*?>", " ", text)

        # 2. Remove special characters (keep basic punctuation)
        text = re.sub(r"[^a-zA-Z0-9\s.,]", " ", text)

        # 3. Remove extra spaces
        text = re.sub(r"\s+", " ", text)

        # 4. Strip leading/trailing spaces
        text = text.strip()

        return text