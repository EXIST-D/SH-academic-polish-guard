#!/usr/bin/env python3
"""detect.py - what is wrong or inconsistent in an academic manuscript, found by rules (no model).

Three layers:
  * mechanical errors with a safe, meaning-neutral fix (spacing, punctuation, repeated words, a/an, unambiguous collocations ...): `autofix_sentence`
  * sentence-level issues that need a decision (agreement patterns, uncountable plurals, double connectors, wordiness / translationese, register, over-claiming wording): `scan_sentence`
  * document-level consistency (terminology variants, US / UK spelling, abbreviations defined / used before definition, number and reference formats): `scan_doc`
Every issue says which rule fired, on which text, and what a fix could look like. Rule tables are plain data: extend them for a field or a house style.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict

import nlib
import protect

# ------------------------------------------------------------------------------------------------ masking of protected spans
MASK = "⦃%d⦄"
MASK_RE = re.compile("⦃(\\d+)⦄")


def mask(text):
    spans = protect.protected_spans(text)
    out, last, store = [], 0, []
    for s, e, g in spans:
        out.append(text[last:s])
        out.append(MASK % len(store))
        store.append(g)
        last = e
    out.append(text[last:])
    return "".join(out), store


def unmask(text, store):
    return MASK_RE.sub(lambda m: store[int(m.group(1))], text)


# ------------------------------------------------------------------------------------------------ a / an
A_SOUND_EXC = ("uni", "use", "usu", "uti", "ubi", "euro", "one", "once", "eul", "ewe", "uk", "uro")
AN_UN = {"unimportant", "unintended", "unintentional", "uninformed", "uninteresting", "unidentified", "unimpressive", "unincorporated", "uninterrupted", "uninhabited", "unimaginable", "unimpeded", "uninformative", "unimodified", "unimpaired", "uninfected"}
AN_H = ("hour", "honest", "honor", "honour", "heir", "herb")
VOWEL_LETTERS = set("AEFHILMNORSX")


def an_needed(word):
    """True if the word is pronounced with a vowel sound (so 'an'), False for consonant sound, None if unknown / skip"""
    w = word.strip("()[]\"'")
    if not w or len(w) == 1 and not w.isdigit():
        return None
    if re.fullmatch(r"[A-Z]{2,}[a-z]?s?", w) or re.fullmatch(r"[A-Z]{2,}[0-9-]+\w*", w):  # acronym read letter by letter
        return w[0] in VOWEL_LETTERS
    m = re.match(r"(\d+)", w)
    if m:
        d = m.group(1)
        return d.startswith("8") or d in ("11", "18") or (len(d) in (4, 7, 10) and d.startswith("11")) or (len(d) in (3, 5) and d.startswith("18")) or (len(d) == 2 and d.startswith("8"))
    lw = w.lower()
    if lw in AN_UN:
        return True
    if lw.startswith(AN_H):
        return True
    if lw.startswith(A_SOUND_EXC) and not lw.startswith(("unimport", "uninter", "unident")):
        return False
    if re.match(r"[aeiou]", lw):
        return True
    return False


ART_RE = re.compile(r"(?<![\w⦃])(A|An|a|an)\s+([A-Za-z0-9][\w-]*)")


def fix_articles(text):
    out, applied = [], []
    last = 0
    for m in ART_RE.finditer(text):
        art, nxt = m.group(1), m.group(2)
        need = an_needed(nxt)
        if need is None:
            continue
        right = ("An" if art[0].isupper() else "an") if need else ("A" if art[0].isupper() else "a")
        if right != art:
            out.append(text[last:m.start(1)])
            out.append(right)
            last = m.end(1)
            applied.append((art + " " + nxt, right + " " + nxt))
    out.append(text[last:])
    return "".join(out), applied


# ------------------------------------------------------------------------------------------------ rule tables
# (id, regex, replacement-or-None, message)   auto rules replace; the others suggest
def R(id_, pat, repl, msg, cat="mechanical", sev="low", flags=re.I):
    return {"id": id_, "rx": re.compile(pat, flags), "repl": repl, "msg": msg, "cat": cat, "sev": sev}


AUTO_EN = [
    R("double_space", r"(?<=\S)[ \t]{2,}(?=\S)", " ", "more than one space"),
    R("space_before_punct", r"(?<=[A-Za-z0-9\)⦄])[ \t]+([,;:!?])(?=\s|$)", r"\1", "space before punctuation", flags=0),
    R("space_before_period", r"(?<=[a-z\)⦄])[ \t]+\.(?=\s|$)", ".", "space before the full stop", flags=0),
    R("space_before_comma_nospace_after", r"(?<=[A-Za-z0-9\)\u2984])[ \t]+,(?=[A-Za-z])", ", ", "space before comma and none after", flags=0),
    R("no_space_after_comma", r"(?<=[A-Za-z]),(?=[A-Za-z])", ", ", "missing space after comma", flags=0),
    R("no_space_after_semicolon", r"(?<=[A-Za-z]);(?=[A-Za-z])", "; ", "missing space after semicolon", flags=0),
    R("no_space_after_period", r"(?<=[a-z]{3})\.(?=[A-Z][a-z]{2})", ". ", "missing space after full stop", flags=0),
    R("can_not", r"\bcan\s+not\b(?!\s+only\b)", "cannot", "'can not' is written 'cannot'"),
    R("micro_sign", r"(?<=\d)(\s?)u(M|L|g|m|mol|s)\b", lambda m: m.group(1) + "μ" + m.group(2), "micro prefix written as latin u", flags=0),
    R("space_in_brackets", r"\(\s+(?=\S)", "(", "space after opening bracket", flags=0),
    R("space_in_brackets2", r"(?<=\S)\s+\)", ")", "space before closing bracket", flags=0),
    R("etc_dots", r"\betc\.\.(?!\.)", "etc.", "double full stop after etc."),
    R("double_comma", r",\s*,", ",", "double comma", flags=0),
    R("ie_eg_period", r"\b(i\.e|e\.g)(?=[\s,])", r"\1.", "i.e. / e.g. needs the final full stop"),
    R("informations", r"\b(information|equipment|knowledge|software|hardware|furniture|advice)s\b", r"\1", "uncountable noun used in the plural"),
    R("discuss_about", r"\bdiscuss(es|ed|ing)?\s+about\b", lambda m: "discuss" + (m.group(1) or ""), "'discuss' takes a direct object"),
    R("mention_about", r"\bmention(s|ed|ing)?\s+about\b", lambda m: "mention" + (m.group(1) or ""), "'mention' takes a direct object"),
    R("emphasize_on", r"\bemphasi([sz]e[sd]?|ing)\s+on\b", lambda m: "emphasi" + m.group(1), "'emphasize' takes a direct object"),
    R("other_hand", r"\bin\s+the\s+other\s+hand\b", "on the other hand", "fixed phrase: on the other hand"),
    R("contrary", r"\bin\s+the\s+contrary\b", "on the contrary", "fixed phrase: on the contrary"),
    R("can_able", r"\bcan\s+able\s+to\b", "can", "'can able to'"),
    R("different_with", r"\bdifferent\s+with\b", "different from", "collocation: different from"),
    R("similar_with", r"\bsimilar\s+with\b", "similar to", "collocation: similar to"),
    R("depend_of", r"\bdepends?\s+(of|from)\b", lambda m: "depend" + ("s" if m.group(0).lower().startswith("depends") else "") + " on", "collocation: depend on"),
    R("reason_because", r"\bthe\s+reason\s+(is|was)\s+because\b", lambda m: "the reason " + m.group(1) + " that", "'the reason is because'"),
    R("amongst_fix", r"\bin\s+a\s+nutshell\b", "in summary", "informal idiom", cat="register"),
]
# suggestions only (the fix changes wording, so the author or the model decides)
SUGGEST_EN = [
    R("agree_pl_subject", r"\b(results|data|findings|experiments|samples|methods|models|algorithms|studies|patients|participants|variables|parameters|properties|features|values|measurements|approaches|tests|effects|levels|analyses|differences|changes|replicates)\s+(?:of|from|in|for|on)\s+[\w\s,-]{1,40}?\s+(is|was|has|does|shows|indicates|suggests|demonstrates|reveals|confirms|provides|exhibits|depends|increases|decreases|improves|requires)\b",
      None, "possible subject-verb disagreement (plural subject with a singular verb after a prepositional phrase)", "grammar", "med"),
    R("agree_sg_head_pl_verb", r"\b(area|amount|level|rate|number|effect|value|size|degree|ratio|fraction|proportion|concentration|expression|activity|percentage|length|mean|average)\s+(?:of|on|in|for|at)\s+[\w\s,.-]{1,40}?\s+(were|are|have)\b",
      None, "singular head noun with a plural verb after a prepositional phrase", "grammar", "med"),
    R("agree_pl_subject2", r"\b(results|findings|experiments|samples|methods|models|algorithms|studies|patients|participants|variables|parameters|properties|features|values|measurements|approaches)\s+(is|was|has|does|shows|indicates|suggests|demonstrates|reveals|confirms|provides|exhibits|depends|increases|decreases|improves|requires)\b",
      None, "plural subject with a singular verb", "grammar", "high"),
    R("agree_sg_subject", r"\b(result|finding|method|model|algorithm|study|experiment|analysis|approach|process|system|figure|table|sample|patient|parameter|variable)\s+(are|were|have|do|show|indicate|suggest|demonstrate|provide|exhibit|depend|require)\b",
      None, "singular subject with a plural verb (unless 'result' etc. is a modifier)", "grammar", "med"),
    R("this_plural", r"\b(this|that)\s+(results|methods|data|experiments|studies|samples|models|approaches|algorithms|findings|parameters|features|variables)\b", None, "this / that with a plural noun (these / those?)", "grammar", "high"),
    R("these_singular", r"\b(these|those)\s+(result|method|experiment|study|sample|model|approach|algorithm|finding|kind|type|parameter|feature|variable)\b", None, "these / those with a singular noun", "grammar", "high"),
    R("less_count", r"\bless\s+(samples|participants|patients|parameters|layers|errors|images|features|experiments|data\s+points|subjects|cases|steps|iterations)\b", None, "'less' with a countable plural (fewer?)", "grammar", "med"),
    R("much_count", r"\bmuch\s+(samples|participants|patients|parameters|layers|errors|images|features|experiments|studies|methods|models)\b", None, "'much' with a countable plural (many?)", "grammar", "high"),
    R("article_uncountable", r"\ban?\s+(information|equipment|knowledge|evidence|advice|research|software|feedback|progress)\b", None, "article before an uncountable noun", "grammar", "med"),
    R("perfect_past", r"\b(?:has|have)\s+been\s+\w+(?:ed|en)\s+in\s+(?:19|20)\d{2}\b", None, "present perfect with a definite past year (simple past?)", "grammar", "med"),
    R("consist_passive", r"\bis\s+consisted\s+of\b|\bare\s+consisted\s+of\b", None, "'consist of' is not used in the passive", "grammar", "high"),
    R("composed_by", r"\b(?:is|are)\s+composed\s+by\b", None, "composed of", "grammar", "med"),
    R("comprise_of", r"\bcompris(?:e|es|ed|ing)\s+of\b", None, "'comprise' takes no 'of' (consist of / comprise)", "grammar", "med"),
    R("double_connector", r"\b(?:although|though)\b[^.;]{3,120}?,\s*but\b|\bbecause\b[^.;]{3,120}?,\s*(?:so|therefore|thus)\b|\bsince\b[^.;]{3,120}?,\s*(?:so|therefore)\b", None, "two connectors for one relation (although ... but / because ... so)", "wording", "med"),
    R("not_only_but", r"\bnot\s+only\b[^.;]{3,100}?\bbut\b(?!\s+also)", None, "'not only ... but' without 'also' (check parallel structure)", "wording", "low"),
    R("dangling", r"^(?:Using|Applying|Considering|Based on|By using|Compared with|Comparing)\s[^,]{3,80},\s+(?:the|a|an)\s+\w+(?:\s+\w+)?\s+(?:was|were|is|are)\b", None, "possible dangling modifier (the subject of the main clause is not the doer of the opening phrase)", "grammar", "low"),
    R("missing_subject", r"^(?:In this paper|In this study|In this work),?\s+(?:is|are|was|were)\b", None, "sentence without subject", "grammar", "high"),
    R("which_comma", r",\s+which\s+(?:is|are|was|were)\s+\w+\s+(?:by|in|for)\b[^.]{60,}", None, "long relative clause: consider splitting the sentence", "clarity", "low"),
]
WORDY_EN = [
    ("with the development of", "As X develops / Advances in X", "wording", "med"), ("more and more", "increasingly", "wording", "med"),
    ("plays? an important role in", "is important for / contributes to (say what it does)", "wording", "med"), ("it is well known that", "delete, or cite the source", "wording", "med"),
    ("as we all know|as is known to all|as everyone knows", "delete, or cite the source", "wording", "high"), ("in order to", "to", "concision", "low"), ("due to the fact that", "because", "concision", "med"),
    ("a large number of", "many", "concision", "low"), ("a great deal of", "much", "concision", "low"), ("has the ability to|have the ability to", "can", "concision", "med"), ("is able to|are able to", "can", "concision", "low"),
    ("so as to", "to", "concision", "low"), ("take(?:s|n)? into consideration", "consider", "concision", "med"), ("carry out", "perform / conduct", "wording", "low"), ("it can be seen (?:from [^,.]{1,40} )?that", "Figure X shows that ...", "wording", "med"),
    ("according to [^,.]{1,60}, it can be (?:seen|found|concluded) that", "state the result directly", "wording", "high"), ("in a word", "in summary", "wording", "med"), ("in recent years,? [^.]{0,80}(?:has|have) attracted (?:more and more|much|great) attention", "say what changed and cite it", "wording", "med"),
    ("pay(?:s|ing)? (?:much|great|more) attention to", "focus on / investigate", "wording", "med"), ("nowadays", "currently / at present", "register", "med"), ("with the rapid development of", "Advances in X", "wording", "med"),
    ("is widely used in many fields", "name the fields", "wording", "med"), ("have a good effect on|has a good effect on", "improve / benefit", "wording", "med"), ("in the process of", "while / during", "concision", "low"), ("there (?:is|are) (?:a lot of|lots of)", "state the quantity", "register", "med"),
    ("be used to do|be used to doing", "check 'used to' structure", "grammar", "med"), ("on the basis of", "based on", "concision", "low"), ("at the same time of", "while", "wording", "med"), ("for the purpose of", "to / for", "concision", "low"), ("in terms of", "check whether a simpler preposition works", "concision", "low"),
]
REGISTER_EN = [
    (r"\b(?:very|quite|really|extremely|pretty|rather(?!\s+than))\s+(?=[a-z]+\b)", "intensifier: quantify or drop", "register", "low"), (r"\ba lot of\b|\blots of\b|\btons of\b|\bkind of\b|\bsort of\b", "informal quantifier", "register", "med"),
    (r"\b(?:gonna|wanna|gotta|kinda|sorta|ok|okay|stuff|guys)\b", "informal word", "register", "high"), (r"\b(?:get|gets|got|getting)\b(?!\s+(?:better|worse|larger|smaller|higher|lower|close|closer))", "informal verb: obtain / receive / become", "register", "low"),
    (r"\b(?:big|huge|tiny)\b", "vague size word: give the size", "register", "low"), (r"\b(?:good|bad|nice)\s+(?:results?|performance|effects?|properties)\b", "vague evaluative adjective: give the measure", "register", "med"), (r"\bthings?\b", "vague noun", "register", "low"),
    (r"\b(?:don't|doesn't|didn't|can't|won't|isn't|aren't|wasn't|weren't|hasn't|haven't|wouldn't|shouldn't|couldn't|it's|that's|there's|let's|what's|we're|we've|we'll|they're|they've|i'm|i've|you're)\b", "contraction in formal writing", "register", "med"),
    (r"!(?=\s|$)", "exclamation mark in academic text", "register", "med"), (r"\byou\b|\byour\b", "second person in academic text", "register", "med"), (r"\band so on\b|\band so forth\b", "vague list ending: say what else", "register", "low"),
]
CLAIM_EN = [
    (r"\b(?:perfect(?:ly)?|revolutionary|groundbreaking|unprecedented|amazing|remarkable|excellent|outstanding|superb|magnificent|breakthrough)\b", "promotional wording"), (r"\b(?:best|optimal)\b(?!\s+(?:fit|practice|performing))", "superlative: needs a comparison"),
    (r"\b(?:always|never|completely|totally|fully|entirely|undoubtedly|obviously|certainly|definitely|absolutely|undeniabl[ey])\b", "absolute wording"), (r"\bfor the first time\b|\bthe first (?:to|study|paper|work)\b|\bnovel\b", "priority / novelty claim: needs support"),
    (r"\b(?:prove[sd]?|proof)\b", "'prove' is strong: show / demonstrate / suggest?"), (r"\b(?:solve[sd]?|eliminat(?:e|es|ed))\s+(?:the|this|all)\b", "absolute claim"),
]
FIRST_PERSON = re.compile(r"\b(?:I|my|me|mine)\b")
# Chinese
AUTO_ZH = [
    R("zh_comma", r"(?<=[㐀-鿿]),(?=\s*[㐀-鿿])", "，", "半角逗号用在中文句子里", cat="mechanical", flags=0),
    R("zh_semicolon", r"(?<=[㐀-鿿]);(?=\s*[㐀-鿿])", "；", "半角分号用在中文句子里", cat="mechanical", flags=0),
    R("zh_colon", r"(?<=[㐀-鿿]):(?=\s*[㐀-鿿])", "：", "半角冒号用在中文句子里", cat="mechanical", flags=0),
    R("zh_period_end", r"(?<=[㐀-鿿])\.(?=\s*$)", "。", "半角句号结束中文句子", cat="mechanical", flags=0),
    R("zh_question", r"(?<=[㐀-鿿])\?(?=\s*$|\s*[㐀-鿿])", "？", "半角问号用在中文句子里", cat="mechanical", flags=0),
    R("zh_dup_particle", r"([的了和在是与及])\1(?![\w])", r"\1", "助词/连词重复", cat="mechanical", flags=0),
    R("zh_dup_punct", r"([，。；：！？、])\1+", r"\1", "标点重复", cat="mechanical", flags=0),
    R("zh_space_between", r"(?<=[㐀-鿿])[ \t]+(?=[㐀-鿿])", "", "汉字之间多余空格", cat="mechanical", flags=0),
    R("zh_ji_yu", r"基于([^，。；]{2,30})的基础上", r"在\1的基础上", "「基于…的基础上」杂糅", cat="grammar", flags=0),
]
SUGGEST_ZH = [(r"进行了?[^，。；]{0,6}(?:研究|分析|讨论|探讨|调查|实验|评估|比较)", "名词化：「进行研究/分析」可改为动词「研究/分析」", "wording", "med"), (r"众所周知|不言而喻|毋庸置疑|显而易见", "绝对化/套话：删除或给出依据", "wording", "med"),
              (r"随着[^，。]{2,20}的(?:快速|不断|飞速)?发展", "套话开头：说明具体变化并给出依据", "wording", "med"), (r"(?:由于|因为)[^。；]{2,60}，所以", "「由于…所以」双重连接词", "wording", "med"), (r"不难(?:发现|看出|得出)|可以看出|可以发现", "「可以看出」可直接陈述结果", "wording", "low"),
              (r"[挺特超老]\s*[好大多快慢高低强弱]|搞定|弄出|咱们|牛[的]|很多很多|非常非常", "口语化", "register", "high"), (r"起到了?[^，。；]{0,4}重要的?作用|具有[^，。；]{0,8}的作用", "套话：说明具体作用", "wording", "med"),
              (r"完美|革命性|颠覆性|史无前例|绝对|彻底解决|一定|必然|永远|从不", "绝对化/宣传化措辞：需要证据支撑，润色不得擅自加强或削弱", "claim_strength", "med"), (r"被[^，。；]{1,15}所", "「被…所」欧化句式", "wording", "low"),
              (r"关于[^，。；]{2,20}的(?:问题|研究)进行", "欧化长定语/名词化", "wording", "med")]


# ------------------------------------------------------------------------------------------------ sentence level
def issue(rule, cat, sev, start, end, text, msg, suggestion=None, auto=False):
    return {"rule": rule, "cat": cat, "sev": sev, "start": start, "end": end, "text": text, "why": msg, "suggestion": suggestion, "auto": auto}


def scan_sentence(text, lang="en", genre="general"):
    """-> list of issues of one sentence. Protected spans (citations, math, references, URLs) are masked: nothing inside them is judged."""
    masked, store = mask(text)
    out = []
    if lang == "zh":
        for r in AUTO_ZH:
            for m in r["rx"].finditer(masked):
                out.append(issue(r["id"], r["cat"], r["sev"], m.start(), m.end(), unmask(m.group(0), store), r["msg"], None, True))
        for pat, msg, cat, sev in SUGGEST_ZH:
            for m in re.finditer(pat, masked):
                out.append(issue("zh_" + cat, cat, sev, m.start(), m.end(), unmask(m.group(0), store), msg))
        return sorted(out, key=lambda x: x["start"])
    for r in AUTO_EN:
        for m in r["rx"].finditer(masked):
            sug = r["repl"](m) if callable(r["repl"]) else m.expand(r["repl"])
            if sug == m.group(0):
                continue
            out.append(issue(r["id"], r["cat"], r["sev"], m.start(), m.end(), unmask(m.group(0), store), r["msg"], unmask(sug, store), True))
    for m in re.finditer(r"\b(\w+)\s+\1\b", masked, re.I):
        if m.group(1).lower() not in ("had", "that", "is", "very", "far", "so", "no", "bye", "to", "can", "do", "ha"):
            out.append(issue("repeated_word", "mechanical", "low", m.start(), m.end(), m.group(0), "repeated word", m.group(1), True))
    fixed, ap = fix_articles(masked)
    for was, now in ap:
        k = masked.find(was)
        out.append(issue("a_an", "mechanical", "low", max(k, 0), max(k, 0) + len(was), was, "a / an chosen by the sound of the next word", now, True))
    for r in SUGGEST_EN:
        for m in r["rx"].finditer(masked):
            if r["id"] == "agree_pl_subject" and re.search(r"(?:of|in|on|for|with|by|from|number|amount|series|set|range|variety|part|type|kind|rest|many|most|some|each|all)\s+(?:the\s+|these\s+|those\s+|\w+\s+)?$", masked[max(0, m.start() - 24):m.start()], re.I):
                continue
            out.append(issue(r["id"], r["cat"], r["sev"], m.start(), m.end(), unmask(m.group(0), store), r["msg"]))
    for pat, sug, cat, sev in WORDY_EN:
        for m in re.finditer(r"(?<![\w-])(?:%s)(?![\w-])" % pat, masked, re.I):
            out.append(issue("wordy", cat, sev, m.start(), m.end(), unmask(m.group(0), store), "wordy / translationese pattern", sug))
    for pat, msg, cat, sev in REGISTER_EN:
        for m in re.finditer(pat, masked, re.I):
            out.append(issue("register", cat, sev, m.start(), m.end(), unmask(m.group(0), store), msg))
    for pat, msg in CLAIM_EN:
        for m in re.finditer(pat, masked, re.I):
            out.append(issue("claim_wording", "claim_strength", "med", m.start(), m.end(), unmask(m.group(0), store), msg + " (do not weaken or strengthen on your own: flag for the author)"))
    if genre in ("journal", "abstract", "thesis") and FIRST_PERSON.search(masked):
        m = FIRST_PERSON.search(masked)
        out.append(issue("person", "register", "low", m.start(), m.end(), m.group(0), "first person singular in a %s: 'we' (several authors) / the passive / 'this thesis' as the genre prefers" % genre))
    if genre in ("journal", "abstract") and re.search(r"\b(?:I|we)\s+(?:think|feel|believe|guess)\b", masked, re.I):
        m = re.search(r"\b(?:I|we)\s+(?:think|feel|believe|guess)\b", masked, re.I)
        out.append(issue("opinion_verb", "register", "med", m.start(), m.end(), m.group(0), "opinion verb: state the finding and its evidence instead"))
    if masked.count("(") != masked.count(")") or masked.count('"') % 2 or masked.count("“") != masked.count("”"):
        out.append(issue("unbalanced", "mechanical", "med", 0, len(masked), text[:50], "unbalanced brackets or quotation marks"))
    if re.match(r"[a-z]", masked.strip("⦃⦄ 0123456789(").strip()[:1] or "A") and not re.match(r"^(?:e\.g|i\.e|et\s+al|[a-z]+\d)", masked.strip()):
        out.append(issue("lowercase_start", "mechanical", "low", 0, 1, masked[:20], "sentence starts with a lower-case letter"))
    return sorted(out, key=lambda x: x["start"])


def autofix_sentence(text, lang="en", only=None):
    """apply the safe mechanical fixes -> (new_text, [{rule, from, to}])"""
    masked, store = mask(text)
    applied = []
    cur = masked
    rules = AUTO_ZH if lang == "zh" else AUTO_EN
    for r in rules:
        if only and r["id"] not in only:
            continue
        if r["cat"] not in ("mechanical", "grammar", "register") or (lang == "en" and r["id"] == "amongst_fix"):
            continue
        def rep(m, r=r):
            new = r["repl"](m) if callable(r["repl"]) else m.expand(r["repl"])
            if new != m.group(0):
                applied.append({"rule": r["id"], "from": unmask(m.group(0), store), "to": unmask(new, store)})
            return new
        cur = r["rx"].sub(rep, cur)
    if lang == "en":
        def rep_rep(m):
            if m.group(1).lower() in ("had", "that", "is", "very", "far", "so", "no", "bye", "to", "can", "do", "ha"):
                return m.group(0)
            applied.append({"rule": "repeated_word", "from": m.group(0), "to": m.group(1)})
            return m.group(1)
        cur = re.sub(r"\b(\w+)\s+\1\b", rep_rep, cur, flags=re.I)
        cur, ap = fix_articles(cur)
        applied += [{"rule": "a_an", "from": a, "to": b} for a, b in ap]
    return unmask(cur, store), applied


# ------------------------------------------------------------------------------------------------ document level
US_UK = [("color", "colour"), ("behavior", "behaviour"), ("center", "centre"), ("modeling", "modelling"), ("modeled", "modelled"), ("labeled", "labelled"), ("labeling", "labelling"), ("fiber", "fibre"), ("defense", "defence"), ("gray", "grey"), ("catalog", "catalogue"),
         ("meter", "metre"), ("liter", "litre"), ("favor", "favour"), ("neighbor", "neighbour"), ("flavor", "flavour"), ("honor", "honour"), ("labor", "labour"), ("traveled", "travelled"), ("fulfill", "fulfil"), ("enrollment", "enrolment"), ("aluminum", "aluminium"),
         ("sulfur", "sulphur"), ("tumor", "tumour"), ("hemoglobin", "haemoglobin"), ("estrogen", "oestrogen"), ("anemia", "anaemia"), ("pediatric", "paediatric"), ("esthetic", "aesthetic"), ("judgment", "judgement"), ("analog", "analogue"), ("dialog", "dialogue"),
         ("signaling", "signalling"), ("signaled", "signalled"), ("cancelation", "cancellation"), ("skeptic", "sceptic"), ("maneuver", "manoeuvre"), ("artifact", "artefact"), ("mold", "mould"), ("plow", "plough"), ("draft", "draught")]
ISE_EXC = set("""rise raise advise revise supervise exercise comprise compromise enterprise otherwise promise surprise precise concise expertise premise merchandise devise disguise franchise improvise televise wise noise poise praise arise
paradise bruise cruise treatise demise excise incise likewise clockwise advertise despise apprise chastise circumcise anise raisin""".split())
STYLE_RE = re.compile(r"\b([A-Za-z]{3,})(iz|is)(e|es|ed|ing|ation|ations|er|ers)\b", re.I)
YSE_RE = re.compile(r"\b([A-Za-z]{3,})(yz|ys)(e|es|ed|ing)\b", re.I)


def spelling_style(word):
    """'US' / 'UK' if the word carries a US / UK spelling convention (-ize/-ise, -yze/-yse, table words), else None"""
    w = word.lower()
    m = STYLE_RE.fullmatch(w)
    if m and (m.group(1) + "is" + m.group(3)) not in ISE_EXC and (m.group(1) + "ise") not in ISE_EXC and w not in ISE_EXC:
        return "US" if m.group(2) == "iz" else "UK"
    m = YSE_RE.fullmatch(w)
    if m:
        return "US" if m.group(2) == "yz" else "UK"
    for us, uk in US_UK:
        if re.fullmatch(re.escape(us) + r"(?:s|d|r|rs|ing|ed|es)?", w):
            return "US"
        if re.fullmatch(re.escape(uk) + r"(?:s|d|r|rs|ing|ed|es)?", w):
            return "UK"
    return None


def convert_spelling(word, to):
    """convert one word to the 'US' or 'UK' convention (None if it already has it or is not a style word)"""
    st = spelling_style(word)
    if not st or st == to:
        return None
    w = word.lower()
    m = STYLE_RE.fullmatch(w)
    if m:
        new = m.group(1) + ("iz" if to == "US" else "is") + m.group(3)
    else:
        m = YSE_RE.fullmatch(w)
        if m:
            new = m.group(1) + ("yz" if to == "US" else "ys") + m.group(3)
        else:
            new = None
            for us, uk in US_UK:
                a, b = (uk, us) if to == "US" else (us, uk)
                mm = re.fullmatch(re.escape(a) + r"(s|d|r|rs|ing|ed|es)?", w)
                if mm:
                    new = b + (mm.group(1) or "")
                    break
            if not new:
                return None
    return match_case(word, new)


def match_case(src, new):
    if src.isupper() and len(src) > 1:
        return new.upper()
    if src[:1].isupper():
        return new[:1].upper() + new[1:]
    return new


def norm_term(s):
    s = re.sub(r"[-‐-―_/]", " ", s.lower())
    s = re.sub(r"[^\w\s]", "", s)
    toks = [t[:-1] if len(t) > 3 and t.endswith("s") and not t.endswith(("ss", "us", "is")) else t for t in s.split()]
    return "".join(toks)


STOPT = set(nlib.STOP) | {"has", "have", "had", "do", "does", "did", "there", "here", "how", "why", "all", "any", "some", "very", "well", "much", "many", "only", "just"}


def term_candidates(sentences):
    """n-grams (1-3 words) that occur in at least two surface forms differing only in case / hyphen / spacing / plural"""
    forms = defaultdict(lambda: defaultdict(list))   # key -> surface -> [sentence ids]
    for sid, text in sentences:
        masked, store = mask(text)
        masked = re.sub(r"⦃\d+⦄", " ", masked)
        toks = list(re.finditer(r"[A-Za-z][A-Za-z0-9]*(?:[-‐][A-Za-z0-9]+)*", masked))
        for n in (1, 2, 3):
            for i in range(len(toks) - n + 1):
                seg = toks[i:i + n]
                if any(masked[seg[j].end():seg[j + 1].start()].strip(" ") for j in range(n - 1)):
                    continue
                words = [t.group(0) for t in seg]
                low = [w.lower() for w in words]
                if low[0] in STOPT or low[-1] in STOPT or any(len(w) < 3 for w in low) and n == 1:
                    continue
                if n == 1 and len(low[0]) < 5:
                    continue
                surface = masked[seg[0].start():seg[-1].end()]
                if i == 0 and surface[0].isupper() and not surface.isupper() and not (len(surface) > 1 and surface[1].isupper()):
                    surface = surface[0].lower() + surface[1:]
                forms[norm_term(surface)][surface].append(sid)
        # hyphenated compounds as units
        for t in toks:
            w = t.group(0)
            if "-" in w:
                forms[norm_term(w)][w].append(sid)
    out = []
    for key, sf in forms.items():
        if len(key) < 5 or len(sf) < 2:
            continue
        # drop case-only variants that are just sentence-initial capitalisation
        canon = {}
        for s_, ids in sf.items():
            k2 = s_ if s_.isupper() and len(s_) > 1 else s_
            canon.setdefault(k2, []).extend(ids)
        low_forms = {s_.lower() for s_ in canon}
        if len(canon) < 2:
            continue
        stems = {(s_.lower()[:-1] if s_.lower().endswith("s") and not s_.lower().endswith("ss") else s_.lower()) for s_ in canon}
        if len(stems) == 1:  # singular / plural only: grammar, not terminology
            continue
        if len(low_forms) == 1 and all(s_[:1].isupper() == (s_[:1].isupper()) for s_ in canon) and not any(s_.isupper() and len(s_) > 1 for s_ in canon) and sum(1 for s_ in canon if s_[:1].islower()) == 0:
            continue
        out.append((key, {s_: sorted(set(ids)) for s_, ids in canon.items()}))
    # keep the longest n-gram of overlapping clusters: a cluster whose forms are all contained in another cluster's forms is a fragment
    def total(c):
        return sum(len(v) for v in c[1].values())
    out.sort(key=lambda c: (-len(c[0]), -total(c)))
    keep, seen = [], []
    for c in out:
        txt = " ".join(c[1].keys()).lower()
        if any(txt in s_ for s_ in seen):
            continue
        keep.append(c)
        seen.append(txt)
    return keep


ABBR_DEF = re.compile(r"\b([A-Z][A-Za-z0-9&,'’-]*(?:\s+(?:of|and|for|the|in|on|to|with|[A-Za-z0-9&,'’-]+)){1,8}?)\s*\(\s*([A-Z][A-Za-z0-9-]{1,9}s?)\s*\)")


def abbreviations(sentences):
    """definitions 'Long Form (ABBR)' (Schwartz-Hearst style matching) and uses; -> dict abbr -> {definitions[(long, sid)], uses[sid], first_use}"""
    defs = defaultdict(list)
    uses = defaultdict(list)
    for sid, text in sentences:
        masked, _ = mask(text)
        for m in re.finditer(r"\(\s*([A-Za-z][A-Za-z0-9-]{1,9}s?)\s*\)", masked):
            short = m.group(1)
            if sum(c.isupper() for c in short) < 2 and not short.isupper():
                continue
            words = masked[:m.start()].rstrip().split()
            cand = " ".join(words[-min(len(short) + 5, len(words)):])
            k = _match_short(short.rstrip("s") if short.endswith("s") and short[:-1].isupper() else short, cand)
            if k is None:
                continue
            long_ = cand[k:].strip(" ,;:")
            if len(long_.split()) >= 2 or (len(long_) > len(short)):
                defs[short.rstrip("s") if short.endswith("s") and short[:-1].isupper() else short].append((long_, sid))
        for m in re.finditer(r"\b([A-Z][A-Z0-9]{1,8})s?\b", masked):
            uses[m.group(1)].append(sid)
    return defs, uses


def _match_short(short, long_):
    s_i, l_i = len(short) - 1, len(long_) - 1
    while s_i >= 0:
        c = short[s_i].lower()
        if not c.isalnum():
            s_i -= 1
            continue
        while l_i >= 0 and (long_[l_i].lower() != c or (s_i == 0 and l_i > 0 and long_[l_i - 1].isalnum())):
            l_i -= 1
        if l_i < 0:
            return None
        l_i -= 1
        s_i -= 1
    return l_i + 1


def scan_doc(sentences, lang="en"):
    """document-level consistency -> list of {kind, detail, sids, variants, suggestion}"""
    out = []
    text_all = [(sid, t) for sid, t in sentences]
    if lang == "zh":
        fw = Counter()
        for sid, t in text_all:
            fw["halfwidth" if re.search(r"[㐀-鿿][,;:]", t) else "ok"] += 1
        pct = Counter()
        for sid, t in text_all:
            for m in re.finditer(r"\d\s?%", t):
                pct["with space" if " " in m.group(0) else "no space"] += 1
        if len(pct) > 1:
            out.append({"kind": "number_format", "detail": "百分号写法不一致: %s" % dict(pct), "sids": [], "variants": dict(pct), "suggestion": "统一为无空格的 10%"})
        return out
    words = Counter()
    for sid, t in text_all:
        for w in re.findall(r"[A-Za-z]+", mask(t)[0].lower()):
            words[w] += 1
    styles = {"US": Counter(), "UK": Counter()}
    for w, c in words.items():
        st = spelling_style(w)
        if st:
            styles[st][w] += c
    if styles["US"] and styles["UK"]:
        majority = "US" if sum(styles["US"].values()) >= sum(styles["UK"].values()) else "UK"
        minority = "UK" if majority == "US" else "US"
        sids = [sid for sid, t in text_all if any(re.search(r"\b%s\b" % re.escape(w), t, re.I) for w in styles[minority])]
        out.append({"kind": "spelling_mix", "detail": "US and UK spelling are mixed: US %s (%d) vs UK %s (%d)" % (", ".join(sorted(styles["US"])), sum(styles["US"].values()), ", ".join(sorted(styles["UK"])), sum(styles["UK"].values())),
                    "sids": sids, "variants": {"US": dict(styles["US"]), "UK": dict(styles["UK"])}, "suggestion": "use %s spelling throughout (the majority)" % majority, "majority": majority})
    for key, sf in term_candidates(text_all):
        forms = sorted(sf.items(), key=lambda kv: -len(kv[1]))
        out.append({"kind": "term_variants", "detail": "same term written differently: " + "; ".join("'%s' (%d)" % (s_, len(ids)) for s_, ids in forms), "sids": sorted({i for _, ids in forms for i in ids}), "variants": {s_: len(ids) for s_, ids in forms},
                    "suggestion": "choose one form (suggested: '%s')" % forms[0][0], "canonical": forms[0][0]})
    defs, uses = abbreviations(text_all)
    order = {sid: i for i, (sid, _) in enumerate(text_all)}
    for ab, dl in defs.items():
        longs = {re.sub(r"\W", "", l.lower()) for l, _ in dl}
        if len(dl) > 1 and len(longs) == 1:
            out.append({"kind": "abbr_redefined", "detail": "%s is defined %d times (%s)" % (ab, len(dl), ", ".join(s for _, s in dl)), "sids": [s for _, s in dl], "suggestion": "define once, at first use"})
        elif len(longs) > 1:
            out.append({"kind": "abbr_conflict", "detail": "%s is expanded in different ways: %s" % (ab, "; ".join("'%s' (%s)" % x for x in dl)), "sids": [s for _, s in dl], "suggestion": "one expansion per abbreviation"})
        first_def = min(order[s] for _, s in dl)
        early = [s for s in uses.get(ab, []) if order[s] < first_def]
        if early:
            out.append({"kind": "abbr_before_definition", "detail": "%s is used before its definition (%s)" % (ab, early[0]), "sids": early[:3], "suggestion": "define at first use"})
    for ab, ids in uses.items():
        if ab not in defs and len(ids) >= 2 and len(ab) >= 3 and ab not in ("DNA", "RNA", "USA", "UK", "US", "PCR", "MRI", "CT", "PDF", "URL", "HTML", "AI", "GPU", "CPU", "SD", "SE", "CI", "ANOVA", "OK", "II", "III", "IV", "NOT", "AND", "OR", "TRUE", "FALSE"):
            out.append({"kind": "abbr_undefined", "detail": "%s is used %d times and never defined" % (ab, len(ids)), "sids": ids[:3], "suggestion": "define at first use unless it is standard in the field"})
    fmt = {"percent_space": Counter(), "figure": Counter(), "etal": Counter()}
    for sid, t in text_all:
        for m in re.finditer(r"\d(\s?)%", t):
            fmt["percent_space"]["10 %" if m.group(1) else "10%"] += 1
        for m in re.finditer(r"\b(Fig\.|Figure|Figs\.|Figures)\s*\d", t):
            fmt["figure"][m.group(1).rstrip(".")[:3]] += 1
        for m in re.finditer(r"\bet al(\.?)", t):
            fmt["etal"]["et al." if m.group(1) else "et al"] += 1
    for k, c in fmt.items():
        if len(c) > 1:
            out.append({"kind": "format_mix", "detail": "%s written in different ways: %s" % (k, dict(c)), "sids": [], "variants": dict(c), "suggestion": "use one form (the most frequent: %s)" % c.most_common(1)[0][0]})
    return out
