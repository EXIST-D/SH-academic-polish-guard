#!/usr/bin/env python3
"""pg.py - polish guard: academic language polishing with a proof that the meaning did not change.

The model decides what to improve; the tool finds the problems (mechanical errors, grammar patterns, translationese, register, terminology / spelling / abbreviation
inconsistencies), fixes the mechanical ones safely, checks EVERY edit against the original (citations, references, numbers and units, negation, quantifiers, hedge strength,
causal vs correlational wording, conditionals, direction of change, size of the edit), writes the result back into the same file format with every untouched
character unchanged (Word: tracked changes), and delivers a change log (original / revised / type / reason / risk), a facts map and a review checklist.

  pg.py prepare [INPUT] --work W [--case /input/case.json] [--genre journal|thesis|grant|response|abstract|general] [--lang auto|en|zh]
  pg.py scan W [--cat C] [--min-sev low|med|high] [--limit N]         issues per sentence + document-level consistency
  pg.py show W [--ids S001-S020 | --par P3 | --issues]                 current text with ids
  pg.py autofix W [--no-spelling] [--spelling US|UK]                   safe mechanical fixes (verified, logged)
  pg.py ingest W [FILE|-]                                              edit / keep / term / flag blocks; every edit is verified against the original
  pg.py next W | check W                                               what is unresolved; integrity of the whole document
  pg.py revert W S012 ...  |  status W
  pg.py assemble W --out OUT [--case ...] [--answers answers.json]
"""
from __future__ import annotations

import argparse
import difflib
import html
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import detect  # noqa: E402
import nlib  # noqa: E402
import protect  # noqa: E402
import segment  # noqa: E402

VERSION = "1.0.0"
SCHEMA = "polish-guard/1"
TYPES = ("grammar", "punctuation", "mechanical", "term", "consistency", "register", "wording", "clarity", "concision", "style", "spelling", "translation")
SEV = {"low": 0, "med": 1, "high": 2}


# ------------------------------------------------------------------------------------------------ io
def jload(p, default=None):
    if not os.path.isfile(p):
        return default
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def jsave(p, obj):
    os.makedirs(os.path.dirname(os.path.abspath(p)), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, p)


def find_key(obj, names):
    if isinstance(obj, dict):
        for k in names:
            if k in obj:
                return obj[k]
        for v in obj.values():
            r = find_key(v, names)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = find_key(v, names)
            if r is not None:
                return r
    return None


def load(work):
    doc = jload(os.path.join(work, "doc.json"))
    if doc is None:
        raise SystemExit("no doc.json in %s: run `prepare` first" % work)
    return doc, jload(os.path.join(work, "edits.json"))


def save_edits(work, ed):
    jsave(os.path.join(work, "edits.json"), ed)


def sentences(doc):
    for p in doc["paragraphs"]:
        for s in p["sentences"]:
            yield p, s


def cur_map(doc, ed):
    return {sid: v["cur"] for sid, v in ed["sentences"].items()}


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# ------------------------------------------------------------------------------------------------ prepare
def discover_input(a):
    case = jload(a.case) if a.case and os.path.isfile(a.case) else None
    if a.input and os.path.isfile(a.input):
        return a.input, case
    base = os.path.dirname(os.path.abspath(a.case)) if a.case else "/input"
    cands = []
    if case:
        for k in ("file", "path", "manuscript", "draft", "document", "input_file", "source_file", "files"):
            v = find_key(case, [k])
            for x in (v if isinstance(v, list) else [v]):
                if isinstance(x, str):
                    for root in (base, "/input", ""):
                        pth = os.path.join(root, x) if root else x
                        if os.path.isfile(pth):
                            cands.append(pth)
    if cands:
        return cands[0], case
    for exts in ((".docx", ".tex", ".pdf"), (".md", ".txt")):
        for root in dict.fromkeys((base, "/input")):
            if os.path.isdir(root):
                fs = [os.path.join(root, f) for f in sorted(os.listdir(root)) if f.lower().endswith(exts) and f.lower() not in ("task.md", "readme.md")]
                if fs:
                    if len(fs) > 1:
                        print("NOTE: several candidate files (%s): using the first" % ", ".join(os.path.basename(x) for x in fs[:5]))
                    return fs[0], case
    txt = find_key(case, ["text", "draft", "manuscript", "abstract", "paragraph", "passage", "content", "source_text"]) if case else None
    if isinstance(txt, str) and len(txt) > 30:
        os.makedirs(a.work, exist_ok=True)
        p = os.path.join(a.work, "case_text.txt")
        open(p, "w", encoding="utf-8").write(txt)
        return p, case
    raise SystemExit("no manuscript found: pass INPUT, or --case with a file path / text field (looked in %s and /input)" % base)


def guess_genre(case, text, headings=False):
    s = (json.dumps(case, ensure_ascii=False) if case else "") + " " + text[:400]
    for g, pat in (("grant", r"grant|proposal|基金|申请书|funding"), ("response", r"reviewer|response to|rebuttal|审稿|回复|point-by-point"), ("thesis", r"thesis|dissertation|学位论文|毕业论文")):
        if re.search(pat, s, re.I):
            return g
    if not headings and (len(text.split()) < 300 or nlib.cjk_ratio(text) > 0.3 and len(text) < 500):
        return "abstract"
    return "journal"


def cmd_prepare(a):
    os.makedirs(a.work, exist_ok=True)
    path, case = discover_input(a)
    doc = segment.build(path, a.work)
    body = " ".join(p["text"] for p in doc["paragraphs"] if p["kind"] != "frozen")
    if not body.strip():
        raise SystemExit("no editable text found in the input")
    lang = a.lang if a.lang != "auto" else nlib.detect_lang(body)
    genre = a.genre or guess_genre(case, body, any(p["kind"] == "heading" or p.get("section") not in ("(start)", None) for p in doc["paragraphs"]))
    doc.update({"lang": lang, "genre": genre, "input_path": path, "version": VERSION, "task": (find_key(case, ["task", "instruction", "prompt", "requirements", "description"]) if case else None)})
    jsave(os.path.join(a.work, "doc.json"), doc)
    ed = {"sentences": {s["id"]: {"orig": s["text"], "cur": s["text"], "steps": [], "kept": {}, "flags": []} for _, s in sentences(doc)}, "terms": [], "rejected": [], "log": []}
    save_edits(a.work, ed)
    ss = [(s["id"], s["text"]) for _, s in sentences(doc)]
    iss = Counter(i["cat"] for _, t in ss for i in detect.scan_sentence(t, lang, genre))
    dd = detect.scan_doc(ss, lang)
    frozen = Counter(p["frozen_reason"] for p in doc["paragraphs"] if p["kind"] == "frozen")
    print(json.dumps({"ok": True, "work": a.work, "file": doc["file"], "format": doc["format"], "lang": lang, "genre": genre, "paragraphs": len(doc["paragraphs"]), "editable_sentences": len(ss), "frozen_paragraphs": dict(frozen),
                      "issues_by_category": dict(iss), "document_level": dict(Counter(d["kind"] for d in dd))}, ensure_ascii=False))
    if doc.get("note"):
        print("NOTE: " + doc["note"])
    if doc.get("task"):
        print("TASK (from the case file): " + str(doc["task"])[:600])
    print("Next: `autofix` (safe mechanical fixes), `scan` (what needs a decision), `show`, write edits and `ingest` them, `check`, `assemble`.")


# ------------------------------------------------------------------------------------------------ scan / show
def sentence_issues(doc, ed, include_auto=True):
    out = {}
    for p, s in sentences(doc):
        cur = ed["sentences"][s["id"]]["cur"]
        iss = detect.scan_sentence(cur, doc["lang"], doc["genre"])
        kept = ed["sentences"][s["id"]]["kept"]
        iss = [i for i in iss if i["rule"] not in kept and (include_auto or not i["auto"])]
        if iss:
            out[s["id"]] = iss
    return out


def cmd_scan(a):
    doc, ed = load(a.work)
    iss = sentence_issues(doc, ed)
    byp = {s["id"]: p for p, s in sentences(doc)}
    n_auto = sum(1 for v in iss.values() for i in v if i["auto"])
    print("%d sentence(s) with issues; %d mechanical issue(s) can be fixed by `autofix`" % (len(iss), n_auto))
    rows = []
    for sid, v in iss.items():
        v2 = [i for i in v if not i["auto"] and (not a.cat or i["cat"] == a.cat) and SEV[i["sev"]] >= SEV[a.min_sev]]
        if v2:
            rows.append((-max(SEV[i["sev"]] for i in v2), -len(v2), sid, v2))
    rows.sort()
    for _, _, sid, v2 in rows[:a.limit]:
        p = byp[sid]
        print("%s [%s | %s] %s" % (sid, p["id"], (p["section"] or "")[:30], ed["sentences"][sid]["cur"][:160].replace("\n", " ")))
        for i in v2[:6]:
            print("    - %s/%s %s: '%s'%s  (%s)" % (i["cat"], i["sev"], i["rule"], i["text"][:50], (" -> " + i["suggestion"]) if i["suggestion"] else "", i["why"][:90]))
    if len(rows) > a.limit:
        print("... %d more sentence(s): --limit / --cat / --min-sev" % (len(rows) - a.limit))
    ss = [(s["id"], ed["sentences"][s["id"]]["cur"]) for _, s in sentences(doc)]
    dd = detect.scan_doc(ss, doc["lang"])
    print("\nDOCUMENT-LEVEL (%d)" % len(dd))
    for d in dd:
        print("  - %s: %s%s" % (d["kind"], d["detail"][:200], ("  -> " + d["suggestion"]) if d.get("suggestion") else ""))
    if dd:
        print("  decide with `=== term` blocks (canonical + variants) or `autofix` (spelling); abbreviations: define at first use in an edit")


def cmd_show(a):
    doc, ed = load(a.work)
    sel = None
    if a.ids:
        ids = []
        for part in re.split(r"[,\s]+", a.ids.strip()):
            m = re.fullmatch(r"S(\d+)-S?(\d+)", part)
            if m:
                ids += ["S%03d" % n for n in range(int(m.group(1)), int(m.group(2)) + 1)]
            elif part:
                ids.append(part)
        sel = set(ids)
    iss = sentence_issues(doc, ed)
    last = None
    for p, s in sentences(doc):
        if sel is not None and s["id"] not in sel:
            continue
        if a.par and p["id"] != a.par:
            continue
        if a.issues and s["id"] not in iss:
            continue
        if p["id"] != last:
            print("\n## %s [%s] %s" % (p["id"], p["kind"], (p["section"] or "")[:50]))
            last = p["id"]
        e = ed["sentences"][s["id"]]
        mark = ("*" if e["cur"] != e["orig"] else " ") + ("!" if s["id"] in iss else " ")
        print("%s%s %s" % (s["id"], mark, e["cur"].replace("\n", " ")))
        if e["cur"] != e["orig"] and a.orig:
            print("      was: " + e["orig"].replace("\n", " "))
    print("\n(* = edited, ! = open issue)")


# ------------------------------------------------------------------------------------------------ applying steps
def add_step(ed, sid, by, typ, rule, old, new, reason, warns=None):
    e = ed["sentences"][sid]
    e["steps"].append({"by": by, "type": typ, "rule": rule, "from": old, "to": new, "reason": reason, "warnings": warns or [], "ts": now()})
    e["cur"] = new


def verified_set(doc, ed, sid, new, by, typ, rule, reason, allow_rewrite=False, doc_terms=None):
    """verify `new` against the ORIGINAL sentence; apply if no error. -> (ok, issues)"""
    e = ed["sentences"][sid]
    iss = protect.verify_edit(e["orig"], new, allow_rewrite=allow_rewrite, doc_content=doc_terms)
    errs = [i for i in iss if i["severity"] == "error"]
    if errs:
        ed["rejected"].append({"sid": sid, "by": by, "type": typ, "rule": rule, "revised": new, "reason": reason, "errors": errs, "ts": now()})
        return False, iss
    add_step(ed, sid, by, typ, rule, e["cur"], new, reason, [i for i in iss if i["severity"] == "warn"])
    for r in ed["rejected"]:
        if r["sid"] == sid and by == "model":
            r["resolved"] = True  # a later accepted edit of the same sentence supersedes the rejected attempt
    return True, iss


def doc_terms(doc):
    c = Counter()
    for p in doc["paragraphs"]:
        c.update(protect.ABBR_RE.findall(protect.strip_protected(p["text"])))
    return c


def cmd_autofix(a):
    doc, ed = load(a.work)
    lang = doc["lang"]
    applied, skipped = Counter(), []
    dt = doc_terms(doc)
    for p, s in sentences(doc):
        sid = s["id"]
        cur = ed["sentences"][sid]["cur"]
        new, ap = detect.autofix_sentence(cur, lang)
        if new != cur:
            ok, iss = verified_set(doc, ed, sid, new, "autofix", "mechanical", ",".join(sorted({x["rule"] for x in ap})), "; ".join("%s: '%s' -> '%s'" % (x["rule"], x["from"][:30], x["to"][:30]) for x in ap[:4]), doc_terms=dt)
            if ok:
                for x in ap:
                    applied[x["rule"]] += 1
            else:
                skipped.append((sid, [i["kind"] for i in iss if i["severity"] == "error"]))
    # spelling consistency
    sp_changed = 0
    if lang == "en" and not a.no_spelling:
        ss = [(s["id"], ed["sentences"][s["id"]]["cur"]) for _, s in sentences(doc)]
        sd = next((d for d in detect.scan_doc(ss, lang) if d["kind"] == "spelling_mix"), None)
        if sd:
            target = a.spelling or sd["majority"]
            for p, s in sentences(doc):
                sid = s["id"]
                cur = ed["sentences"][sid]["cur"]
                masked, store = detect.mask(cur)
                changes = []

                def rep(m):
                    c = detect.convert_spelling(m.group(0), target)
                    if c:
                        changes.append((m.group(0), c))
                        return c
                    return m.group(0)
                new = detect.unmask(re.sub(r"[A-Za-z]{4,}", rep, masked), store)
                if changes and new != cur:
                    ok, iss = verified_set(doc, ed, sid, new, "autofix", "spelling", "spelling_" + target, "%s spelling used throughout: %s" % (target, "; ".join("%s -> %s" % x for x in changes[:4])), doc_terms=dt)
                    sp_changed += len(changes) if ok else 0
    if lang == "en" and not a.no_spelling:
        pct = Counter()
        for p, s in sentences(doc):
            for m in re.finditer(r"\d( ?)%", ed["sentences"][s["id"]]["cur"]):
                pct["sp" if m.group(1) else "no"] += 1
        if pct["sp"] and pct["no"] >= pct["sp"]:
            for p, s in sentences(doc):
                sid = s["id"]
                cur = ed["sentences"][sid]["cur"]
                new = re.sub(r"(?<=\d) %", "%", cur)
                if new != cur:
                    verified_set(doc, ed, sid, new, "autofix", "consistency", "percent_format", "percent sign written without a space throughout", doc_terms=dt)
    save_edits(a.work, ed)
    print("autofix: %d mechanical fix(es) %s; %d spelling change(s); %d sentence(s) skipped by the verifier %s" % (sum(applied.values()), dict(applied), sp_changed, len(skipped), skipped[:3]))


# ------------------------------------------------------------------------------------------------ ingest
BLOCK_KEYS = {"revised": "revised", "revision": "revised", "text": "revised", "type": "type", "reason": "reason", "why": "reason", "rewrite": "rewrite", "canonical": "canonical", "variants": "variants", "variant": "variants", "note": "note", "rule": "rule", "scope": "scope"}


def parse_blocks(text):
    recs, cur, key = [], None, None
    for ln in text.splitlines():
        s = ln.rstrip()
        if re.match(r"^\s*```\w*\s*$", s):
            continue
        m = re.match(r"^\s*[#=*]{2,}\s*(edit|keep|term|flag|revert)\b\s*(.*?)[*=#]*\s*$", s, re.I)
        if m:
            cur = {"kind": m.group(1).lower(), "target": m.group(2).strip(), "fields": {}}
            recs.append(cur)
            key = None
            continue
        if cur is None:
            continue
        mk = re.match(r"^\s*(?:[-*]\s*)?([A-Za-z_]+)\s*[:：]\s*(.*)$", s)
        if mk and mk.group(1).lower() in BLOCK_KEYS:
            key = BLOCK_KEYS[mk.group(1).lower()]
            cur["fields"].setdefault(key, [])
            if mk.group(2).strip() or key in ("revised",):
                cur["fields"][key].append(mk.group(2).rstrip())
            continue
        if key:
            cur["fields"][key].append(s.rstrip())
    out = []
    for r in recs:
        f = {k: "\n".join(v).strip() if k == "revised" else " ".join(x.strip() for x in v).strip() for k, v in r["fields"].items()}
        out.append({"kind": r["kind"], "target": r["target"], "f": f})
    return out


def expand_ids(spec):
    ids = []
    for part in re.split(r"[,\s]+", spec.strip()):
        m = re.fullmatch(r"S(\d+)-S?(\d+)", part)
        if m:
            ids += ["S%03d" % n for n in range(int(m.group(1)), int(m.group(2)) + 1)]
        elif re.fullmatch(r"S\d+", part):
            ids.append("S%03d" % int(part[1:]))
    return ids


def apply_term(doc, ed, canonical, variants, reason, dt):
    n_sent, n_rep, skipped = 0, 0, []
    vs = sorted({v.strip() for v in variants if v.strip() and v.strip() != canonical}, key=len, reverse=True)
    if not vs:
        return 0, 0, []
    rx = re.compile(r"(?<![\w-])(?:%s)(?![\w-])" % "|".join(re.escape(v) for v in vs), re.I)
    for p, s in sentences(doc):
        sid = s["id"]
        cur = ed["sentences"][sid]["cur"]
        masked, store = detect.mask(cur)
        cnt = [0]

        def rep(m):
            cnt[0] += 1
            tgt = canonical
            if m.group(0)[:1].isupper() and not canonical[:1].isupper() and (m.start() == 0 or masked[max(0, m.start() - 2):m.start()].strip() in (".", "")):
                tgt = canonical[:1].upper() + canonical[1:]
            elif m.group(0).isupper() and len(m.group(0)) > 1:
                tgt = canonical.upper() if canonical.isupper() else canonical
            return tgt
        new = detect.unmask(rx.sub(rep, masked), store)
        if cnt[0] and new != cur:
            ok, iss = verified_set(doc, ed, sid, new, "term", "term", "term:" + canonical, reason or "terminology: '%s' used for all variants" % canonical, doc_terms=dt)
            if ok:
                n_sent += 1
                n_rep += cnt[0]
            else:
                skipped.append(sid)
    return n_sent, n_rep, skipped


def cmd_ingest(a):
    doc, ed = load(a.work)
    text = sys.stdin.read() if (not a.file or a.file == "-") else open(a.file, encoding="utf-8").read()
    recs = parse_blocks(text)
    if not recs:
        raise SystemExit("no blocks found: start each with '=== edit S012', '=== keep S015', '=== term' or '=== flag S020'")
    dt = doc_terms(doc)
    lines, n = [], Counter()
    for r in recs:
        k, f = r["kind"], r["f"]
        if k == "edit":
            ids = expand_ids(r["target"])
            if not ids or any(i not in ed["sentences"] for i in ids):
                lines.append("edit '%s': unknown sentence id (see `show`)" % r["target"])
                n["bad"] += 1
                continue
            rev = f.get("revised", "")
            typ = (f.get("type") or "").lower() or "style"
            if not rev:
                lines.append("%s: no `revised:` text" % r["target"])
                n["bad"] += 1
                continue
            if typ not in TYPES:
                lines.append("%s: type '%s' is not one of %s (kept as 'style')" % (r["target"], typ, ", ".join(TYPES)))
                typ = "style"
            if not f.get("reason"):
                lines.append("%s WARN: no `reason:` (every change needs one)" % r["target"])
            sid = ids[0]
            allow = (f.get("rewrite") or "").lower() in ("yes", "true", "1")
            if len(ids) > 1:  # merge: the revised text replaces the first sentence, the others become empty
                joined_orig = " ".join(ed["sentences"][i]["orig"] for i in ids)
                iss = protect.verify_edit(joined_orig, rev, allow_rewrite=allow, doc_content=dt)
                errs = [i for i in iss if i["severity"] == "error"]
                if errs:
                    ed["rejected"].append({"sid": r["target"], "by": "model", "type": typ, "rule": "edit", "revised": rev, "reason": f.get("reason", ""), "errors": errs, "ts": now()})
                    n["rejected"] += 1
                    lines.append("%s REJECTED: %s" % (r["target"], "; ".join("%s: %s" % (i["kind"], i["detail"][:160]) for i in errs)))
                    continue
                for j, i in enumerate(ids):
                    old = ed["sentences"][i]["cur"]
                    add_step(ed, i, "model", typ, "merge/split", old, rev if j == 0 else "", f.get("reason", ""), [x for x in iss if x["severity"] == "warn"] if j == 0 else [])
                n["applied"] += 1
                for w in [x for x in iss if x["severity"] == "warn"]:
                    lines.append("%s WARN %s: %s" % (r["target"], w["kind"], w["detail"][:160]))
                continue
            before = {i["rule"] for i in detect.scan_sentence(ed["sentences"][sid]["cur"], doc["lang"], doc["genre"])}
            ok, iss = verified_set(doc, ed, sid, rev, "model", typ, "edit", f.get("reason", ""), allow_rewrite=allow, doc_terms=dt)
            if ok:
                n["applied"] += 1
                newiss = [i for i in detect.scan_sentence(rev, doc["lang"], doc["genre"]) if i["rule"] not in before and i["cat"] in ("grammar", "mechanical", "claim_strength")]
                for i in newiss[:3]:
                    ed["sentences"][sid]["steps"][-1]["warnings"].append({"severity": "warn", "kind": "new_issue", "detail": "the revision introduces: %s ('%s')" % (i["why"], i["text"][:40])})
                    lines.append("%s WARN new_issue: %s ('%s')" % (sid, i["why"][:80], i["text"][:40]))
                for w in [x for x in iss if x["severity"] == "warn"]:
                    lines.append("%s WARN %s: %s" % (sid, w["kind"], w["detail"][:160]))
            else:
                n["rejected"] += 1
                lines.append("%s REJECTED (original kept): %s" % (sid, "; ".join("%s: %s" % (i["kind"], i["detail"][:170]) for i in iss if i["severity"] == "error")))
        elif k == "keep":
            for sid in expand_ids(r["target"]):
                if sid in ed["sentences"]:
                    rule = f.get("rule") or "*"
                    ed["sentences"][sid]["kept"][rule] = f.get("reason", "kept by decision")
                    n["kept"] += 1
        elif k == "flag":
            for sid in expand_ids(r["target"]):
                if sid in ed["sentences"]:
                    ed["sentences"][sid]["flags"].append(f.get("note") or f.get("reason") or "needs confirmation")
                    n["flagged"] += 1
        elif k == "revert":
            for sid in expand_ids(r["target"]):
                if sid in ed["sentences"]:
                    e = ed["sentences"][sid]
                    e["cur"], e["steps"] = e["orig"], []
                    n["reverted"] += 1
        elif k == "term":
            canon = f.get("canonical", "").strip()
            vs = [x.strip() for x in re.split(r"[;|]", f.get("variants", "")) if x.strip()]
            if not canon or not vs:
                lines.append("term block needs `canonical:` and `variants:` (separated by ;)")
                n["bad"] += 1
                continue
            ns, nr, sk = apply_term(doc, ed, canon, vs, f.get("reason", ""), dt)
            ed["terms"].append({"canonical": canon, "variants": vs, "sentences": ns, "replacements": nr, "reason": f.get("reason", ""), "skipped": sk})
            n["terms"] += 1
            lines.append("term '%s': %d replacement(s) in %d sentence(s)%s" % (canon, nr, ns, (" - skipped by the verifier: " + ", ".join(sk)) if sk else ""))
    save_edits(a.work, ed)
    print("applied %d edit(s) | rejected %d | kept %d | flagged %d | terms %d | bad %d" % (n["applied"], n["rejected"], n["kept"], n["flagged"], n["terms"], n["bad"]))
    for ln in lines[:40]:
        print("  " + ln)
    sys.exit(2 if (n["rejected"] or n["bad"]) else 0)


# ------------------------------------------------------------------------------------------------ check
def doc_inventory(doc, ed, which):
    prot, nums = Counter(), Counter()
    for p in doc["paragraphs"]:
        if p["kind"] == "frozen":
            continue
        for s in p["sentences"]:
            t = ed["sentences"][s["id"]]["orig" if which == "orig" else "cur"]
            prot.update(protect.inventory(t)["protected"])
            nums.update(protect.numbers_of(t))
    return prot, nums


def run_check(doc, ed):
    iss = sentence_issues(doc, ed)
    unresolved = [(sid, i) for sid, v in iss.items() for i in v if SEV[i["sev"]] >= 1 and not i["auto"]]
    auto_left = [(sid, i) for sid, v in iss.items() for i in v if i["auto"]]
    ss = [(s["id"], ed["sentences"][s["id"]]["cur"]) for _, s in sentences(doc)]
    dd = detect.scan_doc(ss, doc["lang"])
    po, no = doc_inventory(doc, ed, "orig")
    pc, nc = doc_inventory(doc, ed, "cur")
    integrity = []
    if po != pc:
        integrity.append("citations / references / math differ: removed %s; added %s" % (dict(po - pc), dict(pc - po)))
    if no != nc:
        integrity.append("numbers / units differ: removed %s; added %s" % ({"%s%s" % k: v for k, v in (no - nc).items()}, {"%s%s" % k: v for k, v in (nc - no).items()}))
    changed = [sid for sid, e in ed["sentences"].items() if e["cur"] != e["orig"]]
    ratios = {sid: protect.edit_ratio(ed["sentences"][sid]["orig"], ed["sentences"][sid]["cur"]) for sid in changed}
    warn_steps = [(sid, w) for sid in changed for st in ed["sentences"][sid]["steps"] for w in st.get("warnings", [])]
    flagged = [sid for sid, e in ed["sentences"].items() if e["flags"]]
    return {"issues": iss, "unresolved": unresolved, "auto_left": auto_left, "doc_level": dd, "integrity": integrity, "changed": changed, "ratios": ratios, "warn_steps": warn_steps, "flagged": flagged}


def cmd_check(a):
    doc, ed = load(a.work)
    r = run_check(doc, ed)
    n_sent = len(ed["sentences"])
    tot_o = sum(len(protect.tok(e["orig"])) for e in ed["sentences"].values())
    tot_c = sum(len(protect.tok(e["cur"])) for e in ed["sentences"].values())
    mean_r = sum(r["ratios"].values()) / max(1, len(r["ratios"]))
    print("sentences: %d | changed: %d (%.0f%%) | mean edit ratio of changed sentences %.2f | tokens %d -> %d" % (n_sent, len(r["changed"]), 100.0 * len(r["changed"]) / max(1, n_sent), mean_r, tot_o, tot_c))
    print("INTEGRITY (whole document): %s" % ("OK - every citation, reference, number and unit of the original is still there" if not r["integrity"] else ""))
    for x in r["integrity"]:
        print("  ERROR " + x)
    print("rejected edits (original kept, not yet superseded): %d | edits with warnings: %d | flagged for the author: %d" % (len([x for x in ed["rejected"] if not x.get("resolved")]), len(r["warn_steps"]), len(r["flagged"])))
    print("unresolved issues (med/high, not fixed or kept): %d | mechanical issues still open: %d | document-level items: %d" % (len(r["unresolved"]), len(r["auto_left"]), len(r["doc_level"])))
    shown = 0
    for sid, i in r["unresolved"]:
        if shown >= a.limit:
            break
        print("  %s %s/%s %s: '%s'%s" % (sid, i["cat"], i["sev"], i["rule"], i["text"][:40], (" -> " + i["suggestion"]) if i["suggestion"] else ""))
        shown += 1
    for d in r["doc_level"][:8]:
        print("  DOC %s: %s" % (d["kind"], d["detail"][:160]))
    if a.warnings:
        for sid, w in r["warn_steps"]:
            print("  WARN %s %s: %s" % (sid, w["kind"], w["detail"][:170]))
    sys.exit(2 if r["integrity"] else 0)


def cmd_next(a):
    doc, ed = load(a.work)
    r = run_check(doc, ed)
    print("changed %d sentence(s); rejected %d; integrity %s" % (len(r["changed"]), len(ed["rejected"]), "OK" if not r["integrity"] else "BROKEN"))
    if r["auto_left"]:
        print("TODO run `autofix`: %d mechanical issue(s)" % len(r["auto_left"]))
    hi = [(s, i) for s, i in r["unresolved"] if i["sev"] == "high"]
    for sid, i in hi[:8]:
        print("TODO %s %s: '%s'%s" % (sid, i["rule"], i["text"][:40], (" -> " + i["suggestion"]) if i["suggestion"] else ""))
    if len(hi) > 8:
        print("... %d more high-severity issue(s): `scan --min-sev high`" % (len(hi) - 8))
    cl = [s for s, i in r["unresolved"] if i["cat"] == "claim_strength"]
    if cl:
        print("DECIDE %d claim-strength wording(s) (%s): do not change on your own: `=== keep S.. rule: claim_wording reason: ...` or `=== flag S..`" % (len(cl), ", ".join(sorted(set(cl))[:6])))
    for d in r["doc_level"][:6]:
        print("TODO %s: %s" % (d["kind"], d["detail"][:140]))
    if not r["auto_left"] and not hi and not r["doc_level"] and not r["integrity"]:
        print("Nothing blocking. `assemble W --out OUT`.")


def cmd_revert(a):
    doc, ed = load(a.work)
    for sid in a.ids:
        if sid in ed["sentences"]:
            e = ed["sentences"][sid]
            e["cur"], e["steps"] = e["orig"], []
            print("reverted " + sid)
    save_edits(a.work, ed)


def cmd_status(a):
    doc, ed = load(a.work)
    r = run_check(doc, ed)
    print(json.dumps({"sentences": len(ed["sentences"]), "changed": len(r["changed"]), "rejected": len(ed["rejected"]), "unresolved": len(r["unresolved"]), "integrity_ok": not r["integrity"], "terms": len(ed["terms"])}, ensure_ascii=False))


# ------------------------------------------------------------------------------------------------ assemble
def redline_md(doc, ed):
    L = []
    cur = cur_map(doc, ed)
    for pid, (old, new) in segment.paragraph_texts(doc, cur).items():
        if old == new:
            continue
        out = []
        for op, t in segment.word_diff(old, new):
            out.append(t if op == "=" else ("~~%s~~" % t.strip() + (" " if t.endswith(" ") else "") if op == "-" else "**%s**" % t.strip() + (" " if t.endswith(" ") else "")))
        L.append("**%s** %s\n" % (pid, "".join(out)))
    return "\n".join(L) or "(no change)\n"


def redline_html(doc, ed):
    cur = cur_map(doc, ed)
    parts = ["<!doctype html><meta charset='utf-8'><title>Redline</title><style>body{font:16px/1.6 Georgia,serif;max-width:46em;margin:2em auto;padding:0 1em}del{background:#fdd;color:#900}ins{background:#dfd;color:#060;text-decoration:none}.pid{color:#888;font:12px monospace}</style>"]
    for p in doc["paragraphs"]:
        if p["kind"] == "frozen":
            parts.append("<p class=pid>%s (frozen: %s)</p><pre>%s</pre>" % (p["id"], html.escape(p["frozen_reason"] or ""), html.escape(p["text"][:400])))
            continue
        old, new = segment.paragraph_texts(doc, cur)[p["id"]]
        body = "".join(html.escape(t) if op == "=" else ("<del>%s</del>" % html.escape(t) if op == "-" else "<ins>%s</ins>" % html.escape(t)) for op, t in segment.word_diff(old, new))
        parts.append("<p><span class=pid>%s</span> %s</p>" % (p["id"], body))
    return "\n".join(parts)


def facts_map(doc, ed):
    rows = []
    kinds = (("citation / reference", lambda t: list(protect.inventory(t)["protected"].elements())), ("number", lambda t: ["%s%s" % k for k in protect.numbers_of(t).elements()]))
    for kind, fn in kinds:
        idx_o, idx_c = defaultdict(list), defaultdict(list)
        for sid, e in ed["sentences"].items():
            for x in fn(e["orig"]):
                idx_o[x].append(sid)
            for x in fn(e["cur"]):
                idx_c[x].append(sid)
        for x in sorted(set(idx_o) | set(idx_c)):
            rows.append({"kind": kind, "item": x, "original_sentences": idx_o.get(x, []), "revised_sentences": idx_c.get(x, []), "status": "unchanged" if Counter(idx_o.get(x, [])).keys() and len(idx_o.get(x, [])) == len(idx_c.get(x, [])) else ("MISSING in revision" if x in idx_o and x not in idx_c else ("not in original" if x not in idx_o else "count changed"))})
    return rows


def changes_rows(doc, ed):
    byp = {s["id"]: p for p, s in sentences(doc)}
    rows = []
    for sid, e in ed["sentences"].items():
        if e["cur"] == e["orig"]:
            continue
        p = byp[sid]
        warns = [w for st in e["steps"] for w in st.get("warnings", [])]
        rows.append({"id": sid, "paragraph": p["id"], "section": p["section"], "original": e["orig"], "revised": e["cur"], "types": sorted({st["type"] for st in e["steps"]}), "by": sorted({st["by"] for st in e["steps"]}),
                     "reasons": [st["reason"] for st in e["steps"] if st["reason"]], "steps": [{"by": st["by"], "type": st["type"], "from": st["from"], "to": st["to"], "reason": st["reason"]} for st in e["steps"]],
                     "edit_ratio": round(protect.edit_ratio(e["orig"], e["cur"]), 2), "risk": [{"kind": w["kind"], "detail": w["detail"]} for w in warns], "needs_author": e["flags"]})
    return rows


def changes_md(rows):
    L = ["# Change log", "", "| id | type | original | revised | reason | risk |", "|---|---|---|---|---|---|"]
    for r in rows:
        L.append("| %s | %s | %s | %s | %s | %s |" % (r["id"], ", ".join(r["types"]), r["original"].replace("|", "/").replace("\n", " ")[:220], r["revised"].replace("|", "/").replace("\n", " ")[:220],
                                                   "; ".join(r["reasons"])[:160].replace("|", "/"), ("; ".join(x["kind"] for x in r["risk"]) or "-") + ((" / AUTHOR: " + "; ".join(r["needs_author"])) if r["needs_author"] else "")))
    return "\n".join(L) + "\n"


def review_md(doc, ed, chk, rows):
    L = ["# Review checklist", "", "Machine-assisted polish: nothing here has been approved by the author. Tick each item.", "", "## Edits that carry a risk flag"]
    risky = [r for r in rows if r["risk"] or r["needs_author"] or r["edit_ratio"] > 0.5]
    L += ["- [ ] %s (%.0f%% changed): %s | %s" % (r["id"], 100 * r["edit_ratio"], "; ".join(x["kind"] for x in r["risk"]) or "heavy edit", r["revised"][:140].replace("\n", " ")) for r in risky] or ["- none"]
    L += ["", "## Claim-strength wording left unchanged (author decision)"]
    cl = [(sid, i) for sid, v in chk["issues"].items() for i in v if i["cat"] == "claim_strength"]
    L += ["- [ ] %s: '%s' (%s)" % (sid, i["text"], i["why"][:60]) for sid, i in cl[:30]] or ["- none"]
    L += ["", "## Rejected edits (the original sentence was kept)"] + (["- %s: %s" % (x["sid"], "; ".join(e["kind"] for e in x["errors"])) for x in ed["rejected"] if not x.get("resolved")] or ["- none"])
    L += ["", "## Terminology decisions"] + (["- %s <- %s (%d replacements)" % (t["canonical"], ", ".join(t["variants"]), t["replacements"]) for t in ed["terms"]] or ["- none"])
    L += ["", "## Document-level items still open"] + (["- [ ] %s: %s" % (d["kind"], d["detail"][:160]) for d in chk["doc_level"]] or ["- none"])
    fz = Counter(p["frozen_reason"] for p in doc["paragraphs"] if p["kind"] == "frozen")
    L += ["", "## Not edited (frozen)"] + (["- %d paragraph(s): %s" % (n, r) for r, n in fz.items()] or ["- none"])
    L += ["", "## Always verify by hand", "- every changed sentence still says what the author meant (the checks are lexical: they catch dropped negations, changed numbers and strengthened claims, not every shift in meaning)", "- technical terms the tool cannot know are right or wrong", ""]
    return "\n".join(L)


def contract_fields(case):
    oc = find_key(case, ["output_contract", "outputContract", "output_schema", "outputs"]) if case else None
    fields = []

    def add(x):
        if isinstance(x, str) and x not in fields:
            fields.append(x)
    if isinstance(oc, list):
        for it in oc:
            add(it if isinstance(it, str) else (it.get("name") or it.get("field") or it.get("key")) if isinstance(it, dict) else None)
    elif isinstance(oc, dict):
        inner = oc.get("fields") or oc.get("required") or oc.get("properties") or oc.get("required_fields")
        if isinstance(inner, list):
            for it in inner:
                add(it if isinstance(it, str) else (it.get("name") or it.get("field") or it.get("key")) if isinstance(it, dict) else None)
        elif isinstance(inner, dict):
            for k in inner:
                add(k)
        else:
            for k in oc:
                if k not in ("type", "description", "title", "version", "schema", "$schema", "additionalProperties"):
                    add(k)
    return fields


def derive_field(name, ctx):
    n = name.lower()
    if n in ("status", "run_status", "state", "outcome"):
        return True, ctx["status"]
    if n in ("polished_text", "revised_text", "polished", "revised", "manuscript", "target", "product", "deliverable", "target_product", "text", "result_text", "edited_text", "改稿", "润色稿"):
        return True, {"file": ctx["polished_file"], "text": ctx["polished_text"]}
    if n in ("change_log", "changes", "edits", "revision_log", "modifications", "change_records", "修改记录", "edit_list", "diff"):
        return True, ctx["rows"]
    if n in ("facts", "fact_map", "facts_map", "source_map", "source_mapping", "numbers", "citations", "references_map", "fact_source_map", "事实与来源映射"):
        return True, ctx["facts"]
    if n in ("terminology", "glossary", "term_table", "terms", "terminology_table", "术语表"):
        return True, ctx["glossary"]
    if n in ("human_review", "needs_review", "review_items", "manual_review", "to_confirm", "open_items", "人工确认项"):
        return True, ctx["review"]
    if n in ("uncertainty", "uncertainties", "caveats", "risks", "limits", "boundaries", "limitations", "gaps", "版本与边界"):
        return True, ctx["uncertainty"]
    if n in ("sources", "source", "input", "inputs", "input_id", "input_files"):
        return True, ctx["sources"]
    if n in ("verification", "checks", "qa", "validation", "quality", "self_check", "integrity"):
        return True, ctx["verification"]
    if n in ("redline", "tracked_changes", "diff_view"):
        return True, {"markdown": "redline.md", "html": "redline.html", "docx": ctx.get("tracked_file")}
    if n in ("files", "output_files", "artifacts"):
        return True, ctx["files"]
    if n in ("summary", "overview", "report"):
        return True, ctx["summary_text"]
    return False, None


def cmd_assemble(a):
    doc, ed = load(a.work)
    chk = run_check(doc, ed)
    out = a.out
    os.makedirs(out, exist_ok=True)
    cur = cur_map(doc, ed)
    ext = {"md": ".md", "txt": ".txt", "tex": ".tex", "docx": ".docx"}[doc["format"]]
    base = os.path.splitext(doc["file"])[0]
    files = []
    polished_file, tracked_file, polished_text = "polished" + ext, None, None
    if doc["format"] == "docx":
        ptexts = segment.paragraph_texts(doc, cur)
        segment.write_docx(doc["input_path"], os.path.join(out, "polished.docx"), ptexts, doc, tracked=False)
        tracked_file = "polished_tracked_changes.docx"
        segment.write_docx(doc["input_path"], os.path.join(out, tracked_file), ptexts, doc, tracked=True)
        polished_text = "\n\n".join(p[1] for p in ptexts.values())
        open(os.path.join(out, "polished_text.txt"), "w", encoding="utf-8").write(polished_text + "\n")
        files += ["polished.docx", tracked_file, "polished_text.txt"]
    else:
        polished_text = segment.apply_text_like(doc, cur)
        open(os.path.join(out, polished_file), "w", encoding="utf-8").write(polished_text)
        files.append(polished_file)
    rows = changes_rows(doc, ed)
    open(os.path.join(out, "redline.md"), "w", encoding="utf-8").write(redline_md(doc, ed))
    open(os.path.join(out, "redline.html"), "w", encoding="utf-8").write(redline_html(doc, ed))
    open(os.path.join(out, "changes.md"), "w", encoding="utf-8").write(changes_md(rows))
    jsave(os.path.join(out, "changes.json"), rows)
    fm = facts_map(doc, ed)
    jsave(os.path.join(out, "facts_map.json"), fm)
    ss = [(s["id"], ed["sentences"][s["id"]]["cur"]) for _, s in sentences(doc)]
    defs, uses = detect.abbreviations(ss)
    glossary = {"decisions": ed["terms"], "open_variants": [d for d in chk["doc_level"] if d["kind"] in ("term_variants", "spelling_mix", "format_mix")], "abbreviations": {k: {"definitions": [{"long": l, "sentence": s} for l, s in v], "uses": len(uses.get(k, []))} for k, v in defs.items()}}
    jsave(os.path.join(out, "glossary.json"), glossary)
    remaining = [{"sentence": sid, "rule": i["rule"], "cat": i["cat"], "severity": i["sev"], "text": i["text"], "why": i["why"], "suggestion": i["suggestion"]} for sid, v in chk["issues"].items() for i in v]
    jsave(os.path.join(out, "issues_remaining.json"), remaining)
    open(os.path.join(out, "review_checklist.md"), "w", encoding="utf-8").write(review_md(doc, ed, chk, rows))
    ver = {"integrity_ok": not chk["integrity"], "integrity_errors": chk["integrity"], "sentences": len(ed["sentences"]), "changed_sentences": len(rows), "rejected_edits": len([x for x in ed["rejected"] if not x.get("resolved")]), "edits_with_warnings": len(chk["warn_steps"]),
           "unresolved_issues_med_high": len(chk["unresolved"]), "mechanical_issues_open": len(chk["auto_left"]), "document_level_open": len(chk["doc_level"]),
           "mean_edit_ratio_changed": round(sum(chk["ratios"].values()) / max(1, len(chk["ratios"])), 3), "facts_missing_in_revision": sum(1 for r in fm if r["status"] == "MISSING in revision"), "facts_not_in_original": sum(1 for r in fm if r["status"] == "not in original")}
    jsave(os.path.join(out, "check_report.json"), {"verification": ver, "rejected": ed["rejected"], "issues_remaining": remaining[:200]})
    review = [{"sentence": r["id"], "why": [x["kind"] for x in r["risk"]] + (["heavy_edit"] if r["edit_ratio"] > 0.5 else []) + (["author_flag"] if r["needs_author"] else []), "revised": r["revised"][:200]} for r in rows if r["risk"] or r["needs_author"] or r["edit_ratio"] > 0.5]
    review += [{"sentence": sid, "why": ["claim_strength_wording_left_unchanged"], "text": i["text"]} for sid, v in chk["issues"].items() for i in v if i["cat"] == "claim_strength"][:30]
    unc = []
    for x in [y for y in ed["rejected"] if not y.get("resolved")]:
        unc.append({"kind": "rejected_edit", "sentence": x["sid"], "detail": "; ".join(e["kind"] for e in x["errors"]) + " (original sentence kept)"})
    for fz, nfz in Counter(p["frozen_reason"] for p in doc["paragraphs"] if p["kind"] == "frozen").items():
        unc.append({"kind": "not_edited", "detail": "%d paragraph(s) not edited: %s" % (nfz, fz)})
    for x in chk["integrity"]:
        unc.append({"kind": "integrity_error", "detail": x})
    for d in chk["doc_level"]:
        unc.append({"kind": "open_" + d["kind"], "detail": d["detail"][:200]})
    if doc["format"] == "docx":
        unc.append({"kind": "docx_formatting", "detail": "inside an edited paragraph only the first run's character formatting is kept (bold / italic inside the paragraph is lost); paragraph properties are unchanged"})
    if doc.get("note"):
        unc.append({"kind": "input_note", "detail": doc["note"]})
    ok = not chk["integrity"] and not chk["auto_left"]
    status = "success" if ok and not any(i["sev"] == "high" for _, i in chk["unresolved"]) else "partial"
    summary_text = "%d of %d sentences changed (mean %.0f%% of tokens); integrity %s; %d edit(s) rejected by the verifier; %d review item(s)." % (len(rows), len(ed["sentences"]), 100 * ver["mean_edit_ratio_changed"], "OK" if not chk["integrity"] else "BROKEN", len(ed["rejected"]), len(review))
    ctx = {"status": status, "polished_file": tracked_file and "polished.docx" or polished_file, "polished_text": polished_text, "rows": rows, "facts": fm, "glossary": glossary, "review": review, "uncertainty": unc,
           "sources": [{"file": doc["file"], "format": doc["format"], "language": doc["lang"], "genre": doc["genre"], "tool": "polish-guard %s" % VERSION}], "verification": ver, "files": files, "tracked_file": tracked_file, "summary_text": summary_text}
    files += ["redline.md", "redline.html", "changes.md", "changes.json", "facts_map.json", "glossary.json", "issues_remaining.json", "review_checklist.md", "check_report.json"]
    ctx["files"] = files
    case = jload(a.case) if a.case and os.path.isfile(a.case) else None
    fields = contract_fields(case)
    answers = jload(a.answers, {}) if a.answers else {}
    cid = (find_key(case, ["case_id", "caseId"]) or find_key(case, ["id"])) if case else None
    result = {"case_id": cid}
    unfilled = []
    for fld in fields:
        if fld == "case_id":
            continue
        if fld in answers:
            result[fld] = answers[fld]
            continue
        okf, v = derive_field(fld, ctx)
        result[fld] = v if okf else None
        if not okf:
            unfilled.append(fld)
    for nm in ("status", "polished_text", "change_log", "facts_map", "glossary", "human_review", "uncertainty", "sources", "verification", "files"):
        if nm not in result:
            alias = {"polished_text": "polished_text", "change_log": "change_log", "facts_map": "facts_map", "glossary": "glossary", "human_review": "human_review"}.get(nm, nm)
            result[nm] = answers.get(nm, derive_field(alias, ctx)[1])
    for k, v in answers.items():
        result.setdefault(k, v)
    if case is not None and cid is None:
        unfilled.append("case_id")
    result["_meta"] = {"generator": "polish-guard/pg.py %s" % VERSION, "contract_fields": fields, "unfilled_fields": unfilled, "contract_found": bool(fields), "files": files}
    jsave(os.path.join(out, "result.json"), result)
    print(json.dumps({"written": out, "status": status, "changed_sentences": len(rows), "sentences": len(ed["sentences"]), "integrity_ok": not chk["integrity"], "rejected_edits": len([x for x in ed["rejected"] if not x.get("resolved")]), "unresolved_med_high": len(chk["unresolved"]),
                      "mechanical_open": len(chk["auto_left"]), "unfilled_contract_fields": unfilled, "contract_found": bool(fields), "polished": ctx["polished_file"]}, ensure_ascii=False))
    if unfilled:
        print("UNFILLED contract fields (put them in answers.json and re-run assemble --answers): " + ", ".join(unfilled))
    if not fields and a.case:
        print("WARNING: no output_contract found in the case file: read /input/case.json and task.md and add the fields by hand via --answers")
    sys.exit(0 if ((not unfilled and fields) or not a.case) else 2)


# ------------------------------------------------------------------------------------------------ main
def main(argv=None):
    ap = argparse.ArgumentParser(prog="pg.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def P(name, fn):
        p = sub.add_parser(name)
        p.set_defaults(fn=fn)
        return p
    p = P("prepare", cmd_prepare)
    p.add_argument("input", nargs="?")
    p.add_argument("--work", required=True)
    p.add_argument("--case")
    p.add_argument("--genre", choices=["journal", "thesis", "grant", "response", "abstract", "general"])
    p.add_argument("--lang", default="auto", choices=["auto", "en", "zh"])
    p = P("scan", cmd_scan)
    p.add_argument("work")
    p.add_argument("--cat")
    p.add_argument("--min-sev", dest="min_sev", default="low", choices=["low", "med", "high"])
    p.add_argument("--limit", type=int, default=40)
    p = P("show", cmd_show)
    p.add_argument("work")
    p.add_argument("--ids")
    p.add_argument("--par")
    p.add_argument("--issues", action="store_true")
    p.add_argument("--orig", action="store_true")
    p = P("autofix", cmd_autofix)
    p.add_argument("work")
    p.add_argument("--no-spelling", action="store_true")
    p.add_argument("--spelling", choices=["US", "UK"])
    p = P("ingest", cmd_ingest)
    p.add_argument("work")
    p.add_argument("file", nargs="?")
    p = P("next", cmd_next)
    p.add_argument("work")
    p = P("check", cmd_check)
    p.add_argument("work")
    p.add_argument("--limit", type=int, default=25)
    p.add_argument("--warnings", action="store_true")
    p = P("revert", cmd_revert)
    p.add_argument("work")
    p.add_argument("ids", nargs="+")
    p = P("status", cmd_status)
    p.add_argument("work")
    p = P("assemble", cmd_assemble)
    p.add_argument("work")
    p.add_argument("--out", required=True)
    p.add_argument("--case")
    p.add_argument("--answers")
    a = ap.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
