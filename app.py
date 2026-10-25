"""LegalEase India - multilingual legal information assistant (Streamlit).

Run:  streamlit run app.py
"""
import html as _html
import os
import re
from datetime import datetime

import streamlit as st

from src.analyzer import analyze
from src.chunking import build_chunks_for_document
from src.constants import (APP_TITLE, BORDER, GREEN, INK, LANGS, LIGHT_BG, MAX_UPLOAD_MB, MUTED, NAVY, NAVY_2,
                           SAFFRON, WHITE)
from src.knowledge_base import COMPLIANCE, TOPICS, TOPIC_BY_ID
from src.lawyer_directory import filter_lawyers, get_unique, load_lawyers
from src.pdf_utils import extract_pages_from_pdf
from src.retrieval import DocumentIndex, TopicIndex, best_sentences
from src.sos_data import EMERGENCY_NUMBERS, get_localized_numbers
from src.ui_text import ABOUT_FEATURES, ABOUT_HOW, EXAMPLES, T

BASE = os.path.dirname(os.path.abspath(__file__))
esc = _html.escape

st.set_page_config(page_title="LegalEase India", page_icon="⚖️", layout="wide", initial_sidebar_state="collapsed")


def H(s: str):
    """Render an HTML snippet (newlines collapsed so markdown never sees code blocks)."""
    st.markdown(re.sub(r"\s*\n\s*", " ", s).strip(), unsafe_allow_html=True)


# --------------------------------------------------------------------------- styling
CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Noto+Sans+Devanagari:wght@400;500;600;700&display=swap');
:root {{ --navy:{NAVY}; --navy2:{NAVY_2}; --saffron:{SAFFRON}; --green:{GREEN}; --ink:{INK}; --muted:{MUTED}; --border:{BORDER}; --bg:{LIGHT_BG}; }}
html, body, .stApp, .stMarkdown, p, li, label, input, textarea, button, [data-baseweb="select"] {{ font-family: 'Inter','Noto Sans Devanagari','Segoe UI',system-ui,sans-serif; }}
[data-testid="stIconMaterial"], .material-icons, [class*="material-symbols"] {{ font-family: 'Material Symbols Rounded' !important; }}
.stApp {{ background: var(--bg); color: var(--ink); }}
#MainMenu, footer, [data-testid="stToolbar"], [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"], [data-testid="stDecoration"] {{ display:none !important; }}
header[data-testid="stHeader"], [data-testid="stHeader"] {{ display:none !important; }}
.block-container {{ max-width: 1180px; padding-top: 1.1rem; padding-bottom: 3rem; }}

/* top brand bar */
.brandbar {{ display:flex; align-items:center; gap:12px; padding: 4px 0 2px; }}
.logo {{ width:42px; height:42px; border-radius:12px; background: linear-gradient(135deg,var(--navy),var(--navy2)); display:flex; align-items:center; justify-content:center; font-size:22px; box-shadow:0 4px 12px rgba(11,31,59,.25); }}
.brandname {{ font-size:22px; font-weight:800; color:var(--navy); letter-spacing:-.3px; line-height:1; }}
.brandname span {{ color: var(--saffron); }}
.brandtag {{ font-size:12px; color:var(--muted); margin-top:3px; }}

/* hero */
.hero {{ position:relative; overflow:hidden; border-radius:20px; padding:30px 34px 28px; margin: 10px 0 14px; color:#fff;
  background: radial-gradient(900px 300px at 85% -20%, rgba(255,153,51,.35), transparent 60%), linear-gradient(135deg, var(--navy) 0%, var(--navy2) 100%);
  box-shadow: 0 10px 30px rgba(11,31,59,.18); }}
.hero:before {{ content:""; position:absolute; left:0; right:0; top:0; height:5px; background: linear-gradient(90deg, var(--saffron) 33%, #fff 33% 66%, var(--green) 66%); }}
.hero h1 {{ font-size: 32px; line-height:1.2; font-weight:800; margin:6px 0 10px; color:#fff; letter-spacing:-.5px; padding:0; }}
.hero p {{ font-size:15.5px; line-height:1.6; color:#D6E0F0; max-width:760px; margin:0; }}
.hero .pill {{ display:inline-block; font-size:12px; font-weight:600; padding:4px 12px; border-radius:999px; background:rgba(255,255,255,.12); border:1px solid rgba(255,255,255,.22); color:#fff; margin: 14px 8px 0 0; }}

/* disclaimer */
.disclaimer {{ display:flex; gap:12px; background:#FFF6E8; border:1px solid #FFE0B8; border-left:5px solid var(--saffron); border-radius:12px; padding:11px 16px; font-size:13px; color:#5A3B0C; margin-bottom:10px; line-height:1.55; }}
.disclaimer b {{ color:#7A4300; }}

/* tabs */
.stTabs [data-baseweb="tab-list"] {{ gap:4px; border-bottom:1px solid var(--border); flex-wrap:wrap; }}
.stTabs [data-baseweb="tab"] {{ height:46px; padding: 0 14px; border-radius:10px 10px 0 0; font-weight:600; color:var(--muted); background:transparent; }}
.stTabs [data-baseweb="tab"] p {{ font-size:14.5px; font-weight:600; }}
.stTabs [aria-selected="true"] {{ color:var(--navy); }}
.stTabs [aria-selected="true"] p {{ color:var(--navy); }}
.stTabs [data-baseweb="tab-highlight"] {{ background-color: var(--saffron); height:3px; }}
.stTabs [data-baseweb="tab-border"] {{ display:none; }}

/* section headings */
.sec-title {{ font-size:22px; font-weight:800; color:var(--navy); margin: 10px 0 2px; letter-spacing:-.3px; }}
.sec-sub {{ font-size:14px; color:var(--muted); margin-bottom:14px; line-height:1.55; }}
.h5 {{ font-size:12px; font-weight:700; letter-spacing:.9px; text-transform:uppercase; color:var(--muted); margin: 14px 0 6px; }}

/* cards */
.card {{ background:#fff; border:1px solid var(--border); border-radius:16px; padding:18px 20px; box-shadow:0 1px 2px rgba(16,24,40,.04), 0 4px 14px rgba(16,24,40,.04); }}
.card + .card {{ margin-top: 12px; }}
.ans-head {{ display:flex; align-items:center; gap:10px; font-size:18px; font-weight:700; color:var(--navy); }}
.ans-ico {{ width:38px; height:38px; border-radius:11px; background:#FFF1DE; display:flex; align-items:center; justify-content:center; font-size:20px; flex:none; }}
.chip {{ display:inline-block; font-size:12px; font-weight:600; padding:4px 10px; border-radius:999px; background:#EAF0FB; color:var(--navy2); border:1px solid #D5E1F5; margin:3px 6px 3px 0; }}
.chip.g {{ background:#E8F5E9; color:#1B5E20; border-color:#C8E6C9; }}
.ans-simple {{ font-size:15px; line-height:1.65; color:var(--ink); background:#F7F9FD; border-radius:12px; padding:12px 14px; border:1px solid var(--border); }}
ol.steps {{ margin:4px 0 0; padding:0; list-style:none; counter-reset: s; }}
ol.steps li {{ counter-increment: s; position:relative; padding: 4px 0 10px 40px; font-size:14.5px; line-height:1.6; }}
ol.steps li:before {{ content: counter(s); position:absolute; left:0; top:2px; width:28px; height:28px; border-radius:50%; background:var(--navy); color:#fff; font-weight:700; font-size:13px; display:flex; align-items:center; justify-content:center; }}
ol.steps li:not(:last-child):after {{ content:""; position:absolute; left:13.5px; top:32px; bottom:0; width:1px; background:var(--border); }}
.two {{ display:grid; grid-template-columns: 1fr 1fr; gap:14px; }}
@media (max-width: 760px) {{ .two {{ grid-template-columns: 1fr; }} .hero h1 {{ font-size:25px; }} .hero {{ padding:24px 20px; }} }}
.mini {{ background:#F7F9FD; border:1px solid var(--border); border-radius:12px; padding:10px 14px; font-size:14px; line-height:1.55; }}
.mini ul {{ margin:0; padding-left:18px; }}
.doc-hit {{ border:1px solid #CFE3FF; background:#F3F8FF; border-radius:12px; padding:12px 14px; margin-top:10px; }}
.doc-hit-h {{ font-size:12.5px; font-weight:700; color:var(--navy2); margin-bottom:6px; }}
.doc-hit-b {{ font-size:14.5px; line-height:1.65; }}
.doc-hit-b mark {{ background:#FFE9BF; padding:1px 3px; border-radius:4px; }}
.doc-hit-x {{ font-size:12.5px; color:var(--muted); margin-top:8px; line-height:1.55; border-top:1px dashed #CFE3FF; padding-top:8px; }}
.helpline {{ margin-top:12px; font-size:13px; font-weight:600; color:#1B5E20; background:#E8F5E9; border-radius:10px; padding:8px 12px; display:inline-block; }}
.empty {{ text-align:center; padding:26px 16px; color:var(--muted); font-size:14.5px; line-height:1.6; }}
.empty .big {{ font-size:40px; margin-bottom:6px; }}

/* risk + stats */
.risk {{ display:flex; align-items:center; gap:14px; border-radius:14px; padding:14px 18px; font-weight:600; border:1px solid; }}
.risk.high {{ background:#FDECEC; border-color:#F5C2C2; color:#8A1C1C; }}
.risk.medium {{ background:#FFF4E0; border-color:#FFD99A; color:#7A4A00; }}
.risk.low {{ background:#E8F5E9; border-color:#B9DFBC; color:#1B5E20; }}
.risk .dot {{ width:14px; height:14px; border-radius:50%; flex:none; }}
.risk.high .dot {{ background:#D32F2F; }} .risk.medium .dot {{ background:#F59E0B; }} .risk.low .dot {{ background:#2E7D32; }}
.risk small {{ display:block; font-weight:500; opacity:.85; font-size:12.5px; }}
.stat {{ background:#fff; border:1px solid var(--border); border-radius:14px; padding:12px 16px; }}
.stat b {{ display:block; font-size:24px; color:var(--navy); font-weight:800; line-height:1.1; }}
.stat span {{ font-size:12px; color:var(--muted); font-weight:600; letter-spacing:.3px; }}
.flag {{ border:1px solid var(--border); border-left-width:5px; border-radius:12px; padding:11px 14px; margin-bottom:10px; background:#fff; }}
.flag.high {{ border-left-color:#D32F2F; }} .flag.medium {{ border-left-color:#F59E0B; }} .flag.low {{ border-left-color:#3B82F6; }}
.sev {{ font-size:10.5px; font-weight:800; letter-spacing:.8px; padding:2px 8px; border-radius:6px; margin-right:8px; color:#fff; }}
.sev.high {{ background:#D32F2F; }} .sev.medium {{ background:#F59E0B; }} .sev.low {{ background:#3B82F6; }}
.flag .q {{ font-size:12.5px; color:var(--muted); margin-top:6px; font-style:italic; line-height:1.5; }}
.kv b {{ color:var(--navy); }}
.jg {{ display:grid; grid-template-columns: 210px 1fr; gap:6px 14px; font-size:14px; }}
.jg .t {{ font-weight:700; color:var(--navy); }}
@media (max-width: 760px) {{ .jg {{ grid-template-columns: 1fr; }} }}

/* lawyers */
.lawyer {{ display:flex; gap:14px; align-items:flex-start; }}
.avatar {{ width:52px; height:52px; border-radius:50%; flex:none; display:flex; align-items:center; justify-content:center; color:#fff; font-weight:800; font-size:18px; background: linear-gradient(135deg,var(--navy),#2B5BA8); }}
.lname {{ font-size:16px; font-weight:700; color:var(--navy); }}
.lmeta {{ font-size:13px; color:var(--muted); margin:2px 0 6px; }}
.callbtn {{ display:inline-block; text-decoration:none !important; background:var(--saffron); color:var(--navy) !important; font-weight:700; font-size:13px; padding:7px 14px; border-radius:9px; margin-top:8px; }}
.callbtn:hover {{ filter:brightness(.95); }}

/* sos */
.sosbanner {{ background:linear-gradient(135deg,#B71C1C,#E53935); color:#fff; border-radius:16px; padding:16px 20px; font-size:18px; font-weight:700; display:flex; gap:12px; align-items:center; box-shadow:0 8px 20px rgba(183,28,28,.25); }}
.sosgrid {{ display:grid; grid-template-columns: repeat(auto-fill, minmax(250px,1fr)); gap:12px; margin-top:14px; }}
.sos {{ display:flex; gap:12px; align-items:center; background:#fff; border:1px solid var(--border); border-radius:14px; padding:12px 14px; text-decoration:none !important; color:inherit !important; transition: all .15s; }}
.sos:hover {{ border-color:#E53935; box-shadow:0 6px 16px rgba(229,57,53,.15); transform: translateY(-1px); }}
.sos.prio {{ border:2px solid #E53935; background:#FFF5F5; }}
.sos .ico {{ font-size:26px; width:44px; height:44px; border-radius:12px; background:#F3F6FB; display:flex; align-items:center; justify-content:center; flex:none; }}
.sos .nm {{ font-weight:700; color:var(--navy); font-size:14.5px; line-height:1.25; }}
.sos .ds {{ font-size:12px; color:var(--muted); margin-top:2px; line-height:1.35; }}
.sos .num {{ margin-left:auto; background:#D32F2F; color:#fff; font-weight:800; font-size:15px; padding:6px 12px; border-radius:999px; flex:none; }}

/* streamlit widgets */
[data-testid="stBaseButton-primary"], button[kind="primary"] {{ background:var(--saffron) !important; color:var(--navy) !important; border:none !important; font-weight:700 !important; }}
[data-testid="stBaseButton-primary"]:hover {{ filter:brightness(.95); }}
[data-testid="stBaseButton-secondary"], button[kind="secondary"] {{ border-radius:10px; border:1px solid var(--border); background:#fff; color:var(--navy); font-weight:600; }}
[data-testid="stBaseButton-secondary"]:hover {{ border-color:var(--saffron); color:var(--navy); background:#FFF8EE; }}
.stButton > button, .stDownloadButton > button {{ border-radius:10px; }}
[data-testid="stFileUploaderDropzone"] {{ background:#FBFCFE; border:2px dashed #C9D4E5; border-radius:14px; }}
[data-testid="stFileUploaderDropzone"] button {{ background:#fff; color:var(--navy); border:1px solid var(--border); }}
[data-testid="stChatInput"] {{ border-radius:14px; border:1.5px solid #C9D4E5; background:#fff; }}
[data-testid="stChatMessage"] {{ background:transparent; padding: 6px 0; }}
[data-testid="stExpander"] {{ background:#fff; border:1px solid var(--border) !important; border-radius:14px !important; }}
[data-testid="stExpander"] summary p {{ font-weight:700; color:var(--navy); font-size:15px; }}
[data-testid="stSegmentedControl"] button, [data-testid="stBaseButton-segmented_control"] {{ font-weight:700; }}
div[data-baseweb="select"] > div {{ background:#fff; border-radius:10px; color:var(--ink); }}
div[data-baseweb="select"] * {{ color: var(--ink); }}
input, textarea {{ color: var(--ink) !important; }}
[data-testid="stVerticalBlockBorderWrapper"] {{ border-radius:16px; }}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# --------------------------------------------------------------------------- cached resources
@st.cache_resource(show_spinner=False)
def get_topic_index():
    return TopicIndex()


@st.cache_data(show_spinner=False)
def get_lawyers():
    return load_lawyers(os.path.join(BASE, "data", "lawyers.json"))


topic_index = get_topic_index()

# --------------------------------------------------------------------------- state
ss = st.session_state
ss.setdefault("lang", "en")
ss.setdefault("doc_index", DocumentIndex())
ss.setdefault("analyses", {})
ss.setdefault("chat", [])
ss.setdefault("uploader_ver", 0)
ss.setdefault("feedback", {})
ss.setdefault("flash", None)


def tx(d):
    """Pick the current-language value from a {en,hi,mr} dict."""
    return d.get(ss.lang) or d.get("en", "")


# --------------------------------------------------------------------------- top bar + language
top_l, top_r = st.columns([3, 2], vertical_alignment="center")
with top_l:
    H(f"""<div class="brandbar"><div class="logo">⚖️</div>
    <div><div class="brandname">Legal<span>Ease</span> India</div>
    <div class="brandtag">{esc(T(ss.lang, 'language'))}: English · हिंदी · मराठी</div></div></div>""")
with top_r:
    picked = st.segmented_control("Language / भाषा", options=list(LANGS.keys()), format_func=LANGS.get,
                                 default=ss.lang, selection_mode="single", key="lang_picker",
                                 label_visibility="collapsed")
    if picked and picked != ss.lang:   # a click on the active option returns None - keep current language
        ss.lang = picked
        st.rerun()

lang = ss.lang

H(f"""<div class="hero"><h1>{esc(T(lang, 'hero_title'))}</h1><p>{esc(T(lang, 'hero_sub'))}</p>
<span class="pill">📚 {len(TOPICS)} {esc(T(lang, 'metric_topics'))}</span>
<span class="pill">🌐 3 {esc(T(lang, 'metric_langs'))}</span>
<span class="pill">🆘 {len(EMERGENCY_NUMBERS)} {esc(T(lang, 'metric_helplines'))}</span></div>""")
H(f"""<div class="disclaimer"><div>⚠️</div><div><b>{esc(T(lang, 'disclaimer_title'))}.</b> {esc(T(lang, 'disclaimer_text'))}</div></div>""")


# --------------------------------------------------------------------------- helpers: rendering
def topic_card_html(t, compact=False):
    """Full guide for one knowledge-base topic, in the current language."""
    title = tx(t["title"])
    acts = "".join(f'<span class="chip">{esc(a)}</span>' for a in t["acts"])
    steps = "".join(f"<li>{esc(s)}</li>" for s in tx(t["steps"]))
    docs = "".join(f"<li>{esc(d)}</li>" for d in tx(t["docs"]))
    head = "" if compact else f'<div class="ans-head"><div class="ans-ico">{t["icon"]}</div>{esc(title)}</div>'
    return f"""<div class="card">{head}
    <div class="h5">{esc(T(lang, 'ans_acts'))}</div><div>{acts}</div>
    <div class="h5">{esc(T(lang, 'ans_simple'))}</div><div class="ans-simple">{esc(tx(t['summary']))}</div>
    <div class="h5">{esc(T(lang, 'ans_steps'))}</div><ol class="steps">{steps}</ol>
    <div class="two"><div><div class="h5">{esc(T(lang, 'ans_where'))}</div><div class="mini">📍 {esc(tx(t['where']))}</div></div>
    <div><div class="h5">{esc(T(lang, 'ans_docs'))}</div><div class="mini"><ul>{docs}</ul></div></div></div>
    <div class="helpline">☎ {esc(T(lang, 'ans_helpline'))}</div></div>"""


def compliance_card_html(c, compact=False):
    steps = "".join(f"<li>{esc(s)}</li>" for s in tx(c["steps"]))
    head = "" if compact else f'<div class="ans-head"><div class="ans-ico">{c["icon"]}</div>{esc(tx(c["title"]))}</div>'
    return f"""<div class="card">{head}
    <div class="h5">{esc(T(lang, 'svc_who'))}</div><div class="ans-simple">{esc(tx(c['who']))}</div>
    <div class="h5">{esc(T(lang, 'svc_steps'))}</div><ol class="steps">{steps}</ol>
    <div class="mini">💡 {esc(tx(c['note']))}</div>
    <a class="callbtn" href="{esc(c['link'])}" target="_blank" rel="noopener">{esc(T(lang, 'svc_open'))} ↗</a></div>"""


def strength(score):
    labels = {"en": ("Strong match", "Good match", "Possible match"), "hi": ("मज़बूत मेल", "अच्छा मेल", "संभावित मेल"),
              "mr": ("मजबूत जुळणी", "चांगली जुळणी", "संभाव्य जुळणी")}[lang]
    return labels[0] if score >= 0.35 else labels[1] if score >= 0.2 else labels[2]


def doc_hit_html(hit):
    chunk, score, sents, query = hit["chunk"], hit["score"], hit["sents"], hit["query"]
    raw = re.sub(r"\s+", " ", chunk["raw_text"])
    pos = raw.find(sents[0]) if sents else -1
    if len(raw) > 620 and pos >= 0:      # show a window around the best sentence
        a = max(0, pos - 160)
        b = min(len(raw), a + 620)
        raw = ("…" if a else "") + raw[a:b] + ("…" if b < len(raw) else "")
    body = esc(raw)
    for s in sents:
        body = body.replace(esc(s), f"<mark>{esc(s)}</mark>", 1)
    short = body
    return f"""<div class="doc-hit"><div class="doc-hit-h">📄 {esc(chunk['doc_name'])} · {esc(T(lang, 'ans_page'))} {chunk['page_num']} · {esc(strength(score))}</div>
    <div class="doc-hit-b">{short}</div></div>"""


def run_query(q, scope):
    """Build a language-independent answer record (rendered later in the active language)."""
    rec = {"role": "assistant", "q": q, "topics": [], "doc_hits": []}
    if scope != "__kb__":
        didx = ss.doc_index
        if didx.has_chunks():
            hits = didx.search(q, None if scope == "__all__" else scope, k=2)
            for chunk, score in hits:
                rec["doc_hits"].append({"chunk": chunk, "score": score, "sents": best_sentences(chunk["raw_text"], q, 2), "query": q})
    if scope in ("__kb__", "__all__"):
        ranked = topic_index.rank(q, k=3)
        if ranked:
            top = ranked[0][1]
            rec["topics"] = [(t["id"], t.get("kind", "law"), s) for t, s in ranked if s >= 0.55 * top]
    return rec


def render_answer(rec, idx):
    if not rec["topics"] and not rec["doc_hits"]:
        H(f"""<div class="card"><div class="ans-simple">🤔 {esc(T(lang, 'ans_none'))}</div></div>""")
        return
    if rec["doc_hits"]:
        H(f'<div class="h5">📄 {esc(T(lang, "ans_doc_found"))}</div>')
        for hit in rec["doc_hits"]:
            H(doc_hit_html(hit))
    if rec["topics"]:
        tid, kind, score = rec["topics"][0]
        t = next(c for c in COMPLIANCE if c["id"] == tid) if kind == "compliance" else TOPIC_BY_ID[tid]
        H(compliance_card_html(t) if kind == "compliance" else topic_card_html(t))
        if len(rec["topics"]) > 1:
            names = []
            for tid2, kind2, _ in rec["topics"][1:]:
                t2 = next(c for c in COMPLIANCE if c["id"] == tid2) if kind2 == "compliance" else TOPIC_BY_ID[tid2]
                names.append(f'<span class="chip">{t2["icon"]} {esc(tx(t2["title"]))}</span>')
            H(f'<div class="h5">{esc(T(lang, "ans_also"))}</div>' + "".join(names))
    c1, c2, c3, _sp = st.columns([1.3, 0.35, 0.35, 4])
    fb = ss.feedback.get(idx)
    if fb:
        c1.caption(f"✅ {T(lang, 'feedback_thanks')}")
    else:
        c1.caption(T(lang, "feedback_q"))
        if c2.button("👍", key=f"up_{idx}"):
            ss.feedback[idx] = "up"
            st.rerun()
        if c3.button("👎", key=f"dn_{idx}"):
            ss.feedback[idx] = "down"
            st.rerun()


def chat_transcript():
    lines = [f"{APP_TITLE} - chat export ({datetime.now():%d %b %Y %H:%M})", ""]
    for m in ss.chat:
        if m["role"] == "user":
            lines.append(f"Q: {m['content']}")
        else:
            for tid, kind, _ in m["topics"][:1]:
                t = next(c for c in COMPLIANCE if c["id"] == tid) if kind == "compliance" else TOPIC_BY_ID[tid]
                lines.append(f"A: {tx(t['title'])}")
                if kind != "compliance":
                    lines.append("   Laws: " + "; ".join(t["acts"]))
                    lines += [f"   {i}. {s}" for i, s in enumerate(tx(t["steps"]), 1)]
            for h in m["doc_hits"]:
                lines.append(f"   From {h['chunk']['doc_name']} p.{h['chunk']['page_num']}: " + " ".join(h["sents"]))
            if not m["topics"] and not m["doc_hits"]:
                lines.append("A: (no match found)")
            lines.append("")
    lines.append("Not legal advice. General information only.")
    return "\n".join(lines)


def add_document(name, pages):
    full = "\n\n".join(p["text"] for p in pages)
    chunks = build_chunks_for_document(name, pages)
    ss.doc_index.add_document(name, full, chunks)
    ss.analyses[name] = analyze(full)
    ss.active_doc = name


def pick_example(q):
    ss.pending_q = q


# --------------------------------------------------------------------------- tabs
tabs = st.tabs([T(lang, k) for k in ("nav_chat", "nav_docs", "nav_rights", "nav_services", "nav_lawyer", "nav_sos", "nav_about")])
tab_chat, tab_docs, tab_rights, tab_svc, tab_law, tab_sos, tab_about = tabs

# ============================== CHAT ==============================
with tab_chat:
    H(f'<div class="sec-title">{esc(T(lang, "chat_title"))}</div>')
    scope = "__kb__" if not ss.doc_index.has_chunks() else "__all__"
    if ss.doc_index.has_chunks():
        opts = ["__all__", "__kb__"] + ss.doc_index.doc_names()
        labels = {"__all__": f"📚 + 📄 {T(lang, 'all_docs')}", "__kb__": f"📚 {T(lang, 'kb_only')}"}
        scope = st.selectbox(T(lang, "searching_in"), opts, format_func=lambda x: labels.get(x, f"📄 {x}"), key="scope")

    ex = EXAMPLES[lang]
    if not ss.chat:
        H(f'<div class="empty"><div class="big">💬</div>{esc(T(lang, "chat_empty"))}</div>')
        chip_area = st.container()
    else:
        chip_area = st.expander(f"💡 {T(lang, 'try_asking')}")
    with chip_area:
        cols = st.columns(2)
        for i, q in enumerate(ex):
            cols[i % 2].button(q, key=f"ex_{lang}_{i}", on_click=pick_example, args=(q,), use_container_width=True)

    history = st.container()
    typed = st.chat_input(T(lang, "chat_placeholder"), key="chat_in")
    q = typed or ss.pop("pending_q", None)
    if q and q.strip():
        ss.chat.append({"role": "user", "content": q.strip()})
        ss.chat.append(run_query(q.strip(), scope))

    with history:
        for i, m in enumerate(ss.chat):
            if m["role"] == "user":
                with st.chat_message("user"):
                    st.write(m["content"])
            else:
                with st.chat_message("assistant", avatar="⚖️"):
                    render_answer(m, i)

    if ss.chat:
        b1, b2, _ = st.columns([1, 1, 3])
        if b1.button("🗑 " + T(lang, "clear_chat"), key="clear_chat"):
            ss.chat = []
            ss.feedback = {}
            st.rerun()
        b2.download_button("⬇ " + T(lang, "download_chat"), chat_transcript(), file_name="legalease_chat.txt", key="dl_chat")

# ============================== DOCUMENTS ==============================
with tab_docs:
    H(f'<div class="sec-title">{esc(T(lang, "docs_title"))}</div><div class="sec-sub">{esc(T(lang, "docs_sub"))}</div>')
    up_col, paste_col = st.columns(2, gap="large")
    with up_col:
        files = st.file_uploader(T(lang, "upload_label"), type=["pdf", "txt"], accept_multiple_files=True,
                                 key=f"uploader_{ss.uploader_ver}", help=f"Max {MAX_UPLOAD_MB} MB")
        st.caption(T(lang, "upload_hint"))
        for f in files or []:
            if ss.doc_index.has_doc(f.name):
                continue
            if f.name.lower().endswith(".txt"):
                text = f.getvalue().decode("utf-8", errors="ignore")
                pages = [{"page_num": 1, "text": text}] if text.strip() else []
            else:
                with st.spinner(f"{f.name} ..."):
                    pages = extract_pages_from_pdf(f)
            if pages:
                add_document(f.name, pages)
                st.toast(f"{f.name} {T(lang, 'added_ok')} ✅")
            else:
                st.warning(f"{f.name}: {T(lang, 'scan_warn')}")
    with paste_col:
        pasted = st.text_area(T(lang, "paste_label"), height=130, key="paste_text", label_visibility="visible")
        pc1, pc2 = st.columns([1, 1])
        if pc1.button(T(lang, "analyze_btn"), type="primary", key="analyze_paste", use_container_width=True):
            if pasted.strip():
                name = f"Pasted text {datetime.now():%H:%M:%S}"
                add_document(name, [{"page_num": 1, "text": pasted.strip()}])
                st.rerun()
        if pc2.button("📋 " + T(lang, "sample_btn"), key="sample_btn", use_container_width=True):
            with open(os.path.join(BASE, "data", "sample_rent_agreement.txt"), encoding="utf-8") as fh:
                add_document("Sample rent agreement", [{"page_num": 1, "text": fh.read()}])
            st.rerun()

    names = ss.doc_index.doc_names()
    if not names:
        H(f'<div class="card"><div class="empty"><div class="big">📄</div>{esc(T(lang, "no_docs"))}</div></div>')
    else:
        sel_col, rm_col = st.columns([4, 1], vertical_alignment="bottom")
        default = ss.get("active_doc") if ss.get("active_doc") in names else names[-1]
        doc = sel_col.selectbox(T(lang, "choose_doc"), names, index=names.index(default), key="doc_select")
        if rm_col.button("🗑 " + T(lang, "remove_doc"), key="rm_doc", use_container_width=True):
            ss.doc_index.remove(doc)
            ss.analyses.pop(doc, None)
            ss.uploader_ver += 1
            ss.pop("active_doc", None)
            st.rerun()
        a = ss.analyses.get(doc) or analyze(ss.doc_index.texts[doc])
        ss.analyses[doc] = a

        risk_txt = T(lang, f"risk_{a['risk']}")
        n_flags = len(a["flags"])
        r1, r2, r3, r4 = st.columns([2.2, 1, 1, 1])
        with r1:
            H(f"""<div class="risk {a['risk']}"><div class="dot"></div><div>{esc(T(lang, 'risk_level'))}: {esc(risk_txt)}
            <small>{n_flags} {esc(T(lang, 'sec_flags')).lower()} · {a['words']} {esc(T(lang, 'doc_stats'))}</small></div></div>""")
        with r2:
            H(f'<div class="stat"><b>{a["words"]}</b><span>{esc(T(lang, "doc_stats")).upper()}</span></div>')
        with r3:
            H(f'<div class="stat"><b>{n_flags}</b><span>{esc(T(lang, "sec_flags")).upper()}</span></div>')
        with r4:
            H(f'<div class="stat"><b>{len(a["amounts"])}</b><span>{esc(T(lang, "facts_amounts")).upper()}</span></div>')

        left, right = st.columns([1.35, 1], gap="large")
        with left:
            H(f'<div class="h5">{esc(T(lang, "sec_summary"))}</div>')
            sm = "".join(f"<li>{esc(s)}</li>" for s in a["summary"]) or f"<li>{esc(T(lang, 'none_found'))}</li>"
            H(f'<div class="card"><div class="sec-sub" style="margin-bottom:6px">{esc(T(lang, "sec_summary_note"))}</div><ol class="steps">{sm}</ol></div>')
            H(f'<div class="h5">{esc(T(lang, "sec_flags"))}</div>')
            if not a["flags"]:
                H(f'<div class="risk low"><div class="dot"></div><div>{esc(T(lang, "no_flags"))}</div></div>')
            for fl in a["flags"]:
                H(f"""<div class="flag {fl['severity']}"><span class="sev {fl['severity']}">{esc(T(lang, 'sev_' + fl['severity']))}</span>
                {esc(tx(fl['explain']))}<div class="q">{esc(fl['quote'])}</div></div>""")
        with right:
            def facts(label, items):
                body = "".join(f"<li>{esc(i)}</li>" for i in items) or f"<li style='color:{MUTED}'>{esc(T(lang, 'none_found'))}</li>"
                return f'<div class="h5">{esc(label)}</div><div class="mini"><ul>{body}</ul></div>'
            H('<div class="card">' + f'<div class="h5" style="margin-top:0">{esc(T(lang, "sec_facts"))}</div>'
              + facts(T(lang, "facts_amounts"), a["amounts"]) + facts(T(lang, "facts_durations"), a["durations"])
              + facts(T(lang, "facts_dates"), a["dates"]) + facts(T(lang, "facts_notice"), [(n if len(n) <= 150 else n[:150].rsplit(" ", 1)[0] + "…") for n in a["notice"]]) + '</div>')
            if a["jargon"]:
                H(f'<div class="h5">{esc(T(lang, "sec_jargon"))}</div>')
                rows = "".join(f'<div class="t">{esc(j["term"])}</div><div>{esc(tx(j["meaning"]))}</div>' for j in a["jargon"])
                H(f'<div class="card"><div class="jg">{rows}</div></div>')

        if a["obligations"]:
            with st.expander(f"📌 {T(lang, 'sec_oblig')}"):
                for o in a["obligations"]:
                    st.markdown(f"- {o}")
        st.info(T(lang, "ask_doc_hint"), icon="💬")

        # downloadable report
        rep = [f"{APP_TITLE} - Document report: {doc}", f"Risk: {a['risk'].upper()}  |  Words: {a['words']}", "", "SUMMARY"]
        rep += [f"- {s}" for s in a["summary"]] + ["", "CLAUSES TO CHECK"]
        rep += [f"- [{f['severity'].upper()}] {f['explain']['en']}  ({f['quote']})" for f in a["flags"]] or ["- none detected"]
        rep += ["", "KEY FACTS", "Amounts: " + ", ".join(a["amounts"]), "Periods: " + ", ".join(a["durations"]), "Dates: " + ", ".join(a["dates"]),
                "", "Not legal advice. Please consult a licensed advocate."]
        st.download_button("⬇ " + T(lang, "download_report"), "\n".join(rep), file_name="legalease_report.txt", key="dl_report")

# ============================== RIGHTS ==============================
with tab_rights:
    H(f'<div class="sec-title">{esc(T(lang, "rights_title"))}</div><div class="sec-sub">{esc(T(lang, "rights_sub"))}</div>')
    term = st.text_input(T(lang, "rights_search"), key="rights_q", placeholder="🔎 …", label_visibility="collapsed").strip().lower()
    shown = 0
    for t in TOPICS:
        hay = (" ".join(t["title"].values()) + " " + t["keywords"]).lower()
        if term and term not in hay:
            continue
        shown += 1
        with st.expander(f"{t['icon']}  {tx(t['title'])}", expanded=bool(term) and shown == 1):
            H(topic_card_html(t, compact=True))
    if not shown:
        H(f'<div class="card"><div class="empty">{esc(T(lang, "ans_none"))}</div></div>')

# ============================== SERVICES ==============================
with tab_svc:
    H(f'<div class="sec-title">{esc(T(lang, "svc_title"))}</div><div class="sec-sub">{esc(T(lang, "svc_sub"))}</div>')
    for i, c in enumerate(COMPLIANCE):
        with st.expander(f"{c['icon']}  {tx(c['title'])}", expanded=(i == 0)):
            H(compliance_card_html(c, compact=True))

# ============================== LAWYERS ==============================
with tab_law:
    H(f'<div class="sec-title">{esc(T(lang, "law_title"))}</div>')
    st.info(T(lang, "law_demo"), icon="ℹ️")
    lawyers = get_lawyers()
    all_l = T(lang, "f_all")
    f1, f2, f3, f4 = st.columns(4)
    city = f1.selectbox(T(lang, "f_city"), [all_l] + get_unique(lawyers, "city"), key="f_city")
    spec = f2.selectbox(T(lang, "f_spec"), [all_l] + get_unique(lawyers, "specialization"), key="f_spec")
    lg = f3.selectbox(T(lang, "f_lang"), [all_l] + list(LANGS.keys()), format_func=lambda x: all_l if x == all_l else LANGS[x], key="f_lang")
    max_fee = f4.slider(T(lang, "f_fee"), 500, 3000, 3000, step=100, key="f_fee")
    res = filter_lawyers(lawyers, None if city == all_l else city, None if spec == all_l else spec,
                         None if lg == all_l else lg, max_fee)
    st.caption(f"**{len(res)}** {T(lang, 'law_count')}")
    if not res:
        H(f'<div class="card"><div class="empty"><div class="big">🔍</div>{esc(T(lang, "law_none"))}</div></div>')
    cols = st.columns(2)
    for i, l in enumerate(res):
        ini = "".join(w[0] for w in l["name"].replace("Adv. ", "").split()[:2]).upper()
        tags = "".join(f'<span class="chip">{esc(s)}</span>' for s in l["specialization"])
        lgs = " · ".join(LANGS[x] for x in l["languages"])
        with cols[i % 2]:
            H(f"""<div class="card" style="margin-bottom:12px"><div class="lawyer"><div class="avatar">{esc(ini)}</div><div>
            <div class="lname">{esc(l['name'])}</div>
            <div class="lmeta">📍 {esc(l['city'])}, {esc(l['state'])} · {l['experience']} {esc(T(lang, 'law_exp'))}</div>
            <div>{tags}</div>
            <div class="lmeta" style="margin-top:6px">🗣 {esc(lgs)} · {esc(T(lang, 'law_fee'))}: <b>₹{l['fees']}</b></div>
            <a class="callbtn" href="tel:{esc(l['phone'])}">📞 {esc(T(lang, 'law_call'))} {esc(l['phone'])}</a></div></div></div>""")

# ============================== SOS ==============================
with tab_sos:
    H(f'<div class="sec-title">{esc(T(lang, "sos_title"))}</div>')
    H(f'<div class="sosbanner"><div style="font-size:30px">🚨</div><div>{esc(T(lang, "sos_alert"))}</div></div>')
    st.caption(T(lang, "sos_tip"))
    cards = ""
    for it in get_localized_numbers(lang):
        cards += f"""<a class="sos {'prio' if it['prio'] else ''}" href="tel:{it['number']}"><div class="ico">{it['icon']}</div>
        <div><div class="nm">{esc(it['name'])}</div><div class="ds">{esc(it['desc'])}</div></div><div class="num">{it['number']}</div></a>"""
    H(f'<div class="sosgrid">{cards}</div>')

# ============================== ABOUT ==============================
with tab_about:
    H(f'<div class="sec-title">{esc(T(lang, "about_title"))}</div>')
    m1, m2, m3, m4 = st.columns(4)
    for col, num, lab in ((m1, len(TOPICS) + len(COMPLIANCE), T(lang, "metric_topics")), (m2, 3, T(lang, "metric_langs")),
                          (m3, len(EMERGENCY_NUMBERS), T(lang, "metric_helplines")), (m4, ss.doc_index.num_docs(), T(lang, "metric_docs"))):
        col.markdown(f'<div class="stat"><b>{num}</b><span>{esc(lab).upper()}</span></div>', unsafe_allow_html=True)
    H(f'<div class="card" style="margin-top:14px"><div class="ans-simple">{esc(T(lang, "about_body"))}</div>'
      f'<div class="h5">{esc(T(lang, "about_features"))}</div><div class="mini"><ul>' + "".join(f"<li>{esc(x)}</li>" for x in ABOUT_FEATURES[lang]) + '</ul></div>'
      f'<div class="h5">{esc(T(lang, "about_how"))}</div><div class="mini"><ul>' + "".join(f"<li>{esc(x)}</li>" for x in ABOUT_HOW[lang]) + '</ul></div>'
      f'<div class="h5">{esc(T(lang, "about_limits"))}</div><div class="mini">{esc(T(lang, "about_limits_body"))}</div></div>')
