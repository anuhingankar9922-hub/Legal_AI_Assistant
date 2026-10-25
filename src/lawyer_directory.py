import json
import os


def load_lawyers(json_path: str):
    try:
        if not os.path.exists(json_path):
            return []
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def get_unique(lawyers, field):
    vals = set()
    for l in lawyers:
        v = l.get(field)
        if isinstance(v, list):
            vals.update(v)
        elif v:
            vals.add(v)
    return sorted(vals)


def filter_lawyers(lawyers, city=None, spec=None, lang=None, max_fee=None):
    out = lawyers
    if city:
        out = [l for l in out if l.get("city") == city]
    if spec:
        out = [l for l in out if spec in l.get("specialization", [])]
    if lang:
        out = [l for l in out if lang in l.get("languages", [])]
    if max_fee is not None:
        out = [l for l in out if l.get("fees", 0) <= max_fee]
    return sorted(out, key=lambda l: (-l.get("experience", 0), l.get("fees", 0)))
