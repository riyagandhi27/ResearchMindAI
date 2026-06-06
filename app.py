import os
import uuid

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    Response,
    stream_with_context
)

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
app.secret_key = os.getenv("SECRET_KEY", "researchmind-secret")

db.init_app(app)


# =========================
# RUNTIME FOLDERS
# =========================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
DATABASE_FOLDER = os.path.join(BASE_DIR, "database")
VECTOR_FOLDER = os.path.join(BASE_DIR, "vector_store")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DATABASE_FOLDER, exist_ok=True)
os.makedirs(VECTOR_FOLDER, exist_ok=True)


# =========================
# GLOBAL RAG INSTANCE
# =========================

rag_service = RAGService()


# =========================
# HELPERS
# =========================

def get_session_id():
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())

    return session["session_id"]


def reset_rag():
    rag_service.reset()


def set_active_document(doc):
    session["current_doc_id"] = str(doc.id)
    session["current_filename"] = doc.filename


def get_latest_document():
    return Document.query.order_by(Document.id.desc()).first()


def rebuild_rag_from_document(doc):
    reset_rag()

    rag_service.index_document(
        doc.content,
        doc_id=str(doc.id),
        source_name=doc.filename
    )


# =========================
# HOME ROUTE
# =========================

@app.route("/")
def index():

    get_session_id()

    latest_doc = get_latest_document()

    current_file = latest_doc.filename if latest_doc else None

    if latest_doc:
        set_active_document(latest_doc)

    return render_template(
        "index.html",
        current_file=current_file
    )


# =========================
# CLEAR CURRENT DOCUMENT
# =========================

@app.route("/clear_document", methods=["POST"])
def clear_document():

    reset_rag()

    session.pop("current_doc_id", None)
    session.pop("current_filename", None)

    return redirect(url_for("index"))


# =========================
# PDF UPLOAD
# =========================

@app.route("/upload_pdf", methods=["POST"])
def upload_pdf():

    print("[UPLOAD PDF] request.files keys:", list(request.files.keys()))
    print("[UPLOAD PDF] request.form keys:", list(request.form.keys()))

    file = (
        request.files.get("file")
        or request.files.get("pdf_file")
        or request.files.get("document")
    )

    if not file or file.filename == "":
        print("[UPLOAD PDF] No file received.")
        return "No file uploaded. Please choose a PDF file first.", 400

    filename = file.filename
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(file_path)

    pdf_processor = PDFProcessor()
    raw_text = pdf_processor.extract_text(file_path)

    cleaner = TextCleaner()
    clean_text = cleaner.clean(raw_text)

    if not clean_text or len(clean_text.strip()) < 10:
        return "No readable content found in PDF.", 400

    # Clear previous documents
    Document.query.delete()
    db.session.commit()

    # Clear FAISS memory
    reset_rag()

    new_doc = Document(
        filename=filename,
        filetype="pdf",
        source="pdf",
        content=clean_text
    )

    db.session.add(new_doc)
    db.session.commit()

    set_active_document(new_doc)
    rebuild_rag_from_document(new_doc)

    print(f"[UPLOAD PDF] Uploaded successfully: {filename} | doc_id={new_doc.id}")

    return redirect(url_for("index"))


# =========================
# CSV UPLOAD
# =========================

@app.route("/upload_csv", methods=["POST"])
def upload_csv():

    print("[UPLOAD CSV] request.files keys:", list(request.files.keys()))
    print("[UPLOAD CSV] request.form keys:", list(request.form.keys()))

    file = (
        request.files.get("file")
        or request.files.get("csv_file")
        or request.files.get("document")
    )

    if not file or file.filename == "":
        print("[UPLOAD CSV] No file received.")
        return "No file uploaded. Please choose a CSV file first.", 400

    filename = file.filename
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(file_path)

    import pandas as pd

    df = pd.read_csv(file_path)
    csv_text = df.to_string()

    cleaner = TextCleaner()
    clean_text = cleaner.clean(csv_text)

    if not clean_text or len(clean_text.strip()) < 10:
        return "CSV has no usable content.", 400

    # Clear previous documents
    Document.query.delete()
    db.session.commit()

    # Clear FAISS memory
    reset_rag()

    new_doc = Document(
        filename=filename,
        filetype="csv",
        source="csv",
        content=clean_text
    )

    db.session.add(new_doc)
    db.session.commit()

    set_active_document(new_doc)
    rebuild_rag_from_document(new_doc)

    print(f"[UPLOAD CSV] Uploaded successfully: {filename} | doc_id={new_doc.id}")

    return redirect(url_for("index"))


# =========================
# URL UPLOAD
# =========================

@app.route("/upload_url", methods=["POST"])
def upload_url():

    url = request.form.get("url")

    if not url or len(url.strip()) < 5:
        return "Invalid URL.", 400

    url = url.strip()

    scraper = WebScraper()
    raw_text = scraper.extract_text(url)

    if not raw_text:
        return "Failed to extract content from URL.", 400

    cleaner = TextCleaner()
    clean_text = cleaner.clean(raw_text)

    if not clean_text or len(clean_text.strip()) < 10:
        return "No readable web content found.", 400

    # Clear previous documents
    Document.query.delete()
    db.session.commit()

    # Clear FAISS memory
    reset_rag()
    
    new_doc = Document(
        filename=url,
        filetype="web",
        source="website",
        content=clean_text
    )

    db.session.add(new_doc)
    db.session.commit()

    set_active_document(new_doc)
    rebuild_rag_from_document(new_doc)

    print(f"[UPLOAD URL] Uploaded successfully: {url} | doc_id={new_doc.id}")

    return redirect(url_for("index"))


# =========================
# STREAM CHAT
# =========================

@app.route("/chat_stream", methods=["POST"])
def chat_stream():

    question = request.form.get("question")

    if not question or not question.strip():
        return "Question required.", 400

    doc = Document.query.first()

    if not doc:
        return "No document uploaded.", 400

    doc_id = str(doc.id)

    set_active_document(doc)
    rebuild_rag_from_document(doc)

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
                print("[APP] Chat history save error:", e)

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