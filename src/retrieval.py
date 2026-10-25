"""Retrieval: matches a user question to (a) the built-in Indian-law topics and
(b) the user's uploaded documents. Pure scikit-learn TF-IDF, works offline and
handles English, Hindi and Marathi text."""
import re
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.constants import TOPIC_THRESHOLD, DOC_THRESHOLD, TOP_K
from src.knowledge_base import TOPICS, COMPLIANCE


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").lower()).strip()


def _words(s: str):
    return set(re.findall(r"[\wऀ-ॿ]{3,}", _norm(s)))


class TopicIndex:
    """Ranks knowledge-base topics for a question in any supported language."""

    def __init__(self):
        self.topics = list(TOPICS) + [dict(c, kind="compliance") for c in COMPLIANCE]
        docs = []
        self.kw_sets = []
        for t in self.topics:
            titles = " ".join(t["title"].values())
            kws = t["keywords"]
            acts = " ".join(t.get("acts", []))
            docs.append(f"{kws} {kws} {titles} {acts}")
            self.kw_sets.append(_words(kws) | _words(titles))
        self.word_vec = TfidfVectorizer(analyzer="word", token_pattern=r"[\wऀ-ॿ]{2,}", sublinear_tf=True)
        self.char_vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True)
        self.wm = self.word_vec.fit_transform(docs)
        self.cm = self.char_vec.fit_transform(docs)

    def rank(self, query: str, k: int = 3):
        q = _norm(query)
        if not q:
            return []
        w = cosine_similarity(self.word_vec.transform([q]), self.wm).ravel()
        c = cosine_similarity(self.char_vec.transform([q]), self.cm).ravel()
        qw = _words(q)
        overlap = np.array([len(qw & ks) for ks in self.kw_sets], dtype=float)
        score = 0.55 * w + 0.25 * c + 0.12 * np.minimum(overlap, 3)
        order = np.argsort(-score)[:k]
        return [(self.topics[i], float(score[i])) for i in order if score[i] >= TOPIC_THRESHOLD]


class DocumentIndex:
    """Chunk index over uploaded documents; rebuilt automatically on change."""

    def __init__(self):
        self.chunks = []
        self.texts = {}          # doc_name -> full text
        self.word_vec = None
        self.char_vec = None
        self.wm = None
        self.cm = None

    # -- bookkeeping
    def has_chunks(self):
        return bool(self.chunks)

    def num_chunks(self):
        return len(self.chunks)

    def doc_names(self):
        return list(self.texts.keys())

    def num_docs(self):
        return len(self.texts)

    def has_doc(self, name):
        return name in self.texts

    def clear(self):
        self.__init__()

    def remove(self, name):
        self.texts.pop(name, None)
        self.chunks = [c for c in self.chunks if c["doc_name"] != name]
        self._build()

    def add_document(self, name, full_text, chunks):
        self.texts[name] = full_text
        self.chunks = [c for c in self.chunks if c["doc_name"] != name] + chunks
        self._build()

    # -- indexing / search
    def _build(self):
        if not self.chunks:
            self.word_vec = self.char_vec = self.wm = self.cm = None
            return
        corpus = [_norm(c["raw_text"]) for c in self.chunks]
        self.word_vec = TfidfVectorizer(analyzer="word", token_pattern=r"[\wऀ-ॿ]{2,}",
                                        ngram_range=(1, 2), sublinear_tf=True)
        self.char_vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True)
        self.wm = self.word_vec.fit_transform(corpus)
        self.cm = self.char_vec.fit_transform(corpus)

    def search(self, query, doc_name=None, k=TOP_K):
        if not self.chunks or self.wm is None:
            return []
        q = _norm(query)
        w = cosine_similarity(self.word_vec.transform([q]), self.wm).ravel()
        c = cosine_similarity(self.char_vec.transform([q]), self.cm).ravel()
        score = 0.6 * w + 0.4 * c
        if doc_name and doc_name != "__all__":
            mask = np.array([ch["doc_name"] == doc_name for ch in self.chunks])
            score = np.where(mask, score, -1)
        order = np.argsort(-score)[:k]
        out = [(self.chunks[i], float(score[i])) for i in order if score[i] >= DOC_THRESHOLD]
        if out:   # drop weak extras that are far below the best hit
            out = [h for h in out if h[1] >= 0.5 * out[0][1]]
        return out


def best_sentences(chunk_text, query, n=2):
    """Pick the n sentences of a chunk most related to the query."""
    sents = [s.strip() for s in re.split(r"(?<=[.!?।])\s+", re.sub(r"\s+", " ", chunk_text)) if len(s.strip()) > 20]
    if not sents:
        return [chunk_text[:300]]
    qw = _words(query)
    ranked = sorted(sents, key=lambda s: -len(_words(s) & qw))
    chosen = ranked[:n]
    return [s for s in sents if s in chosen]
