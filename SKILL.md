---
name: academic-polish-guard
description: Polish an academic manuscript (English or Chinese; Markdown, plain text, LaTeX, Word .docx, or a PDF's text; abstract, journal paper, thesis, grant proposal, response to reviewers) without changing what it says. Rules find mechanical errors, grammar patterns, translationese / wordiness, register problems, over-claiming wording and document-level inconsistencies (term variants, US/UK spelling, abbreviations used before definition, number formats); safe mechanical fixes are applied and logged; every edit you write is verified against the original (citations, figure/table/equation references, math, numbers and units, negation, quantifiers and bounds, hedge strength, causal vs correlational wording, conditionals, direction of change, size of the edit) and rejected if it changes the meaning. Output is written back in the same file format with every untouched character unchanged (Word: tracked changes), plus a change log (original / revised / type / reason / risk), a facts map, a glossary and a review checklist. Use whenever a task asks to polish, proofread, copy-edit, unify terminology, fix grammar, or improve the academic tone of a manuscript while keeping facts, numbers, citations and claim strength intact.
---

# academic-polish-guard

You decide how the text should read; the tool makes sure the polish **did not change what it says**. It finds the problems, fixes the mechanical ones safely, **verifies every edit against the
original**, writes the result back into the same file format, and produces the change log a reviewer needs (original / revised / type / reason / risk).

## When to use
A manuscript must be polished: grammar, collocations, punctuation, wording, academic register, terminology and spelling consistency - while facts, numbers, citations, claim strength and structure stay as written.
English and Chinese. Not for translation or for adding content (it never adds facts; new content words and terms are flagged).

## Quick start (`SK` = directory of this file, installed as `/skills/weekly-skill`; `W=/app/work/pg`)
```bash
python3 $SK/scripts/pg.py prepare /input/<file> --work $W --case /input/case.json [--genre journal|thesis|grant|response|abstract]   # or: prepare --work $W --case ... (finds the file / text itself)
python3 $SK/scripts/pg.py autofix $W                       # safe mechanical fixes + one US/UK spelling + one percent format (verified, logged)
python3 $SK/scripts/pg.py scan $W --limit 40               # what needs a decision: sentence issues + document-level consistency
python3 $SK/scripts/pg.py show $W --issues                 # current text of the sentences with open issues (ids S001...)
python3 $SK/scripts/pg.py ingest $W <<'EOF'                # your edits (format below): each is verified against the ORIGINAL sentence
=== edit S012
revised: ...
type: grammar
reason: ...
EOF
python3 $SK/scripts/pg.py check $W                         # integrity of the whole document + what is still open
python3 $SK/scripts/pg.py assemble $W --out /app/output --case /input/case.json
```
Also: `next W` (to-do list), `show W --ids S010-S020 --orig`, `revert W S012`, `status W`. `prepare` takes `.md .txt .tex .docx .pdf`; a PDF is delivered as Markdown (formatting is lost).

## Procedure (budget: 64 requests; typically 10-16)
1. **Read the task** (`/input/case.json`, `task.md`): genre (journal / thesis / grant / response / abstract), language, house style, what must not change, exact `output_contract`. `prepare` prints the task text, the number of editable sentences,
   frozen paragraphs (code, tables, equations, reference lists, complex Word paragraphs: never edited) and the issue counts.
2. **`autofix`**: spacing / punctuation, repeated words, a/an, unambiguous collocations (`informations`, `discuss about`, `in the other hand`), `can not`, `1 uM`; Chinese: full-width punctuation, duplicated particles; plus one spelling convention
   (the majority) and one percent format. Each fix is checked and logged; nothing is applied that would change a number, a citation or a hedge.
3. **`scan`**, then **`show --issues`**; fix what the rules found **and** what you notice yourself. Decide, in this order: grammar errors (agreement, articles, collocations) -> translationese / wordiness -> register (contractions, intensifiers,
   informal words) -> terminology (`=== term` blocks) -> abbreviations (define at first use inside an edit) -> clarity of long sentences.
4. **Write edits** in the block format below - **minimal edits**: change only what is wrong, keep the author's words where they are correct, keep sentence order. One `ingest` with 10-25 edits; read the REJECTED lines and redo only those.
5. **Claim-strength wording** (`absolute`, `promotional`, novelty claims: always, completely, breakthrough, 完美, 颠覆性): never strengthen or weaken it on your own. Use `=== flag S.. note: ...` (author decides) or `=== keep S.. rule: claim_wording reason: ...`.
6. **`check`**: whole-document integrity (every citation, reference, number and unit of the original must still exist), unresolved issues, edits with warnings. Fix, `assemble`.
7. **Report honestly**: status (`success` only if integrity is intact, no mechanical issue is left and no high-severity issue is open; else `partial` with the reasons), rejected edits, flagged items, what was not edited.

## Edit blocks (no JSON escaping)
```
=== edit S012                       <- a sentence id from `show`; S012-S013 merges / re-splits two sentences into the revised text
revised: The full revised sentence(s) - plain text exactly as it should appear in the file (LaTeX commands, [12], Fig. 3 stay).
type: grammar | punctuation | term | register | wording | clarity | concision | style | consistency | spelling | translation
reason: why this change (the reviewer reads it)          <- required
rewrite: yes                         <- only if a heavy rewrite is justified (otherwise > 85% changed tokens is rejected)
=== term                             <- unify a term everywhere (case-aware, protected spans untouched)
canonical: dataset
variants: data set; data-set
reason: one spelling throughout
=== keep S028
rule: claim_wording                  <- an issue you looked at and deliberately leave (rule id from `scan`; omit for all rules)
reason: the author's claim, not a style choice
=== flag S029
note: needs author confirmation: ...
```
Mechanical issues are not worth an edit block: `autofix` handles them. `show W --ids S012 --orig` shows the original next to the current text.

## What the verifier checks for every edit (error = rejected, the original is kept; warn = accepted and listed as a risk)
| class | error when |
|---|---|
| protected spans | a citation `[12]` / `(Smith et al., 2020)`, `Fig. 3` / `Table 2` / `Eq. (4)` / `图3`, LaTeX `\cite{}` `\ref{}`, math, code or URL differs |
| numbers & units | a number or unit differs (three = 3 is fine; `uM` = `μM`) |
| negation | the count of negations differs |
| quantifiers & bounds | all / some / most / few / only changed; at least / at most / about / more than / exactly changed |
| strength | a hedge (may, might, could, suggest, probably) removed or a booster (clearly, proves, certainly) added; or the opposite |
| `significant(ly)` | added or removed (statistical claim) |
| causal vs correlational | causal wording added or an association turned into a cause (warn if causal wording is removed) |
| conditionals | if / unless / when / provided that changed in number |
| direction | an inverted comparison (increase <-> decrease, higher <-> lower) |
| size of edit | > 85% of the tokens changed (warn above 60%); content words dropped or added, new terms / abbreviations (warn) |
Spelling slips in the original ("beacuse") are read as the intended word, so correcting them is not mistaken for a new claim.

## Frozen and format handling
Markdown / text / LaTeX: untouched characters stay byte-identical; headings are editable one-sentence units; code blocks, tables, math, LaTeX environments and preambles, reference lists are frozen. Word: only plain paragraphs are edited
(paragraphs with hyperlinks, fields, drawings, footnotes are frozen); `polished_tracked_changes.docx` shows insertions / deletions in Word, `polished.docx` has them accepted; inside an edited paragraph only the first run's character formatting is kept.

## Exceptions
| Situation | Behaviour | You do |
|---|---|---|
| no editable text / unsupported file | `prepare` stops with the reason | report `failed`; do not invent a manuscript |
| scanned PDF | no text layer: parser error / empty | report the pages as not processed (OCR belongs to a reading skill) |
| an edit is rejected | the original sentence is kept, the reason is printed and logged | redo with the original wording of the flagged element, or `=== flag` |
| the author's wording is probably wrong but you are unsure | `=== flag S.. note:` | never "fix" content; list it for the author |
| facts (numbers, citations) seem inconsistent inside the manuscript | not changed | flag; never harmonise numbers yourself |
| mixed languages in one document | `--lang` applies to the whole file | split the file or set the language of the main text |

## Dependencies
Python 3.8+, standard library only. `.docx` is read and written with the standard library (zipfile / XML); PDFs use the bundled `scripts/parse_pdf.py` (needs `pymupdf`, falls back to `pdfplumber` / `pypdf`). No network.

## Honesty rules (hard)
Never add facts, numbers, citations or terms that are not in the manuscript; never change claim strength; never silently drop a sentence; never hide a rejected edit; say what the checks cannot prove (they are lexical: the review checklist lists what a human must confirm);
never state scores - the platform records them.

More: `README.md`, `references/` (field dictionary, checks with measured results, detector rules, genre guide, failure modes, method notes), `examples/` (flawed English / Chinese / LaTeX drafts, an edit file, real run output).
