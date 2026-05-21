import io
import pdfplumber
import fitz  # pymupdf


def parse_pdf(file_bytes: bytes) -> str:
    text = _extract_pdfplumber(file_bytes)
    if len(text.strip()) < 100:
        text = _extract_pymupdf(file_bytes)
    return text


def _extract_pdfplumber(file_bytes: bytes) -> str:
    lines = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text(x_tolerance=2, y_tolerance=2)
            if page_text:
                lines.append(page_text)
    return "\n".join(lines)


def _extract_pymupdf(file_bytes: bytes) -> str:
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    pages = [doc[i].get_text() for i in range(len(doc))]
    doc.close()
    return "\n".join(pages)


def extract_pdf_links(file_bytes: bytes) -> list[str]:
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    urls = []
    for page in doc:
        for link in page.get_links():
            uri = link.get("uri", "")
            if uri.startswith("http"):
                urls.append(uri)
    doc.close()
    return urls
