class ChunkingService:

    def chunk_text(self, text, chunk_size=500, overlap=100, page_number=0):

        if not text:
            return []

        words = text.split()
        chunks = []

        start = 0

        while start < len(words):

            end = start + chunk_size
            chunk_words = words[start:end]

            chunks.append({
                "text": " ".join(chunk_words),
                "page": page_number
            })

            start = end - overlap  # overlap for context continuity

            if start < 0:
                start = 0

        return chunks