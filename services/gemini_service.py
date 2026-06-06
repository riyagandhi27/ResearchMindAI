import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()


class GeminiService:

    def __init__(self):

        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")

        genai.configure(api_key=api_key)

        self.model = genai.GenerativeModel(
            "gemini-flash-latest"
        )

    # =========================
    # NORMAL RESPONSE (NON-STREAM)
    # =========================
    def generate_answer(self, question, context):

        if not context or context.strip() == "":
            return "No relevant information found in document"

        context = context[:12000]

        prompt = f"""
You are a strict research assistant.

RULES:
- Use ONLY the context below.
- If the answer is not present, respond exactly:
  "Answer not found in document."
- Do NOT use outside knowledge.

Context:
{context}

Question:
{question}

Answer:
"""

        try:
            response = self.model.generate_content(prompt)
            return response.text

        except Exception as e:
            print("Gemini Error:", e)

            return """
⚠️ Gemini quota exceeded or API error.

Please wait and try again later,
or update your Gemini API key.
"""

    # =========================
    # STREAMING RESPONSE (CHATGPT STYLE)
    # =========================
    def generate_answer_stream(self, question, context):

        if not context or context.strip() == "":
            yield "No relevant information found in document"
            return

        context = context[:12000]

        prompt = f"""
You are a strict research assistant.

RULES:
- Use ONLY the context below.
- If answer is not found, respond exactly:
  "Answer not found in document."
- Do NOT use outside knowledge.

Context:
{context}

Question:
{question}

Answer:
"""

        try:
            response = self.model.generate_content(
                prompt,
                stream=True
            )

            for chunk in response:
                if hasattr(chunk, "text") and chunk.text:
                    yield chunk.text

        except Exception as e:
            print("Gemini Streaming Error:", e)

            yield """
⚠️ Gemini quota exceeded or API error.

Your document was uploaded successfully, but Gemini cannot answer right now.

Please wait a little and try again,
or replace your Gemini API key with a fresh one.
"""