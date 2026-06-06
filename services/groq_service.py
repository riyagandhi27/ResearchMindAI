import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()


class GroqService:

    def __init__(self):

        api_key = os.getenv("GROQ_API_KEY")

        if not api_key:
            raise ValueError("GROQ_API_KEY not found")

        self.client = Groq(api_key=api_key)

        self.model = "llama-3.3-70b-versatile"

    def generate_answer(self, question, context):

        try:

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": context
                    }
                ],
                temperature=0.2
            )

            return response.choices[0].message.content

        except Exception as e:

            print("Groq Error:", e)

            return "Groq API Error"

    def generate_answer_stream(self, question, context):

        try:

            stream = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": context
                    }
                ],
                temperature=0.2,
                stream=True
            )

            for chunk in stream:

                if chunk.choices:

                    delta = chunk.choices[0].delta.content

                    if delta:
                        yield delta

        except Exception as e:

            print("Groq Streaming Error:", e)

            yield "⚠️ Groq API Error"