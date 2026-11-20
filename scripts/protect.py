#!/usr/bin/env python3
"""protect.py - what a polish must NOT change, and the verifier that proves it.

`inventory(text)` extracts, from one sentence, everything that carries meaning independent of wording: protected spans (citations, figure / table / equation
references, LaTeX commands that point somewhere, math, code, URLs), numbers with units, negations, quantifiers and bounds, modal / hedge / booster strength,
causal vs correlational wording, conditionals, direction of change (up / down), abbreviations and named terms.
`verify_edit(original, revised)` compares two inventories and reports every difference with a severity: a polish that drops a negation, turns "may" into
"will", turns "associated with" into "causes", swaps increase and decrease, changes a number or a citation number is an ERROR, not a style choice.
Nothing here calls a model. English and Chinese.
"""
from __future__ import annotations

import difflib
import re
from collections import Counter

import nlib

# ------------------------------------------------------------------------------------------------ protected spans
CITE_CMDS = r"cite[a-zA-Z]*|ref|eqref|autoref|cref|Cref|pageref|label|nocite|url|href|footref"
P_LATEX_REF = r"\\(?:%s)\*?(?:\[[^\]]*\])*\{[^{}]*\}" % CITE_CMDS
P_MATH = r"\$\$.+?\$\$|(?<!\\)\$[^$\n]+?(?<!\\)\$|\\\(.+?\\\)|\\\[.+?\\\]"
P_CODE = r"(?<!`)`[^`\n]+`(?!`)"
P_URL = r"https?://[^\s)>\]]+|doi:\s?10\.\S+|\b10\.\d{4,9}/[^\s)>\]]+|www\.[^\s)>\]]+|[\w.+-]+@[\w-]+\.[\w.-]+"
P_NUMCITE = r"\[\s*\d+(?:\s*[-–,;]\s*\d+)*\s*\]"
P_AUTHYEAR = r"\((?:[A-Z][A-Za-z'’-]+(?:\s+(?:et\s+al\.?|and|&)\s*(?:[A-Z][A-Za-z'’-]+)?)?,?\s*(?:19|20)\d{2}[a-z]?(?:\s*[;,]\s*)?)+\)"
P_FIGREF = r"\b(?:Figs?\.?|Figures?|Tables?|Tab\.|Eqs?\.?|Equations?|Sections?|Sec\.|Appendix|Algorithms?|Supplementary\s+(?:Figure|Table)s?|Panels?)\s*(?:\(\s*[A-Z]?\d+(?:\.\d+)*[a-z]?\s*\)|[A-Z]?\d+(?:\.\d+)*[a-z]?(?:\s*[-–,&]\s*[A-Z]?\d+[a-z]?)*)"
P_ZHREF = r"[图表式附录]\s*(?:\(\s*[A-Za-z]?\d+(?:[-.]\d+)*[a-z]?\s*\)|[A-Za-z]?\d+(?:[-.]\d+)*[a-z]?)|第\s*\d+\s*[章节条]|\[\s*\d+(?:\s*[-–,，]\s*\d+)*\s*\]"
PROTECT_RE = re.compile("|".join("(?:%s)" % p for p in (P_LATEX_REF, P_MATH, P_CODE, P_URL, P_NUMCITE, P_AUTHYEAR, P_FIGREF, P_ZHREF)), re.S)
LATEX_CMD = re.compile(r"\\([A-Za-z]+)\*?")


def protected_spans(text):
    """[(start, end, string)] of spans a polish must keep verbatim (position may move, content may not)"""
    return [(m.start(), m.end(), m.group(0)) for m in PROTECT_RE.finditer(text)]


def norm_protected(s):
    s = re.sub(r"\s+", "", s)
    s = s.replace("Figure", "Fig").replace("Figures", "Figs").replace("Fig.", "Fig").replace("Figs.", "Figs").replace("Tab.", "Table").replace("Equation", "Eq").replace("Eq.", "Eq").replace("Section", "Sec").replace("Sec.", "Sec")
    return s.replace("–", "-").replace("，", ",")


# ------------------------------------------------------------------------------------------------ numbers
NUMWORDS = {"zero": 0, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
            "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90, "hundred": 100, "thousand": 1000,
            "half": 0.5, "dozen": 12, "double": 2, "triple": 3, "twice": 2, "once": 1, "两": 2, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
UNIT = r"%|‰|°C|℃|°F|°|K|kg|g|mg|μg|µg|ug|ng|m|cm|mm|μm|µm|um|nm|km|L|mL|μL|µL|uL|mol|mmol|μmol|umol|M|mM|μM|uM|nM|s|ms|μs|us|min|h|hr|d|Hz|kHz|MHz|GHz|W|kW|V|mV|A|mA|eV|keV|MeV|GeV|Pa|kPa|MPa|GPa|N|J|kJ|bar|ppm|ppb|dB|px|GB|MB|KB|TB|bit|bits|fold|x|×|percent|per\s*cent|years?|months?|days?|hours?|minutes?|seconds?|weeks?|times|samples|patients|participants|epochs|steps|layers|parameters|个|次|倍|年|月|日|天|小时|分钟|秒|米|克|千克|毫米|厘米|公里|摄氏度|度|元|人|例|%"
NUM_RE = re.compile(r"(?<![\w.])([-−–+±]?\d{1,3}(?:,\d{3})+(?:\.\d+)?|[-−–+±]?\d+(?:\.\d+)?(?:[eE][-+−]?\d+)?)\s*(" + UNIT + r")?(?![A-Za-z])")
WORDNUM_RE = re.compile(r"\b(" + "|".join(sorted((w for w in NUMWORDS if w.isascii()), key=len, reverse=True)) + r")\b", re.I)


def norm_unit(u):
    u = (u or "").strip().lower().replace("per cent", "percent").replace("percent", "%").replace("℃", "°c").replace("µ", "μ")
    if u in ("um", "ul", "ug", "umol", "um", "us"):
        u = "μ" + u[1:]
    return {"hr": "h", "hours": "h", "hour": "h", "years": "year", "months": "month", "days": "day", "minutes": "minute", "seconds": "second", "weeks": "week", "bits": "bit", "×": "x"}.get(u, u)


def numbers_of(text):
    """multiset of (value, unit); spelled-out numbers count as numbers (three == 3); protected spans are skipped (they have their own check)"""
    t = text
    for s, e, _ in reversed(protected_spans(text)):
        t = t[:s] + " " + t[e:]
    out = []
    for m in NUM_RE.finditer(t):
        v = m.group(1).replace(",", "").replace("−", "-").replace("–", "-")
        try:
            f = float(v)
            v = ("%g" % f)
        except ValueError:
            pass
        out.append((v, norm_unit(m.group(2))))
    for m in WORDNUM_RE.finditer(t):
        w = m.group(1).lower()
        if w in ("single", "once", "half", "double", "triple", "twice", "dozen") and True:
            continue
        out.append(("%g" % NUMWORDS[w], ""))
    # a bare number and the same number with a unit are different facts
    return Counter(out)


# ------------------------------------------------------------------------------------------------ lexicons of meaning-bearing wording
def wre(words):
    return re.compile(r"(?<![\w-])(?:%s)(?![\w-])" % "|".join(words), re.I)


NEG_EN = wre([r"not", r"no", r"never", r"neither", r"nor", r"none", r"nothing", r"nobody", r"without", r"cannot", r"can't", r"won't", r"don't", r"doesn't", r"didn't", r"isn't", r"aren't", r"wasn't", r"weren't", r"hasn't", r"haven't", r"hadn't",
              r"shouldn't", r"wouldn't", r"couldn't", r"fail(?:s|ed|ing)?\s+to", r"unable", r"lack(?:s|ed|ing)?", r"absence\s+of", r"absent", r"neither", r"rarely", r"hardly", r"barely", r"scarcely", r"un(?:likely|changed|affected|related|clear|known|significant)", r"insignificant", r"non-?significant"])
NEG_ZH = re.compile(r"不|没有|没|无|未|非|否|勿|别|莫|缺乏|缺少|并非|不能|无法|从未|毫无")
QUANT_CLASSES = [("universal", wre([r"all", r"every", r"everywhere", r"each", r"always", r"entire(?:ly)?", r"whole", r"全部", r"所有", r"每", r"一切", r"任何", r"总是", r"始终"])),
                 ("existential", wre([r"some", r"several", r"certain", r"a\s+few", r"part\s+of", r"部分", r"一些", r"某些", r"若干", r"有的"])),
                 ("majority", wre([r"most", r"majority", r"mostly", r"mainly", r"main", r"largely", r"大多数", r"多数", r"主要", r"大部分", r"绝大部分"])),
                 ("many", wre([r"many", r"numerous", r"multiple", r"a\s+lot\s+of", r"lots\s+of", r"plenty\s+of", r"a\s+great\s+deal\s+of", r"a\s+(?:large|great)\s+number\s+of", r"众多", r"许多", r"大量", r"很多"])),
                 ("minority", wre([r"few", r"little", r"rarely", r"seldom", r"少数", r"极少", r"很少", r"少量"])),
                 ("exclusive", wre([r"only", r"solely", r"merely", r"exclusively", r"alone", r"仅", r"只", r"仅仅", r"唯一", r"只有"]))]
BOUND = re.compile(r"(?<![\w-])(?:at\s+least|at\s+most|no\s+more\s+than|no\s+less\s+than|no\s+fewer\s+than|up\s+to|more\s+than|less\s+than|fewer\s+than|greater\s+than|lower\s+than|higher\s+than|smaller\s+than|larger\s+than|exceed(?:s|ed|ing)?|approximately|roughly|exactly|precisely|approx\.|nearly|almost"
                   r"|(?:over|under|below|above|about|around)(?=\s+(?:pH\s*)?(?:[\d\u2983]|(?:one|two|three|four|five|six|seven|eight|nine|ten|twenty|thirty|forty|fifty|hundred|thousand|half)\b))"
                   r"|约|大约|至少|至多|最多|最少|超过|不足|不超过|不少于|近|几乎|恰好|正好)(?![\w-])", re.I)
# hedge / booster ladder: rank 0 speculative .. 4 certain
STRENGTH = {0: wre([r"may", r"might", r"could", r"possibly", r"perhaps", r"potentially", r"conceivabl[ey]", r"presumably", r"speculat\w+", r"hypothesi[sz]e[sd]?", r"or\s+even", r"可能", r"或许", r"也许", r"大概", r"推测", r"假设"]),
            1: wre([r"can", r"suggest(?:s|ed|ing)?", r"indicat(?:e|es|ed|ing)", r"appear(?:s|ed|ing)?(?:\s+to)?", r"seem(?:s|ed|ing)?", r"tend(?:s|ed|ing)?\s+to", r"likely", r"probabl[ey]", r"unlikely", r"imply|implies|implied", r"似乎", r"倾向", r"提示", r"暗示", r"可能性"]),
            2: wre([r"show(?:s|ed|n)?", r"find|found|finds", r"observ(?:e|es|ed|ing)", r"report(?:s|ed|ing)?", r"reveal(?:s|ed|ing)?", r"expect(?:s|ed)?", r"would", r"发现", r"观察到", r"显示", r"揭示", r"报道"]),
            3: wre([r"demonstrat(?:e|es|ed|ing)", r"confirm(?:s|ed|ing)?", r"establish(?:es|ed|ing)?", r"will", r"must", r"should", r"clear(?:ly)?", r"evident(?:ly)?", r"证实", r"证明", r"表明", r"确认", r"明确", r"必须"]),
            4: wre([r"prov(?:e|es|ed|en|ing)", r"definitive(?:ly)?", r"undoubted(?:ly)?", r"certain(?:ly)?", r"obvious(?:ly)?", r"unquestionabl[ey]", r"without\s+(?:a\s+)?doubt", r"conclusive(?:ly)?", r"无疑", r"显然", r"毫无疑问", r"必然", r"一定", r"确凿"])}
SIGNIFICANT = wre([r"significant(?:ly)?", r"显著", r"明显", r"显著性"])
CAUSAL = wre([r"play(?:s|ed|ing)?\s+(?:an?\s+)?(?:\w+\s+)?role", r"role\s+in", r"cause[sd]?", r"causing", r"causal(?:ly)?", r"lead(?:s|ing)?\s+to", r"led\s+to", r"result(?:s|ed|ing)?\s+in", r"due\s+to", r"because(?:\s+of)?", r"since(?!\s+(?:19|20)\d{2})", r"as\s+a\s+result\s+of", r"therefore", r"thus", r"hence", r"consequently", r"as\s+a\s+result", r"so\s+that", r"attributable\s+to", r"responsible\s+for",
              r"induc(?:e|es|ed|ing)", r"driv(?:e|es|en|ing)", r"trigger(?:s|ed|ing)?", r"produc(?:e|es|ed|ing)", r"owing\s+to", r"contribut(?:e|es|ed|ing)\s+to", r"effect\s+of", r"impact\s+of", r"influenc(?:e|es|ed|ing)", r"导致", r"引起", r"造成", r"因为", r"由于", r"因此", r"所以", r"从而", r"使得", r"归因于"])
CORREL = wre([r"associat(?:e|es|ed|ion|ions)\s*(?:with)?", r"correlat(?:e|es|ed|ion|ions)", r"link(?:s|ed)?\s+to", r"related\s+to", r"relationship", r"co-?occur(?:s|red|rence)?", r"consistent\s+with", r"covar(?:y|ies)", r"相关", r"关联", r"联系", r"一致"])
COND = wre([r"if", r"unless", r"whenever", r"when", r"provided\s+that", r"only\s+if", r"as\s+long\s+as", r"in\s+case", r"assuming", r"given\s+that", r"otherwise", r"whether", r"once", r"如果", r"若", r"假如", r"除非", r"只要", r"当", r"假设", r"一旦", r"否则", r"倘若"])
UP = wre([r"increas(?:e|es|ed|ing)", r"ris(?:e|es|en|ing)|rose", r"grow(?:s|n|th|ing)?|grew", r"improv(?:e|es|ed|ing|ement)", r"higher", r"greater", r"larger", r"more", r"enhanc(?:e|es|ed|ing)", r"boost(?:s|ed|ing)?", r"elevat(?:e|es|ed|ing)", r"rais(?:e|es|ed|ing)", r"gain(?:s|ed)?", r"outperform(?:s|ed|ing)?", r"exceed(?:s|ed|ing)?", r"surpass(?:es|ed|ing)?",
          r"better", r"faster", r"upregulat\w+", r"promot(?:e|es|ed|ing)", r"strengthen\w*", r"增加", r"升高", r"提高", r"增强", r"上升", r"增大", r"优于", r"超过", r"更高", r"更大", r"更多", r"改善", r"促进", r"增长"])
DOWN = wre([r"worsen(?:s|ed|ing)?", r"los(?:e|es|t|ing)", r"loss(?:es)?\s+of", r"decreas(?:e|es|ed|ing)", r"declin(?:e|es|ed|ing)", r"drop(?:s|ped|ping)?", r"reduc(?:e|es|ed|ing|tion)", r"lower", r"smaller", r"fewer", r"less", r"worse", r"slower", r"degrad(?:e|es|ed|ing)", r"diminish\w*", r"fall(?:s|en|ing)?|fell", r"downregulat\w+", r"suppress(?:es|ed|ing)?", r"inhibit(?:s|ed|ing)?", r"weaken\w*",
            r"attenuat\w+", r"降低", r"下降", r"减少", r"减弱", r"抑制", r"更低", r"更小", r"更少", r"劣于", r"恶化", r"减小"])
COMPARE = wre([r"than", r"compared\s+(?:to|with)", r"versus", r"vs\.?", r"relative\s+to", r"较", r"比", r"相比", r"相对于"])
ABBR_RE = re.compile(r"\b(?:[A-Z][A-Z0-9]{1,}[a-z]?|[A-Z][a-z]+[A-Z]\w*|[A-Za-z]+-\d+[A-Za-z]*|[a-z]+[A-Z]\w*|p-value|[A-Z][a-z]?\d+)\b")
# strong claims words that are claims about novelty / quality, not style
SIGNALS = ("negation", "quantifier", "bound", "strength", "significant", "causal", "correlational", "conditional", "direction", "comparison")


def count(rx, text):
    return [re.sub(r"\s+", " ", m.group(0).lower()) for m in rx.finditer(text)]


def strip_protected(text):
    t = text
    for s, e, _ in reversed(protected_spans(text)):
        t = t[:s] + " " + t[e:]
    return t


MARKER_WORDS = ["because", "therefore", "however", "although", "though", "cannot", "without", "unless", "whereas", "while", "thus", "hence", "consequently", "never", "neither", "caused", "causes", "increase", "decrease", "increased", "decreased", "significant", "significantly",
                "suggest", "suggests", "indicate", "indicates", "demonstrate", "demonstrates", "probably", "possibly", "perhaps", "potentially", "approximately", "associated", "correlated", "should", "would", "might", "whether", "unlikely", "likely", "obviously", "clearly"]


def fix_typos(text):
    """near-miss spellings of marker words ('beacuse', 'incresed') count as the marker: a correction of the typo must not look like a new claim"""
    def rep(m):
        w = m.group(0)
        lw = w.lower()
        if len(lw) < 6 or lw in MARKER_WORDS:
            return w
        c = difflib.get_close_matches(lw, MARKER_WORDS, n=1, cutoff=0.84)
        return c[0] if c and abs(len(c[0]) - len(lw)) <= 1 else w
    return re.sub(r"[A-Za-z]{6,}", rep, text)


def inventory(text, fix=False):
    t = re.sub(r"\bcan\s+not\b", "cannot", strip_protected(text), flags=re.I)
    if fix:
        t = fix_typos(t)
    zh = nlib.cjk_ratio(text) > 0.3
    inv = {}
    inv["protected"] = Counter(norm_protected(x[2]) for x in protected_spans(text))
    inv["latex"] = [m.group(1) for m in LATEX_CMD.finditer(text) if not re.match(r"(?:%s)$" % CITE_CMDS, m.group(1))]
    inv["numbers"] = numbers_of(text)
    inv["negation"] = Counter(count(NEG_ZH if zh else NEG_EN, t) + (count(NEG_ZH, t) if not zh else []))
    inv["quantifier"] = Counter(c for c, rx in QUANT_CLASSES for _ in rx.finditer(t))
    inv["bound"] = Counter(count(BOUND, t))
    st = []
    for rank, rx in STRENGTH.items():
        st += [(rank, w) for w in count(rx, t)]
    inv["strength"] = st
    inv["significant"] = Counter(count(SIGNIFICANT, t))
    inv["causal"] = Counter(count(CAUSAL, t))
    inv["correlational"] = Counter(count(CORREL, t))
    inv["conditional"] = Counter(count(COND, t))
    td = re.sub(r"\bmore\s+and\s+more\b|\bmore\s+or\s+less\b|\b(?:no|any|once|much|many|one)\s+more\b|\b(?:more|less|fewer|greater|higher|lower|larger|smaller)\s+than\b(?=\s+[\d\u2983])", " ", t, flags=re.I)
    inv["up"], inv["down"] = len(count(UP, td)), len(count(DOWN, td))
    inv["comparison"] = len(count(COMPARE, t))
    inv["abbr"] = Counter(ABBR_RE.findall(t))
    return inv


def tok(text):
    t = strip_protected(text)
    return re.findall(r"[A-Za-z0-9]+(?:['’-][A-Za-z0-9]+)*|[㐀-鿿]|[^\sA-Za-z0-9㐀-鿿]", t)


def edit_ratio(a, b):
    """share of tokens that changed between two texts (0 = identical, 1 = nothing in common)"""
    ta, tb = tok(a), tok(b)
    if not ta and not tb:
        return 0.0
    sm = difflib.SequenceMatcher(None, ta, tb, autojunk=False)
    same = sum(bl.size for bl in sm.get_matching_blocks())
    return 1.0 - 2.0 * same / (len(ta) + len(tb))


def content_set(text):
    return {nlib.stem(w) for w in re.findall(r"[a-z]{3,}", strip_protected(text).lower()) if w not in nlib.STOP}


def diffc(a, b):
    """(removed, added) of two Counters"""
    return a - b, b - a


def fmt(c):
    return ", ".join(("%s x%d" % (k, v)) if v > 1 else str(k) for k, v in c.items())


def issue(sev, kind, detail):
    return {"severity": sev, "kind": kind, "detail": detail}


def verify_edit(orig, rev, allow_rewrite=False, doc_content=None):
    """-> list of issues. ERROR = the meaning-bearing wording changed; WARN = review; rev == orig gives []"""
    if orig == rev:
        return []
    a, b = inventory(orig, fix=True), inventory(rev)
    out = []
    r, ad = diffc(a["protected"], b["protected"])
    if r or ad:
        out.append(issue("error", "protected_changed", "citations / figure-table-equation references / math / links must stay identical: removed %s; added %s" % (fmt(r) or "-", fmt(ad) or "-")))
    if a["latex"] != b["latex"] and Counter(a["latex"]) != Counter(b["latex"]):
        out.append(issue("warn", "latex_changed", "LaTeX commands differ: %s -> %s" % (a["latex"], b["latex"])))
    r, ad = diffc(a["numbers"], b["numbers"])
    if r or ad:
        out.append(issue("error", "number_changed", "numbers / units differ: removed %s; added %s" % (fmt({"%s%s" % k: v for k, v in r.items()}) or "-", fmt({"%s%s" % k: v for k, v in ad.items()}) or "-")))
    na_, nb_ = sum(a["negation"].values()), sum(b["negation"].values())
    if na_ != nb_:
        out.append(issue("error", "negation_changed", "negation count %d -> %d (%s -> %s): check that scope and truth value are unchanged" % (na_, nb_, fmt(a["negation"]) or "none", fmt(b["negation"]) or "none")))
    r, ad = diffc(a["quantifier"], b["quantifier"])
    hard = {k: v for k, v in r.items() if k != "many"}, {k: v for k, v in ad.items() if k != "many"}
    if hard[0] or hard[1]:
        out.append(issue("error", "quantifier_changed", "quantifier class changed: removed %s; added %s (all / some / most / few / only are different claims)" % (fmt(hard[0]) or "-", fmt(hard[1]) or "-")))
    elif r or ad:
        out.append(issue("warn", "quantity_changed", "'many / numerous / a lot of' added or removed: check that the quantity statement is unchanged"))
    r, ad = diffc(a["bound"], b["bound"])
    if r or ad:
        sameclass = lambda x: re.sub(r"approximately|about|around|roughly|nearly|almost|约|大约|近|几乎", "approx", x)
        ra, aa = Counter(map(sameclass, r.elements())), Counter(map(sameclass, ad.elements()))
        rr, aa2 = diffc(ra, aa)
        if rr or aa2:
            out.append(issue("error", "bound_changed", "bound / approximation wording changed: removed %s; added %s (at least / more than / about / exactly are different statements)" % (fmt(rr) or "-", fmt(aa2) or "-")))
    ha, hb = sum(1 for x in a["strength"] if x[0] <= 1), sum(1 for x in b["strength"] if x[0] <= 1)
    ba, bb = sum(1 for x in a["strength"] if x[0] == 4), sum(1 for x in b["strength"] if x[0] == 4)
    m3a, m3b = sum(1 for x in a["strength"] if x[0] == 3), sum(1 for x in b["strength"] if x[0] == 3)
    ra, rb = sorted(x[0] for x in a["strength"] if x[0] <= 1), sorted(x[0] for x in b["strength"] if x[0] <= 1)
    names = lambda inv: sorted({w for r_, w in inv["strength"] if r_ != 2}) or "none"
    if hb < ha or bb > ba or (m3b > m3a and hb <= ha and ha > 0 and rb != ra):
        out.append(issue("error", "strengthened", "claim strength raised: %s -> %s; keep the original hedge or booster (a hedge was removed or a booster added)" % (names(a), names(b))))
    elif hb > ha or bb < ba:
        out.append(issue("error", "weakened", "claim strength lowered: %s -> %s (a hedge was added or a booster removed)" % (names(a), names(b))))
    elif m3b != m3a or ra != rb:
        out.append(issue("warn", "hedge_changed", "hedge / modal wording differs: %s -> %s" % (names(a), names(b))))
    r, ad = diffc(a["significant"], b["significant"])
    if r or ad:
        out.append(issue("error", "significance_changed", "'significant(ly)' added or removed: %s / %s (in a scientific text it claims statistical significance)" % (fmt(r) or "-", fmt(ad) or "-")))
    ca, cb = sum(a["causal"].values()), sum(b["causal"].values())
    ra_, rb_ = sum(a["correlational"].values()), sum(b["correlational"].values())
    if cb > ca and rb_ <= ra_:
        out.append(issue("error", "causal_added", "causal wording added (%s): association must not become causation" % (fmt(b["causal"] - a["causal"]) or "?")))
    elif cb > ca:
        out.append(issue("warn", "causal_added", "more causal wording (%s) while correlational wording changed: check" % fmt(b["causal"] - a["causal"])))
    elif cb < ca:
        out.append(issue("warn", "causal_removed", "causal wording removed (%s): check that the causal link is still stated" % fmt(a["causal"] - b["causal"])))
    if rb_ < ra_ and cb > ca:
        out.append(issue("error", "correlation_to_causation", "correlational wording (%s) replaced by causal wording" % fmt(a["correlational"] - b["correlational"])))
    r, ad = diffc(a["conditional"], b["conditional"])
    if sum(r.values()) != sum(ad.values()) and (r or ad):
        out.append(issue("error", "conditional_changed", "conditional / temporal-conditional wording changed: removed %s; added %s" % (fmt(r) or "-", fmt(ad) or "-")))
    if (a["up"], a["down"]) != (b["up"], b["down"]):
        inv_ = (b["down"] > a["down"] and b["up"] < a["up"]) or (b["up"] > a["up"] and b["down"] < a["down"]) or (a["up"] + a["down"] > 0 and a["up"] + a["down"] == b["up"] + b["down"] and (a["up"] - a["down"]) * (b["up"] - b["down"]) < 0)
        out.append(issue("error" if inv_ else "warn", "direction_changed", "direction of change differs (increase/improve words %d -> %d; decrease/reduce words %d -> %d)%s" % (a["up"], b["up"], a["down"], b["down"], ": an inverted comparison changes the finding" if inv_ else ": check that no comparison was added or dropped")))
    if a["comparison"] != b["comparison"]:
        out.append(issue("warn", "comparison_changed", "comparison marker count %d -> %d (than / compared with): check what is compared with what" % (a["comparison"], b["comparison"])))
    r, ad = diffc(a["abbr"], b["abbr"])
    if r:
        out.append(issue("warn", "term_dropped", "named terms / abbreviations dropped: %s" % fmt(r)))
    new_terms = [t for t in ad if not doc_content or t not in doc_content]
    if ad and new_terms:
        out.append(issue("warn", "term_added", "named terms / abbreviations not in the original sentence: %s (do they appear elsewhere in the manuscript?)" % ", ".join(new_terms[:4])))
    er = edit_ratio(orig, rev)
    if er > 0.85 and not allow_rewrite:
        out.append(issue("error", "rewrite", "%.0f%% of the tokens changed: this is a rewrite, not a polish; keep the author's wording where it is correct (or give `rewrite: yes` and the reason)" % (100 * er)))
    elif er > 0.6:
        out.append(issue("warn", "heavy_edit", "%.0f%% of the tokens changed: check that each change is needed" % (100 * er)))
    ca_, cb_ = content_set(orig), content_set(rev)
    lost, gained = ca_ - cb_, cb_ - ca_
    if len(ca_) >= 6 and len(lost) / len(ca_) > 0.35 and er <= 0.85:
        out.append(issue("warn", "content_dropped", "content words dropped: %s" % ", ".join(sorted(lost)[:8])))
    if len(gained) >= 3 and len(gained) / max(1, len(cb_)) > 0.35:
        out.append(issue("warn", "content_added", "new content words (not in the original): %s: no new information may be added" % ", ".join(sorted(gained)[:8])))
    return out
