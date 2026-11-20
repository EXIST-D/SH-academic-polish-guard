# Method notes

## Mapping of the four questions
1. **Correct fixes** - mechanical errors are repaired by rules with a proof (the verifier must find no meaning-bearing difference); grammar and collocation patterns are reported with the matched text so that a fix is a real fix, not a paraphrase;
   edits are scored against the original, and an edit that only rephrases (more than 85% of the tokens) is rejected.
2. **Sounds like academic writing** - genre rules (journal / thesis / grant / response / abstract), register lexicons (contractions, intensifiers, informal quantifiers), translationese and wordiness tables, document-level terminology, spelling,
   abbreviation and format consistency, with deterministic application (`=== term`, one spelling convention).
3. **Nothing broken** - the verifier compares the meaning-bearing inventory of the original and the revision (see `checks.md`); whole-document integrity re-counts citations, references and numbers; untouched characters of the file stay identical;
   frozen paragraphs are not editable; claim-strength wording is flagged, never changed.
4. **Explained** - every change has original / revised / type / reason / who made it (autofix, term, model) / risk flags; `redline.md` / `redline.html` / tracked-changes `.docx` show it in place; `facts_map.json` maps every number and citation to the sentences
   before and after; `review_checklist.md` lists what a person must confirm.

## What is computed and what is judged by the model
Computed: segmentation, protected spans, issue detection, mechanical fixes, terminology / spelling unification, verification, integrity, write-back, change log. Judged by the model: grammar fixes that need understanding, wording, tone, clarity,
terminology choices, which claim-strength wordings to flag. The checks are lexical: they catch dropped negations, changed numbers, strengthened claims, swapped directions, not every shift in meaning.

## Budget
64 requests: `prepare` (1), `autofix` + `scan` (1-2), `show` (1-3), `ingest` (2-5), `check` (1), `assemble` (1) = about 10-16. Estimated from the procedure, not measured on the platform.

## Known limits
- English markers are exact word lists; other languages are not covered. Chinese has the same inventory but fewer rules (no a/an, no agreement).
- Agreement and collocation rules are patterns: they miss errors that need parsing and can fire on legitimate uses (e.g. `data is`); every report is a suggestion.
- A meaning change expressed without marker words (a swapped subject and object, a changed unit name) is not caught unless numbers, protected spans or content words change.
- Terminology drift is found for 1-3 word terms that differ in case / hyphen / spacing; synonyms (method / approach / technique) are not unified automatically.
- Word: runs inside an edited paragraph are merged (only the first run's formatting survives); fields, hyperlinks, footnotes and drawings are in frozen paragraphs. Tracked changes were validated structurally (accept-all / reject-all of the XML), not opened in Word.
- PDF input is plain text extraction; the polish is delivered as Markdown.
- The verifier was tuned on JFLEG and on my own sentences; thresholds (85% / 60% edit ratio) are defaults, not laws.
