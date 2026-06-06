from services.gemini_service import GeminiService

gemini = GeminiService()

question = "What is Artificial Intelligence?"

context = """
Artificial Intelligence (AI) is a branch of computer science
that enables machines to perform tasks that normally require
human intelligence.
"""

answer = gemini.generate_answer(
    question,
    context
)

print("\nANSWER:\n")
print(answer)