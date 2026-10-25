"""Plain-language document analyzer: key facts, red flags, jargon buster, summary.

Works fully offline with rules + TF scoring (no API key needed), so the demo
never breaks. Explanations are available in English, Hindi and Marathi.
"""
import re
from collections import Counter

# ----------------------------------------------------------------- red flags
# (id, regex, severity, {lang: explanation})
RED_FLAGS = [
    ("autorenew", r"auto(?:matic(?:ally)?)?[\s-]*renew|renew(?:s|ed)? automatically|deemed to be renewed", "medium",
     {"en": "The agreement renews on its own. Note the date by which you must cancel.",
      "hi": "समझौता अपने-आप नवीनीकृत हो जाता है। रद्द करने की अंतिम तारीख याद रखें।",
      "mr": "करार आपोआप नूतनीकृत होतो. रद्द करण्याची अंतिम तारीख लक्षात ठेवा."}),
    ("penalty", r"penalt(?:y|ies)|liquidated damages|forfeit(?:ed|ure)?|fine of", "high",
     {"en": "A penalty or forfeiture applies if you break a rule. Check the amount is reasonable.",
      "hi": "नियम टूटने पर जुर्माना या ज़ब्ती लागू होती है। राशि उचित है या नहीं जाँचें।",
      "mr": "नियम मोडल्यास दंड किंवा जप्ती लागू होते. रक्कम योग्य आहे का ते तपासा."}),
    ("nonrefund", r"non[\s-]?refundable|not (?:be )?refund(?:ed|able)|no refund", "high",
     {"en": "Money paid cannot be taken back. Be sure before you pay.",
      "hi": "दिया गया पैसा वापस नहीं मिलेगा। भुगतान से पहले पक्का कर लें।",
      "mr": "भरलेले पैसे परत मिळणार नाहीत. पैसे देण्यापूर्वी खात्री करा."}),
    ("terminate", r"terminat\w+ (?:this agreement |the agreement |the tenancy |your )?(?:at any time|without (?:any )?(?:prior )?notice|with immediate effect|without assigning)|without (?:any )?(?:prior )?notice", "high",
     {"en": "The other side can end the agreement without notice or a reason. Ask for a fair notice period.",
      "hi": "दूसरा पक्ष बिना नोटिस या कारण के समझौता खत्म कर सकता है। उचित नोटिस अवधि माँगें।",
      "mr": "दुसरा पक्ष नोटीस किंवा कारणाशिवाय करार संपवू शकतो. योग्य नोटीस कालावधी मागा."}),
    ("sole", r"sole (?:and absolute )?discretion|at (?:its|his|her|their) (?:own )?discretion|unilateral(?:ly)?", "medium",
     {"en": "One side alone can decide or change things. Ask for mutual consent instead.",
      "hi": "केवल एक पक्ष निर्णय या बदलाव कर सकता है। आपसी सहमति की शर्त माँगें।",
      "mr": "केवळ एक पक्ष निर्णय किंवा बदल करू शकतो. परस्पर संमतीची अट मागा."}),
    ("indemnify", r"indemnif\w+|hold harmless", "high",
     {"en": "You may have to cover the other side's losses and legal costs. This can be very costly.",
      "hi": "आपको दूसरे पक्ष का नुकसान और कानूनी खर्च भरना पड़ सकता है। यह बहुत महँगा हो सकता है।",
      "mr": "दुसऱ्या पक्षाचे नुकसान आणि कायदेशीर खर्च तुम्हाला भरावा लागू शकतो. हे खूप महागडे ठरू शकते."}),
    ("arbitration", r"arbitrat\w+", "low",
     {"en": "Disputes go to a private arbitrator, not a court. Check who appoints the arbitrator and where.",
      "hi": "विवाद अदालत की जगह निजी मध्यस्थ के पास जाएँगे। मध्यस्थ कौन नियुक्त करेगा और कहाँ, यह जाँचें।",
      "mr": "वाद न्यायालयाऐवजी खाजगी लवादाकडे जातील. लवाद कोण नेमतो व कुठे ते तपासा."}),
    ("jurisdiction", r"(?:exclusive )?jurisdiction of (?:the )?(?:courts?|tribunals?)(?: at| in| of)? [A-Z][a-z]+", "low",
     {"en": "Court cases can only be filed in a specific city. Check it is convenient for you.",
      "hi": "मुकदमा केवल एक तय शहर में हो सकता है। देखें कि यह आपके लिए सुविधाजनक है या नहीं।",
      "mr": "खटला फक्त ठराविक शहरातच दाखल करता येतो. ते तुमच्यासाठी सोयीचे आहे का ते पहा."}),
    ("noncompete", r"non[\s-]?compete|restrain(?:ed|t)? (?:from|of) (?:trade|competing)|shall not (?:join|work for|engage in) .{0,40}compet", "medium",
     {"en": "You are barred from similar work after leaving. After-employment non-competes are generally void under Section 27 of the Contract Act.",
      "hi": "छोड़ने के बाद समान काम करने से रोका गया है। नौकरी के बाद की ऐसी रोक आमतौर पर अनुबंध अधिनियम धारा 27 के तहत शून्य है।",
      "mr": "सोडल्यानंतर तत्सम काम करण्यास मनाई आहे. नोकरीनंतरची अशी मनाई सामान्यतः करार कायद्याच्या कलम 27 अन्वये रद्दबातल आहे."}),
    ("lockin", r"lock[\s-]?in|minimum (?:stay|period|term) of|shall not (?:vacate|leave|terminate) (?:before|within|during)", "medium",
     {"en": "You are tied in for a minimum period. Leaving early may cost you money.",
      "hi": "आप न्यूनतम अवधि तक बँधे हैं। जल्दी छोड़ने पर पैसा कट सकता है।",
      "mr": "तुम्ही किमान कालावधीसाठी बांधलेले आहात. लवकर सोडल्यास पैसे कापले जाऊ शकतात."}),
    ("interest", r"interest (?:at|of|@)[^.]{0,30}(?:per (?:month|annum)|p\.?m\.?|p\.?a\.?|%)|\d+(?:\.\d+)?\s?% per (?:month|annum)", "medium",
     {"en": "Interest is charged on late payment or loans. Compare the rate with the normal bank rate.",
      "hi": "देर से भुगतान या ऋण पर ब्याज लगता है। दर की तुलना सामान्य बैंक दर से करें।",
      "mr": "उशिरा पेमेंट किंवा कर्जावर व्याज लागते. दराची सामान्य बँक दराशी तुलना करा."}),
    ("deposit", r"(?:security )?deposit[^.]{0,80}(?:forfeit|deduct|adjust|not (?:be )?(?:returned|refunded))", "medium",
     {"en": "Deductions can be made from your deposit. Ask for a clear list of what can be deducted and a return date.",
      "hi": "जमानत राशि से कटौती हो सकती है। क्या कट सकता है और वापसी की तारीख की स्पष्ट सूची माँगें।",
      "mr": "अनामत रकमेतून कपात होऊ शकते. काय कापले जाईल व परतीची तारीख याची स्पष्ट यादी मागा."}),
    ("increase", r"(?:rent|fee|charges?|price)[^.]{0,60}(?:increase|escalat|enhance)[^.]{0,60}\d+\s?%", "low",
     {"en": "The price goes up every year or period. Note the percentage.",
      "hi": "कीमत हर साल या अवधि में बढ़ती है। प्रतिशत नोट करें।",
      "mr": "किंमत दरवर्षी किंवा ठराविक कालावधीने वाढते. टक्केवारी नोंदवा."}),
]

SEVERITY_RANK = {"high": 0, "medium": 1, "low": 2}

# ----------------------------------------------------------------- jargon
# (regex, term, {lang: simple meaning})
JARGON = [
    (r"\blessor\b|\blandlord\b", "Lessor / Landlord", {"en": "The owner who gives the property on rent.", "hi": "संपत्ति किराये पर देने वाला मालिक।", "mr": "मालमत्ता भाड्याने देणारा मालक."}),
    (r"\blessee\b|\btenant\b", "Lessee / Tenant", {"en": "The person who takes the property on rent.", "hi": "किराये पर संपत्ति लेने वाला व्यक्ति।", "mr": "भाड्याने मालमत्ता घेणारी व्यक्ती."}),
    (r"\bhereinafter\b", "Hereinafter", {"en": "'From now on in this document' - a short name given to a party.", "hi": "'अब से इस दस्तावेज़ में' - किसी पक्ष को दिया गया छोटा नाम।", "mr": "'यापुढे या दस्तऐवजात' - पक्षाला दिलेले संक्षिप्त नाव."}),
    (r"\bindemnif\w+", "Indemnify", {"en": "Promise to pay for the other side's loss.", "hi": "दूसरे पक्ष के नुकसान की भरपाई का वादा।", "mr": "दुसऱ्या पक्षाच्या नुकसानीची भरपाई करण्याचे वचन."}),
    (r"\bforthwith\b", "Forthwith", {"en": "Immediately.", "hi": "तुरंत।", "mr": "ताबडतोब."}),
    (r"\bnotwithstanding\b", "Notwithstanding", {"en": "'Despite' - this clause overrides others.", "hi": "'बावजूद' - यह शर्त दूसरों पर भारी है।", "mr": "'तरीही' - ही अट इतरांवर प्रभावी आहे."}),
    (r"\bwhereas\b", "Whereas", {"en": "Background facts that explain why the agreement is made.", "hi": "पृष्ठभूमि जो बताती है कि समझौता क्यों हो रहा है।", "mr": "करार का केला जातो ते सांगणारी पार्श्वभूमी."}),
    (r"\bper annum\b|\bp\.a\.", "Per annum", {"en": "Per year.", "hi": "प्रति वर्ष।", "mr": "दरवर्षी."}),
    (r"\bliquidated damages\b", "Liquidated damages", {"en": "A fixed compensation amount agreed in advance for a breach.", "hi": "उल्लंघन पर पहले से तय मुआवज़ा राशि।", "mr": "भंगासाठी आधीच ठरलेली नुकसानभरपाई रक्कम."}),
    (r"\bforce majeure\b", "Force majeure", {"en": "Events outside anyone's control (flood, war, pandemic) that excuse delays.", "hi": "किसी के नियंत्रण से बाहर घटनाएँ (बाढ़, युद्ध, महामारी) जो देरी माफ़ करती हैं।", "mr": "कोणाच्याही नियंत्रणाबाहेरील घटना (पूर, युद्ध, महामारी) ज्या विलंबास माफी देतात."}),
    (r"\barbitrat\w+", "Arbitration", {"en": "Settling a dispute through a private referee instead of court.", "hi": "अदालत की जगह निजी मध्यस्थ से विवाद सुलझाना।", "mr": "न्यायालयाऐवजी खाजगी लवादामार्फत वाद सोडवणे."}),
    (r"\bjurisdiction\b", "Jurisdiction", {"en": "Which court has the power to hear the case.", "hi": "कौन सी अदालत मामला सुन सकती है।", "mr": "कोणते न्यायालय खटला ऐकू शकते."}),
    (r"\bperpetual\b|\birrevocabl\w+", "Perpetual / Irrevocable", {"en": "Forever / cannot be cancelled.", "hi": "हमेशा के लिए / रद्द नहीं हो सकता।", "mr": "कायमचे / रद्द करता येत नाही."}),
    (r"\bsub[\s-]?let(?:ting)?\b|\bsub[\s-]?leas\w+", "Sub-letting", {"en": "Renting the property further to someone else.", "hi": "संपत्ति आगे किसी और को किराये पर देना।", "mr": "मालमत्ता पुढे दुसऱ्याला भाड्याने देणे."}),
    (r"\bsurety\b|\bguarantor\b", "Surety / Guarantor", {"en": "A person who promises to pay if you fail to.", "hi": "वह व्यक्ति जो आपके चूकने पर भुगतान का वादा करता है।", "mr": "तुम्ही चुकल्यास पैसे भरण्याचे वचन देणारी व्यक्ती."}),
    (r"\bmortgage\b|\blien\b|\bcharge over\b", "Mortgage / Lien", {"en": "Your property is held as security for a debt.", "hi": "ऋण की सुरक्षा के रूप में आपकी संपत्ति गिरवी है।", "mr": "कर्जाची हमी म्हणून तुमची मालमत्ता तारण आहे."}),
    (r"\bsuccessors? and assigns\b", "Successors and assigns", {"en": "The agreement also binds heirs and anyone who takes over later.", "hi": "समझौता वारिसों और बाद में अधिकार लेने वालों पर भी लागू होता है।", "mr": "करार वारस आणि नंतर हक्क घेणाऱ्यांवरही बंधनकारक आहे."}),
    (r"\bvacant possession\b", "Vacant possession", {"en": "Handing over the property empty, with no one living in it.", "hi": "संपत्ति खाली करके सौंपना।", "mr": "मालमत्ता रिकामी करून ताब्यात देणे."}),
]

# ----------------------------------------------------------------- key facts
AMOUNT_RE = re.compile(r"(?:₹|\bRs\.?|\bINR)\s?\d[\d,]*(?:\.\d+)?(?:\s?(?:lakh|lac|crore|thousand)\b|/-)?", re.I)
DURATION_RE = re.compile(r"\b(\d+|one|two|three|six|eleven|twelve|thirty|sixty|ninety)\s?(?:\(\d+\)\s?)?(day|week|month|year)s?\b", re.I)
DATE_RE = re.compile(
    r"\b(\d{1,2}(?:st|nd|rd|th)?[\s/-](?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)[\s,/-]+\d{4}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b", re.I)
NOTICE_RE = re.compile(r"([^.]{0,80}\bnotice\b[^.]{0,80})", re.I)

OBLIGATION_RE = re.compile(r"\b(shall|must|agrees? to|undertakes? to|is liable|will be liable|required to|responsible for|obliged)\b", re.I)


_ABBR = re.compile(r"\b(Rs|Mr|Mrs|Ms|Dr|Adv|No|Nos|Sr|Jr|St|Smt|Shri|Sec|Art|Ltd|Pvt|vs|etc|viz)\.", re.I)


def _sentences(text):
    text = re.sub(r"\s+", " ", text)
    text = _ABBR.sub(lambda m: m.group(1) + "․", text)  # protect abbreviation dots
    parts = re.split(r"(?<=[.!?;।])\s+(?=[A-Z0-9₹(ऀ-ॿ])", text)
    return [p.strip().replace("․", ".") for p in parts if len(p.strip()) > 25]


def _tokens(s):
    return re.findall(r"[A-Za-zऀ-ॿ]{3,}", s.lower())


STOP = set("the and for that this with shall any all are not from have has been will which such their into upon under shall hereby between".split())


def analyze(text, lang="en"):
    """Return a dict with summary sentences, key facts, red flags, jargon, obligations."""
    text = text or ""
    sents = _sentences(text)

    # --- extractive summary: weight by word frequency + signal words
    freq = Counter(w for w in _tokens(text) if w not in STOP)
    scored = []
    for i, s in enumerate(sents):
        toks = [w for w in _tokens(s) if w not in STOP]
        if not toks:
            continue
        score = sum(freq[w] for w in toks) / (len(toks) ** 0.7)
        if OBLIGATION_RE.search(s):
            score *= 1.25
        if AMOUNT_RE.search(s) or DURATION_RE.search(s):
            score *= 1.2
        if i < 4:
            score *= 1.1
        scored.append((score, i, s))
    top = sorted(scored, reverse=True)[:5]
    summary = [s for _, _, s in sorted(top, key=lambda x: x[1])]

    # --- key facts
    amounts = []
    for m in AMOUNT_RE.finditer(text):
        label = m.group(0).strip().rstrip(",.")
        if label not in amounts:
            amounts.append(label)
    durations = []
    for m in DURATION_RE.finditer(text):
        label = m.group(0).strip()
        if label.lower() not in [d.lower() for d in durations]:
            durations.append(label)
    dates = []
    for m in DATE_RE.finditer(text):
        if m.group(0) not in dates:
            dates.append(m.group(0))
    notice = []
    for m in NOTICE_RE.finditer(re.sub(r"\s+", " ", text)):
        t = m.group(1).strip()
        if t and t not in notice:
            notice.append(t)

    # --- red flags
    flags = []
    flat = re.sub(r"\s+", " ", text)
    for fid, rx, sev, expl in RED_FLAGS:
        m = re.search(rx, flat, re.I)
        if m:
            start = max(0, m.start() - 90)
            end = min(len(flat), m.end() + 110)
            flags.append({"id": fid, "severity": sev, "explain": expl, "quote": "…" + flat[start:end].strip() + "…"})
    flags.sort(key=lambda f: SEVERITY_RANK[f["severity"]])

    # --- jargon
    jargon = []
    for rx, term, meaning in JARGON:
        if re.search(rx, flat, re.I):
            jargon.append({"term": term, "meaning": meaning})

    # --- obligations
    obligations = [s for s in sents if OBLIGATION_RE.search(s)][:6]

    # --- risk score
    pts = sum({"high": 3, "medium": 2, "low": 1}[f["severity"]] for f in flags)
    risk = "high" if pts >= 7 else "medium" if pts >= 3 else "low"

    return {
        "words": len(text.split()),
        "summary": summary,
        "amounts": amounts[:8],
        "durations": durations[:8],
        "dates": dates[:6],
        "notice": notice[:3],
        "flags": flags,
        "jargon": jargon,
        "obligations": obligations,
        "risk": risk,
    }
