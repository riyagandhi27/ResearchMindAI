from sentence_transformers import SentenceTransformer


class EmbeddingService:

    def __init__(self):
        self.model = SentenceTransformer("all-MiniLM-L6-v2")

    def get_embeddings(self, texts):
        if not texts:
            return []

        return self.model.encode(texts)

    def get_embedding(self, text):
        if not text:
            return []

        return self.model.encode(text)