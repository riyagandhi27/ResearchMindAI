from sentence_transformers import CrossEncoder


class Reranker:

    def __init__(self):
        # lightweight but strong reranker model
        self.model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

    def rerank(self, query, chunks, top_k=3):

        if not chunks:
            return []

        pairs = [(query, chunk["text"] if isinstance(chunk, dict) else chunk) for chunk in chunks]

        scores = self.model.predict(pairs)

        ranked = []

        for i, score in enumerate(scores):
            item = chunks[i]

            if isinstance(item, dict):
                text = item["text"]
            else:
                text = item

            ranked.append({
                "text": text,
                "score": float(score)
            })

        ranked = sorted(ranked, key=lambda x: x["score"], reverse=True)

        return ranked[:top_k]