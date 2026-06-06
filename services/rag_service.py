from services.chunking_service import ChunkingService
from services.embedding_service import EmbeddingService
from services.faiss_manager import FAISSManager
from services.groq_service import GroqService
from services.reranker import Reranker
from services.cache import get_cache, set_cache


class RAGService:

    def __init__(self):
        self.chunker = ChunkingService()
        self.embedder = EmbeddingService()
        self.faiss_manager = FAISSManager()
        self.llm = GroqService()
        self.reranker = Reranker()
        self.chat_history = {}

    def reset(self):
        self.faiss_manager.reset()
        self.chat_history = {}

    def add_to_memory(self, doc_id, role, message):
        if doc_id not in self.chat_history:
            self.chat_history[doc_id] = []

        self.chat_history[doc_id].append({
            "role": role,
            "message": message
        })

    def get_memory(self, doc_id, limit=6):
        return self.chat_history.get(doc_id, [])[-limit:]

    def index_document(self, text, doc_id, source_name="uploaded_file"):
        if not text or not text.strip():
            print("[RAG] Empty text. Skipping indexing.")
            return

        chunks = self.chunker.chunk_text(text)

        if not chunks:
            print("[RAG] No chunks created.")
            return

        for chunk in chunks:
            chunk["doc_id"] = doc_id
            chunk["source"] = source_name

        chunk_texts = [chunk["text"] for chunk in chunks]

        embeddings = self.embedder.get_embeddings(chunk_texts)

        if embeddings is None or len(embeddings) == 0:
            print("[RAG] No embeddings created.")
            return

        self.faiss_manager.add_document(embeddings, chunks)

        print(f"[RAG] Indexed {len(chunks)} chunks for doc_id={doc_id}")

    def _build_context(self, items):
        context = ""

        for i, item in enumerate(items, 1):
            text = item.get("text", "")
            source = item.get("source", "uploaded document")
            page = item.get("page", "N/A")
            score = item.get("score", "N/A")

            context += f"""
[CITATION {i}]
Source: {source}
Page: {page}
Score: {score}

Content:
{text}

"""

        return context

    def _build_memory_text(self, doc_id):
        history = self.get_memory(doc_id)

        memory_text = ""

        for h in history:
            memory_text += f"{h['role']}: {h['message']}\n"

        return memory_text

    def _retrieve_relevant_chunks(self, question, doc_id):
        query_embedding = self.embedder.get_embedding(question)

        candidates = self.faiss_manager.search(
            query_embedding,
            k=10
        )

        candidates = [
            c for c in candidates
            if c.get("doc_id") == doc_id
        ]

        if not candidates:
            return []

        relevant_chunks = self._safe_rerank(
            question,
            candidates,
            top_k=5
        )

        return relevant_chunks

    def _safe_rerank(self, question, candidates, top_k=5):
        try:
            reranked = self.reranker.rerank(
                question,
                candidates,
                top_k=top_k
            )

            if reranked:
                return reranked

        except Exception as e:
            print("[RAG] Reranker skipped:", e)

        return candidates[:top_k]

    def _build_prompt(self, question, memory_text, context):
        return f"""
You are ResearchMind AI, a helpful research assistant.

Answer the user's question using ONLY the provided document context.

Rules:
- Do not use outside knowledge.
- If the answer is not found in the context, say: "I could not find this information in the uploaded document."
- Be clear and concise.
- Mention citations when useful using [CITATION 1], [CITATION 2], etc.

Conversation History:
{memory_text}

Document Context:
{context}

User Question:
{question}
"""

    def ask_question(self, question, doc_id="default"):
        if not question or not question.strip():
            return "Empty question"

        question = question.strip()

        self.add_to_memory(doc_id, "user", question)

        memory_text = self._build_memory_text(doc_id)

        relevant_chunks = self._retrieve_relevant_chunks(question, doc_id)

        if not relevant_chunks:
            return "No relevant information found in document"

        context = self._build_context(relevant_chunks)

        final_prompt = self._build_prompt(
            question,
            memory_text,
            context
        )

        answer = self.llm.generate_answer(question, final_prompt)

        self.add_to_memory(doc_id, "assistant", answer)

        return answer

    def ask_question_stream(self, question, doc_id="default"):
        if not question or not question.strip():
            yield "Empty question"
            return

        question = question.strip()

        cache_key = f"qa:{doc_id}:{question.lower()}"

        cached_answer = get_cache(cache_key)

        if cached_answer:
            print(f"[CACHE HIT] {cache_key}")
            yield cached_answer
            return

        print(f"[CACHE MISS] {cache_key}")

        self.add_to_memory(doc_id, "user", question)

        memory_text = self._build_memory_text(doc_id)

        relevant_chunks = self._retrieve_relevant_chunks(question, doc_id)

        if not relevant_chunks:
            yield "No relevant information found in document"
            return

        context = self._build_context(relevant_chunks)

        final_prompt = self._build_prompt(
            question,
            memory_text,
            context
        )

        stream = self.llm.generate_answer_stream(
            question,
            final_prompt
        )

        full_response = ""

        for chunk in stream:
            full_response += chunk
            yield chunk

        if full_response.strip():
            self.add_to_memory(doc_id, "assistant", full_response)
            set_cache(cache_key, full_response)