from .pdf_parser import parse_pdf, extract_pdf_links


async def parse_file(file_bytes: bytes, file_type: str) -> dict:
    file_type = file_type.lower().strip(".")

    if file_type == "pdf":
        raw_text = parse_pdf(file_bytes)
        embedded_links = extract_pdf_links(file_bytes)
        return {"source_type": "pdf", "raw_text": raw_text, "embedded_links": embedded_links}

    raise ValueError(f"Unsupported file type: {file_type}")
