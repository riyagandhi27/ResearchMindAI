import os
import uuid

from flask import Flask, render_template, request, redirect, url_for, session, Response, stream_with_context

from config import Config
from extensions import db

from models import Document, ChatHistory

from services.pdf_service import PDFProcessor
from services.web_scraper import WebScraper
from services.text_cleaner import TextCleaner
from services.rag_service import RAGService


# =========================
# APP INITIALIZATION
# =========================

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = "super-secret-key"

db.init_app(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
DATABASE_FOLDER = os.path.join(BASE_DIR, "database")
VECTOR_FOLDER = os.path.join(BASE_DIR, "vector_store")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DATABASE_FOLDER, exist_ok=True)
os.makedirs(VECTOR_FOLDER, exist_ok=True)
DATABASE_FOLDER = "database"
os.makedirs(DATABASE_FOLDER, exist_ok=True)

VECTOR_FOLDER = "vector_store"
os.makedirs(VECTOR_FOLDER, exist_ok=True)

# =========================
# GLOBAL RAG INSTANCE
# =========================

rag_service = RAGService()


def get_session_id():
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())

    return session["session_id"]


# =========================
# HOME ROUTE
# =========================

@app.route("/")
def index():

    get_session_id()

    current_file = session.get("current_filename")

    return render_template(
        "index.html",
        current_file=current_file
    )


# =========================
# RESET RAG
# =========================

def reset_rag():
    rag_service.reset()
    session.pop("current_doc_id", None)


# =========================
# CLEAR CURRENT DOCUMENT
# =========================

@app.route("/clear_document", methods=["POST"])
def clear_document():

    reset_rag()

    session.pop("current_filename", None)

    return redirect(url_for("index"))


# =========================
# PDF UPLOAD
# =========================

@app.route("/upload_pdf", methods=["POST"])
def upload_pdf():

    file = request.files.get("file")

    if not file:
        return "No file uploaded", 400

    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)

    pdf_processor = PDFProcessor()
    raw_text = pdf_processor.extract_text(file_path)

    cleaner = TextCleaner()
    clean_text = cleaner.clean(raw_text)

    if not clean_text or len(clean_text.strip()) < 10:
        return "No readable content", 400

    new_doc = Document(
        filename=file.filename,
        filetype="pdf",
        source="pdf",
        content=clean_text
    )

    db.session.add(new_doc)
    db.session.commit()

    reset_rag()

    doc_id = str(new_doc.id)

    rag_service.index_document(
        clean_text,
        doc_id=doc_id,
        source_name=file.filename
    )

    session["current_doc_id"] = doc_id
    session["current_filename"] = file.filename

    return redirect(url_for("index"))


# =========================
# CSV UPLOAD
# =========================

@app.route("/upload_csv", methods=["POST"])
def upload_csv():

    file = request.files.get("file")

    if not file:
        return "No file uploaded", 400

    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)

    import pandas as pd

    df = pd.read_csv(file_path)
    csv_text = df.to_string()

    cleaner = TextCleaner()
    clean_text = cleaner.clean(csv_text)

    if not clean_text or len(clean_text.strip()) < 10:
        return "CSV has no usable content", 400

    new_doc = Document(
        filename=file.filename,
        filetype="csv",
        source="csv",
        content=clean_text
    )

    db.session.add(new_doc)
    db.session.commit()

    reset_rag()

    doc_id = str(new_doc.id)

    rag_service.index_document(
        clean_text,
        doc_id=doc_id,
        source_name=file.filename
    )

    session["current_doc_id"] = doc_id
    session["current_filename"] = file.filename

    return redirect(url_for("index"))


# =========================
# URL UPLOAD
# =========================

@app.route("/upload_url", methods=["POST"])
def upload_url():

    url = request.form.get("url")

    if not url or len(url.strip()) < 5:
        return "Invalid URL", 400

    scraper = WebScraper()
    raw_text = scraper.extract_text(url)

    if not raw_text:
        return "Failed to extract content", 400

    cleaner = TextCleaner()
    clean_text = cleaner.clean(raw_text)

    if not clean_text or len(clean_text.strip()) < 10:
        return "No readable web content", 400

    new_doc = Document(
        filename=url,
        filetype="web",
        source="website",
        content=clean_text
    )

    db.session.add(new_doc)
    db.session.commit()

    reset_rag()

    doc_id = str(new_doc.id)

    rag_service.index_document(
        clean_text,
        doc_id=doc_id,
        source_name=url
    )

    session["current_doc_id"] = doc_id
    session["current_filename"] = url

    return redirect(url_for("index"))


# =========================
# STREAM CHAT
# =========================

@app.route("/chat_stream", methods=["POST"])
def chat_stream():

    question = request.form.get("question")

    if not question:
        return "Question required", 400

    get_session_id()

    doc_id = session.get("current_doc_id")

    if not doc_id:
        return "No document uploaded", 400

    def generate():

        answer_chunks = []

        stream = rag_service.ask_question_stream(
            question,
            doc_id=doc_id
        )

        for chunk in stream:
            answer_chunks.append(chunk)
            yield chunk

        full_answer = "".join(answer_chunks)

        if full_answer.strip():

            try:
                chat = ChatHistory(
                    question=question,
                    answer=full_answer
                )

                db.session.add(chat)
                db.session.commit()

            except Exception as e:
                print("Chat history save error:", e)

    return Response(
        stream_with_context(generate()),
        mimetype="text/plain"
    )


# =========================
# DB INIT
# =========================

with app.app_context():
    db.create_all()


# =========================
# RUN APP
# =========================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7860)