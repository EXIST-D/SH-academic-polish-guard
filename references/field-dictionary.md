# Field dictionary

## Work directory
`doc.json` - the document model: `format`, `file`, `lang`, `genre`, `paragraphs[]` {`id` P3, `kind` text | heading | frozen, `frozen_reason`, `section`, `start`/`end` (offsets in the source file; Word: in the paragraph text), `sentences[]` {`id` S012, `start`, `end`, `text`}}.
`edits.json` - `sentences{S012: {orig, cur, steps[{by autofix|term|model, type, rule, from, to, reason, warnings[]}], kept{rule: reason}, flags[]}}`, `terms[]`, `rejected[]` {sid, revised, errors[], resolved?}.

## Output files (`assemble --out OUT`)
| file | content |
|---|---|
| `polished.md` / `.txt` / `.tex` / `.docx` | the polished manuscript in the input's format; untouched characters unchanged |
| `polished_tracked_changes.docx` | Word only: insertions / deletions as tracked changes (author `polish-guard`) |
| `polished_text.txt` | Word only: plain text of the polished paragraphs |
| `changes.md`, `changes.json` | change log: sentence id, paragraph, section, original, revised, types, who (autofix / term / model), reasons, steps, edit ratio, risk flags, author flags |
| `redline.md`, `redline.html` | the whole text with deletions and insertions marked (word level) |
| `facts_map.json` | every citation / reference / number: original sentences, revised sentences, status (unchanged / MISSING in revision / not in original) |
| `glossary.json` | term decisions, open variants, abbreviations with their definitions and number of uses |
| `issues_remaining.json` | every issue still open on the final text (rule, category, severity, text, suggestion) |
| `review_checklist.md` | what a person must confirm |
| `check_report.json` | verification summary, rejected edits, remaining issues |
| `result.json` | contract fields (from `output_contract`) + `case_id`, `status`, `polished_text`, `change_log`, `facts_map`, `glossary`, `human_review`, `uncertainty`, `sources`, `verification`, `files`, `_meta` |

## `result.json`
Derivable contract names: `polished_text` / `revised_text` / `manuscript` / `target` (file + text), `change_log` / `changes` / `edits` / `revision_log`, `facts` / `fact_map` / `source_map`, `terminology` / `glossary`, `human_review` / `needs_review`, `uncertainty` / `boundaries`,
`sources`, `verification`, `redline`, `files`, `summary`, `status`. Other names are `null` and listed in `_meta.unfilled_fields` (supply them with `--answers answers.json`).
`status`: `success` (integrity intact, no mechanical issue left, no high-severity issue open) / `partial` (otherwise).
`uncertainty` lists: rejected edits, frozen paragraphs, integrity errors, open document-level items, Word formatting loss, input notes.

## Issue categories
`mechanical` (autofixable), `grammar`, `wording`, `concision`, `register`, `clarity`, `claim_strength` (flag only), `consistency` (document level: term_variants, spelling_mix, abbreviations, format_mix).
