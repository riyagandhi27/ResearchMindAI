import pdfplumber


class PDFProcessor:

    def extract_text(self, pdf_path):

        text = ""

        try:

            with pdfplumber.open(pdf_path) as pdf:

                for page in pdf.pages:

                    page_text = page.extract_text()

                    if page_text:
                        text += page_text + "\n"

        except Exception as e:

            print("PDF Error:", e)

        return text