# Failure modes -> what to do

| symptom | cause | action |
|---|---|---|
| `prepare`: no editable text / unsupported type | wrong file, empty file | report `failed`; supported: md, txt, tex, docx, pdf (text layer) |
| `prepare` on a scanned PDF: parser error or empty | no text layer | report the pages as not processed |
| many paragraphs `frozen` | LaTeX environments, tables, code, Word paragraphs with hyperlinks / fields | not edited by design; listed in `uncertainty`; polish them by hand if needed |
| edit REJECTED `protected_changed` | a citation / reference / math / URL differs | copy the protected token exactly (also inside `\cite{a,b}`); do not reorder the keys |
| edit REJECTED `number_changed` | a number or unit changed or vanished | keep every number and unit; `three` = `3` is fine, `5 mg` -> `5 g` is not |
| edit REJECTED `negation_changed` / `quantifier_changed` | not / no / never / all / some / only added or dropped | keep them; if the wording is wrong, fix the grammar around them |
| edit REJECTED `strengthened` / `weakened` | a hedge (may, suggest) removed or a booster added, or the opposite | keep the author's hedge; if you think the claim is too strong, `=== flag` it |
| edit REJECTED `causal_added` | "associated with" became "causes" / "because" added | keep the relation as the author wrote it |
| edit REJECTED `direction_changed` | an inverted comparison | keep the direction; "A is lower than B" must not become "B is lower than A" |
| edit REJECTED `rewrite` | > 85% of the tokens changed | polish only what is wrong, or give `rewrite: yes` with a reason |
| `autofix` skipped a sentence | the verifier found a meaning-bearing difference in the fix | leave it: it needs a decision (`show`, edit by hand) |
| open `claim_wording` issues | absolute / promotional wording | never change on your own: `=== flag` or `=== keep ... reason:` |
| `check` INTEGRITY errors | a citation or number of the original is missing in the revision | `revert` the sentence(s) responsible (`facts_map.json` lists the missing items) |
| `assemble` UNFILLED contract fields | field name not derivable | write the values to `answers.json`, re-run with `--answers` |
| Word file: formatting inside an edited paragraph lost | only the first run's formatting is kept | review the paragraph in `polished_tracked_changes.docx`; keep edits short in heavily formatted paragraphs |
