import os
import pickle

import faiss
import numpy as np


class FAISSManager:

    def __init__(
        self,
        dimension=384,
        index_path="vector_store/faiss.index",
        chunks_path="vector_store/chunks.pkl"
    ):
        self.dimension = dimension
        self.index_path = index_path
        self.chunks_path = chunks_path

        os.makedirs("vector_store", exist_ok=True)

        self.index = faiss.IndexFlatL2(dimension)
        self.chunks = []

        self.load()

    def reset(self):
        self.index = faiss.IndexFlatL2(self.dimension)
        self.chunks = []

        self.save()

    def save(self):
        faiss.write_index(self.index, self.index_path)

        with open(self.chunks_path, "wb") as f:
            pickle.dump(self.chunks, f)

        print("[FAISS] Saved index and chunks")

    def load(self):
        if os.path.exists(self.index_path) and os.path.exists(self.chunks_path):
            self.index = faiss.read_index(self.index_path)

            with open(self.chunks_path, "rb") as f:
                self.chunks = pickle.load(f)

            print(f"[FAISS] Loaded {len(self.chunks)} chunks")
        else:
            print("[FAISS] No saved index found. Starting fresh.")

    def add_document(self, embeddings, chunks):
        if embeddings is None or len(embeddings) == 0:
            return

        embeddings = np.array(embeddings).astype("float32")

        self.index.add(embeddings)
        self.chunks.extend(chunks)

        self.save()

    def search(self, query_embedding, k=5):
        if self.index.ntotal == 0:
            return []

        query_embedding = np.array([query_embedding]).astype("float32")

        distances, indices = self.index.search(query_embedding, k)

        results = []

        for distance, idx in zip(distances[0], indices[0]):
            if idx == -1:
                continue

            if idx < len(self.chunks):
                item = self.chunks[idx].copy()
                item["score"] = float(distance)
                results.append(item)

        return results