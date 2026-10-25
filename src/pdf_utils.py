from pypdf import PdfReader


def extract_pages_from_pdf(uploaded_file):
    """Return [{'page_num', 'text'}] for every page that has readable text."""
    pages = []
    try:
        reader = PdfReader(uploaded_file)
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception:
                return []
        for idx, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            if text.strip():
                pages.append({"page_num": idx + 1, "text": text.strip()})
    except Exception as e:  # corrupt / unreadable file
        print(f"Error reading PDF: {e}")
    return pages
