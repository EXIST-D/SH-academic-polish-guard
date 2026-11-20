# Minimal example (real output of the tool on FLAWED, INVENTED drafts)

`draft_en.md`, `draft_zh.md` and `draft_tex.tex` are invented manuscripts with deliberate problems; the findings and numbers are not real. Everything below is the output of the commands (long lines shortened with `...`). `example_output/` holds the files `assemble` wrote for the English draft. Nothing here is a result of a platform case.

## 1. Prepare the English draft
```bash
python3 scripts/pg.py prepare draft_en.md --work W
```
```text
{"ok": true, "work": "W/en", "file": "draft_en.md", "format": "md", "lang": "en", "genre": "journal", "paragraphs": 11, "editable_sentences": 32, "frozen_paragraphs": {}, "issues_by_category": {"wording": 5, "grammar": 4, "mechanical": 5, "register": 5, "concision": 1, "claim_strength": 3}, "document_level": {"spelling_mix": 1, "term_variants": 1, "abbr_before_definition": 1, "abbr_undefined": 1, "format_mix": 1}}
Next: `autofix` (safe mechanical fixes), `scan` (what needs a decision), `show`, write edits and `ingest` them, `check`, `assemble`.
```

## 2. Safe mechanical fixes (verified and logged)
```bash
python3 scripts/pg.py autofix W
```
```text
autofix: 5 mechanical fix(es) {'space_before_punct': 1, 'can_not': 1, 'micro_sign': 1, 'repeated_word': 1, 'a_an': 1}; 3 spelling change(s); 0 sentence(s) skipped by the verifier []
```

## 3. What still needs a decision
```bash
python3 scripts/pg.py scan W --limit 12
```
```text
9 sentence(s) with issues; 0 mechanical issue(s) can be fixed by `autofix`
S025 [P9 | Results] This results shows that YAP is very important for the stiffness response.
    - grammar/high this_plural: 'This results'  (this / that with a plural noun (these / those?))
    - grammar/high agree_pl_subject2: 'results shows'  (plural subject with a singular verb)
    - register/low register: 'very '  (intensifier: quantify or drop)
S029 [P11 | Discussion] We didn't test in vivo scaffolds, but this will be a huge breakthrough in the future!
    - register/med register: 'didn't'  (contraction in formal writing)
    - register/low register: 'huge'  (vague size word: give the size)
    - claim_strength/med claim_wording: 'breakthrough'  (promotional wording (do not weaken or strengthen on your own: flag for the author))
    - register/med register: '!'  (exclamation mark in academic text)
S003 [P3 | Abstract] With the development of tissue engineering, more and more researchers pay attention to the substrate stiffness.
    - wording/med wordy: 'With the development of' -> As X develops / Advances in X  (wordy / translationese pattern)
    - wording/med wordy: 'more and more' -> increasingly  (wordy / translationese pattern)
S009 [P5 | Introduction] It is well known that substrate stiffness plays an important role in stem cell fate [1,2].
    - wording/med wordy: 'It is well known that' -> delete, or cite the source  (wordy / translationese pattern)
    - wording/med wordy: 'plays an important role in' -> is important for / contributes to (say what it does)  (wordy / translationese pattern)
S012 [P5 | Introduction] Because the osteoblast data set is small, so we used a lot of replicates.
    - wording/med double_connector: 'Because the osteoblast data set is small, so'  (two connectors for one relation (although ... but / because ... so))
    - register/med register: 'a lot of'  (informal quantifier)
S028 [P11 | Discussion] Our findings are completely different from the opinion that stiffer matrices always promote osteogenic differentiation.
    - claim_strength/med claim_wording: 'completely'  (absolute wording (do not weaken or strengthen on your own: flag for the author))
    - claim_strength/med claim_wording: 'always'  (absolute wording (do not weaken or strengthen on your own: flag for the author))
S005 [P3 | Abstract] The mineralised nodule area on 10 kPa gels were 2.3-fold higher than that on 40 kPa gels (p = 0.004, n = 6).
    - grammar/med agree_sg_head_pl_verb: 'area on 10 kPa gels were'  (singular head noun with a plural verb after a prepositional phrase)
S011 [P5 | Introduction] However, direct tests on primary osteoblasts is scarce.
    - grammar/med agree_pl_subject: 'tests on primary osteoblasts is'  (possible subject-verb disagreement (plural subject with a singular verb after a prepositio)
S018 [P7 | Methods] In order to evaluate YAP, nuclear localisation was scored by immunofluorescence in at least 200 nuclei per gel.
    - concision/low wordy: 'In order to' -> to  (wordy / translationese pattern)

DOCUMENT-LEVEL (3)
  - term_variants: same term written differently: 'data set' (1); 'data-set' (1)  -> choose one form (suggested: 'data set')
  - abbr_before_definition: CNN is used before its definition (S031)  -> define at first use
  - abbr_undefined: YAP is used 6 times and never defined  -> define at first use unless it is standard in the field
  decide with `=== term` blocks (canonical + variants) or `autofix` (spelling); abbreviations: define at first use in an edit
```

## 4. Submit edits (`edits_en.txt`). Note the REJECTED line: that edit dropped 'always' from the author's claim, so the original sentence is kept
```bash
python3 scripts/pg.py ingest W edits_en.txt
```
```text
applied 9 edit(s) | rejected 1 | kept 1 | flagged 1 | terms 1 | bad 0
  S003 WARN content_dropped: content words dropped: attention, develop, pay
  S003 WARN content_added: new content words (not in the original): advanc, increasing, interest: no new information may be added
  S009 WARN content_dropped: content words dropped: important, play, role, well
  S012 WARN content_dropped: content words dropped: data, lot, set
  S028 REJECTED (original kept): quantifier_changed: quantifier class changed: removed universal; added - (all / some / most / few / only are different claims)
  term 'dataset': 1 replacement(s) in 1 sentence(s)
```

## 5. Whole-document check
```bash
python3 scripts/pg.py check W
```
```text
sentences: 32 | changed: 15 (47%) | mean edit ratio of changed sentences 0.17 | tokens 463 -> 444
INTEGRITY (whole document): OK - every citation, reference, number and unit of the original is still there
rejected edits (original kept, not yet superseded): 1 | edits with warnings: 5 | flagged for the author: 1
unresolved issues (med/high, not fixed or kept): 1 | mechanical issues still open: 0 | document-level items: 2
  S029 claim_strength/med claim_wording: 'breakthrough'
  DOC abbr_before_definition: CNN is used before its definition (S031)
  DOC abbr_undefined: YAP is used 6 times and never defined
```

## 6. Assemble
```bash
python3 scripts/pg.py assemble W --out example_output
```
```text
{"written": "example_output", "status": "success", "changed_sentences": 15, "sentences": 32, "integrity_ok": true, "rejected_edits": 1, "unresolved_med_high": 1, "mechanical_open": 0, "unfilled_contract_fields": [], "contract_found": false, "polished": "polished.md"}
```

## What changed (`example_output/changes.md`, first rows)
```text
# Change log

| id | type | original | revised | reason | risk |
|---|---|---|---|---|---|
| S003 | wording | With the development of tissue engineering, more and more researchers pay attention to the substrate stiffness. | With advances in tissue engineering, researchers are increasingly interested in substrate stiffness. | replaces the template opening "With the development of ... more and more ... pay attention to" with direct academic phrasing; meaning unchanged | content_dropped; content_added |
| S005 | grammar | The mineralised nodule area on 10 kPa gels were 2.3-fold higher than that on 40 kPa gels (p = 0.004, n = 6). | The mineralised nodule area on 10 kPa gels was 2.3-fold higher than that on 40 kPa gels (p = 0.004, n = 6). | subject-verb agreement (area ... was) | - |
| S006 | grammar, spelling | Nuclear YAP localization was lower on soft gels, which suggests that YAP signaling may mediate a part of the stiffness response [3]. | Nuclear YAP localisation was lower on soft gels, which suggests that YAP signalling may mediate part of the stiffness response [3]. | UK spelling used throughout: localization -> localisation; signaling -> signalling; "a part of" -> "part of"; spelling made consistent | - |
| S007 | mechanical | The effect was not observed in a human cell line , so the results can not be generalised to all cell types. | The effect was not observed in a human cell line, so the results cannot be generalised to all cell types. | space_before_punct: ' ,' -> ','; can_not: 'can not' -> 'cannot' | - |
| S009 | wording | It is well known that substrate stiffness plays an important role in stem cell fate [1,2]. | Substrate stiffness is known to influence stem cell fate [1,2]. | "It is well known that ... plays an important role in" is a template phrase; the cited claim is kept | content_dropped |
| S011 | grammar | However, direct tests on primary osteoblasts is scarce. | However, direct tests on primary osteoblasts are scarce. | plural subject "tests" needs "are" | - |
| S012 | grammar | Because the osteoblast data set is small, so we used a lot of replicates. | Because the osteoblast dataset is small, we used many replicates. | "because ... so" double connector removed; "a lot of" is informal; "data set" unified | content_dropped |
```

## Redline of one paragraph (`example_output/redline.md`)
```text
**P5** ~~It~~**Substrate stiffness** is ~~well~~ known ~~that~~**to** ~~substrate stiffness plays an important role in~~**influence** stem cell fate [1,2]. Engler et al. showed that matrix elasticity directs lineage specification of mesenchymal stem cells [2]. However, direct tests on primary osteoblasts ~~is~~**are** scarce. Because the osteoblast ~~data set~~**dataset** is small, ~~so~~ we used ~~a lot of~~**many** replicates. The ~~data-set~~**dataset** was described in Table 1.
```

## Chinese draft: prepare, autofix, scan
```bash
python3 scripts/pg.py prepare draft_zh.md --work W2
python3 scripts/pg.py autofix W2
python3 scripts/pg.py scan W2 --limit 5
```
```text
{"ok": true, "work": "W/draft_zh", "file": "draft_zh.md", "format": "md", "lang": "zh", "genre": "journal", "paragraphs": 5, "editable_sentences": 13, "frozen_paragraphs": {}, "issues_by_category": {"wording": 5, "mechanical": 2, "register": 2, "grammar": 1, "claim_strength": 2}, "document_level": {
Next: `autofix` (safe mechanical fixes), `scan` (what needs a decision), `show`, write edits and `ingest` them, `check`, `assemble`.
autofix: 3 mechanical fix(es) {'zh_period_end': 1, 'zh_comma': 1, 'zh_ji_yu': 1}; 0 spelling change(s); 0 sentence(s) skipped by the verifier []
5 sentence(s) with issues; 0 mechanical issue(s) can be fixed by `autofix`
S010 [P5 | 讨论] 由于样本量比较小，所以我们用了很多很多重复。
    - wording/med zh_wording: '由于样本量比较小，所以'  (「由于…所以」双重连接词)
    - register/high zh_register: '很多很多'  (口语化)
S011 [P5 | 讨论] 在前人的研究的基础上，我们认为 YAP 非常非常重要。
    - register/high zh_register: '非常非常'  (口语化)
S003 [P3 | 摘要] 随着组织工程的快速发展，越来越多的研究者对基质硬度进行了研究。
    - wording/med zh_wording: '随着组织工程的快速发展'  (套话开头：说明具体变化并给出依据)
    - wording/med zh_wording: '进行了研究'  (名词化：「进行研究/分析」可改为动词「研究/分析」)
S009 [P5 | 讨论] 众所周知，基质硬度对干细胞命运起到了重要的作用 [1,2]。
    - wording/med zh_wording: '众所周知'  (绝对化/套话：删除或给出依据)
    - wording/med zh_wording: '起到了重要的作用'  (套话：说明具体作用)
S012 [P5 | 讨论] 本研究的发现完美地推翻了硬基质总是促进成骨分化的观点，这将是一个颠覆性的突破。
    - claim_strength/med zh_claim_strength: '完美'  (绝对化/宣传化措辞：需要证据支撑，润色不得擅自加强或削弱)
    - claim_strength/med zh_claim_strength: '颠覆性'  (绝对化/宣传化措辞：需要证据支撑，润色不得擅自加强或削弱)

DOCUMENT-LEVEL (0)
```

## LaTeX draft: prepare, autofix, scan
```bash
python3 scripts/pg.py prepare draft_tex.tex --work W2
python3 scripts/pg.py autofix W2
python3 scripts/pg.py scan W2 --limit 5
```
```text
{"ok": true, "work": "W/draft_tex", "file": "draft_tex.tex", "format": "tex", "lang": "en", "genre": "abstract", "paragraphs": 3, "editable_sentences": 5, "frozen_paragraphs": {"LaTeX environment": 1}, "issues_by_category": {"wording": 2, "grammar": 1, "mechanical": 1, "register": 2, "claim_strength
Next: `autofix` (safe mechanical fixes), `scan` (what needs a decision), `show`, write edits and `ingest` them, `check`, `assemble`.
autofix: 1 mechanical fix(es) {'a_an': 1}; 0 spelling change(s); 0 sentence(s) skipped by the verifier []
3 sentence(s) with issues; 0 mechanical issue(s) can be fixed by `autofix`
S003 [P1 | (start)] The results shows that pruning may be more effective than quantization, which is an obvious advantage.
    - grammar/high agree_pl_subject2: 'results shows'  (plural subject with a singular verb)
S005 [P3 | (start)] We didn't evaluate on ImageNet-21k, but this will be a huge breakthrough.
    - register/med register: 'didn't'  (contraction in formal writing)
    - register/low register: 'huge'  (vague size word: give the size)
    - claim_strength/med claim_wording: 'breakthrough'  (promotional wording (do not weaken or strengthen on your own: flag for the author))
S001 [P1 | (start)] With the development of deep learning, more and more researchers pay attention to the model compression \cite{han2016,hinton2015}.
    - wording/med wordy: 'With the development of' -> As X develops / Advances in X  (wordy / translationese pattern)
    - wording/med wordy: 'more and more' -> increasingly  (wordy / translationese pattern)

DOCUMENT-LEVEL (0)
```
