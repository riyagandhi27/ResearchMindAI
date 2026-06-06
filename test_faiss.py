from services.embedding_service import EmbeddingService
from services.faiss_manager import FAISSManager

# embeddings
embedder = EmbeddingService()

chunks = [
    "machine learning is important",
    "flask is a web framework",
    "python is used for AI"
]

embeddings = embedder.get_embeddings(chunks)

# FAISS setup
faiss_db = FAISSManager()
faiss_db.add_embeddings(embeddings, chunks)

# test search
query = "what is flask?"
query_vector = embedder.get_embeddings([query])[0]

results = faiss_db.search(query_vector)

print("Search Results:")
for r in results:
    print("-", r)