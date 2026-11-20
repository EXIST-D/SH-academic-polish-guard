#!/usr/bin/env python3
"""Evaluation of the meaning-preservation verifier and of the rule detectors on public data (JFLEG, Napoles et al. 2017: learner sentences with four human
fluency corrections each; CC BY-NC-SA 4.0) plus a hand-written set of academic sentences with seeded meaning changes.

Data: dev/ref/jfleg/{dev,test}.{src,ref0..ref3}   (https://github.com/keisks/jfleg)
 1. false alarms: the verifier is run on (source -> human correction) pairs. Human fluency corrections keep the meaning, so every ERROR is a false alarm.
 2. seeded meaning changes: one meaning-bearing change is injected into a human correction (negation dropped, number changed, quantifier swapped, hedge strengthened, ...)
    and the share caught as an ERROR is reported. Only references that contain the feature are used.
 3. academic set (dev/academic_set.py): 40 hand-written sentences x seeded changes, including causal / correlational wording, conditionals, direction, citations.
 4. precision of detector rules: a hit is 'true' when the matched phrase is changed by at least 2 of the 4 human corrections (the phrase is absent from them).
usage: jfleg_eval.py
"""
import os
import random
import re
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "submission", "scripts"))
sys.path.insert(0, HERE)
import detect  # noqa: E402
import protect  # noqa: E402

D = os.path.join(HERE, "ref", "jfleg")


def load():
    rows = []
    for sp in ("dev", "test"):
        src = open(os.path.join(D, sp + ".src"), encoding="utf-8").read().split("\n")
        refs = [open(os.path.join(D, "%s.ref%d" % (sp, k)), encoding="utf-8").read().split("\n") for k in range(4)]
        for i, s in enumerate(src):
            if s.strip():
                rows.append((s.strip(), [r[i].strip() for r in refs]))
    return rows


def errors(a, b, **kw):
    return {i["kind"] for i in protect.verify_edit(a, b, **kw) if i["severity"] == "error"}


MUT = {
    "negation dropped": lambda t: re.sub(r"\b(?:do|does|did|can|could|will|would|should|is|are|was|were|has|have|had)\s+not\b|n't\b|\bnot\b|\bnever\b|\bno\b", "", t, count=1) if re.search(r"\bnot\b|n't|\bnever\b|\bno\b", t) else None,
    "number changed": lambda t: re.sub(r"\d+", lambda m: str(int(m.group(0)) + 1), t, count=1) if re.search(r"\d+", t) else None,
    "quantifier swapped (all/some/most/few/only)": lambda t: (lambda x: x if x != t else None)(re.sub(r"\b(all|every)\b", "some", t, count=1) if re.search(r"\b(all|every)\b", t) else (re.sub(r"\bsome\b", "all", t, count=1) if re.search(r"\bsome\b", t) else (re.sub(r"\bmost\b", "few", t, count=1) if re.search(r"\bmost\b", t) else (re.sub(r"\bonly\b", "also", t, count=1) if re.search(r"\bonly\b", t) else t)))),
    "hedge strengthened (may/might/could -> will)": lambda t: re.sub(r"\b(may|might|could)\b", "will", t, count=1) if re.search(r"\b(may|might|could)\b", t) else None,
    "modal weakened (will/must -> may)": lambda t: re.sub(r"\b(will|must|should)\b", "may", t, count=1) if re.search(r"\b(will|must|should)\b", t) else None,
    "conditional dropped (if/unless/when)": lambda t: re.sub(r"\b(if|unless)\b", "because", t, count=1) if re.search(r"\b(if|unless)\b", t) else None,
    "direction inverted (increase<->decrease, more<->less)": lambda t: (re.sub(r"\bincreas\w*", "decreased", t, count=1) if re.search(r"\bincreas", t) else (re.sub(r"\bmore\b", "less", t, count=1) if re.search(r"\bmore\b", t) else (re.sub(r"\bbetter\b", "worse", t, count=1) if re.search(r"\bbetter\b", t) else None))),
}


def main():
    rows = load()
    print("JFLEG dev+test: %d sentences x 4 human corrections" % len(rows))
    fa, n, kinds = 0, 0, Counter()
    for s, refs in rows:
        for r in refs:
            if r == s:
                continue
            n += 1
            e = errors(s, r)
            fa += bool(e)
            kinds.update(e)
    print("1. false alarms on human corrections: %d / %d pairs with an error-level flag (%.1f%%); by kind: %s" % (fa, n, 100.0 * fa / n, dict(kinds.most_common(6))))
    print("   (rewrites above 85%% of the tokens are an error by design: JFLEG's fluency edits sometimes rewrite whole sentences)")
    fa2, n2 = 0, 0
    for s, refs in rows:
        for r in refs:
            if r == s or protect.edit_ratio(s, r) > 0.85:
                continue
            n2 += 1
            fa2 += bool(errors(s, r))
    print("   excluding the rewrites: %d / %d (%.1f%%)" % (fa2, n2, 100.0 * fa2 / n2))
    print("2. seeded meaning changes on human corrections (caught = any error-level flag):")
    rnd = random.Random(5)
    for name, fn in MUT.items():
        tot = hit = 0
        for s, refs in rows:
            r = rnd.choice(refs)
            if protect.edit_ratio(s, r) > 0.6:
                continue
            m = fn(r)
            if m is None or m == r:
                continue
            tot += 1
            hit += bool(errors(r, m) )
        print("   %-55s %4d cases  caught %.0f%%" % (name, tot, 100.0 * hit / tot if tot else 0))
    import academic_set
    print("3. academic sentences (hand-written) with seeded changes:")
    res = academic_set.run(errors)
    for name, (tot, hit, miss) in res["rows"].items():
        print("   %-55s %4d cases  caught %.0f%%" % (name, tot, 100.0 * hit / tot if tot else 0))
    print("   correct polishes of the same sentences flagged as error: %d / %d" % (res["fa"], res["fa_n"]))
    print("4. precision of detector rules against the human corrections (hit is true when >=2 of 4 corrections change the phrase):")
    per = defaultdict(lambda: [0, 0])
    for s, refs in rows:
        for i in detect.scan_sentence(s, "en", "journal"):
            if i["rule"] in ("a_an", "repeated_word", "agree_pl_subject2", "agree_pl_subject", "agree_sg_subject", "this_plural", "these_singular", "less_count", "much_count", "article_uncountable", "informations", "discuss_about", "other_hand", "different_with",
                             "can_not", "consist_passive", "double_connector", "mention_about", "emphasize_on", "depend_of", "similar_with", "perfect_past", "comprise_of", "composed_by", "reason_because", "contrary", "lowercase_start"):
                key = i["text"].strip().lower()
                changed = sum(1 for r in refs if key not in r.lower())
                per[i["rule"]][0] += 1
                per[i["rule"]][1] += changed >= 2
    for k, (h, tp) in sorted(per.items(), key=lambda kv: -kv[1][0]):
        print("   %-22s hits %4d  precision %.0f%%" % (k, h, 100.0 * tp / h))


if __name__ == "__main__":
    main()
