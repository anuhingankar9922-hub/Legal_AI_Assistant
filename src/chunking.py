import re
from src.constants import CHUNK_SIZE_CHARS, CHUNK_OVERLAP_CHARS


def build_chunks_for_document(doc_name, pages):
    """Split each page into overlapping chunks, preferring to end on a sentence boundary."""
    chunks = []
    counter = 1
    for p in pages:
        text = re.sub(r"[ \t]+", " ", p["text"])
        start = 0
        while start < len(text):
            end = min(start + CHUNK_SIZE_CHARS, len(text))
            if end < len(text):
                cut = max(text.rfind(". ", start, end), text.rfind("\n", start, end), text.rfind("। ", start, end))
                if cut > start + CHUNK_SIZE_CHARS * 0.5:
                    end = cut + 1
            piece = text[start:end].strip()
            if piece:
                chunks.append({"chunk_id": f"{doc_name}-p{p['page_num']}-c{counter}", "doc_name": doc_name,
                               "page_num": p["page_num"], "raw_text": piece})
                counter += 1
            if end >= len(text):
                break
            start = max(end - CHUNK_OVERLAP_CHARS, start + 1)
    return chunks


def build_chunks_from_plain_text(doc_name, text):
    return build_chunks_for_document(doc_name, [{"page_num": 1, "text": text}])
