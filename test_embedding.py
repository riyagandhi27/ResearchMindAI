from services.embedding_service import EmbeddingService

# Create object
embedder = EmbeddingService()

# Sample chunks
chunks = [
    "hello world",
    "artificial intelligence is powerful",
    "flask is a python web framework"
]

# Test multiple embeddings
vectors = embedder.get_embeddings(chunks)

print("Number of chunks:", len(chunks))
print("Number of vectors:", len(vectors))
print("Embeddings shape:", vectors.shape)
print("First vector sample:", vectors[0][:5])

# Test single embedding (NEW)
query = "What is artificial intelligence?"

query_vector = embedder.get_embedding(query)

print("\nQuery:", query)
print("Query vector shape:", query_vector.shape)
print("Query vector sample:", query_vector[:5])