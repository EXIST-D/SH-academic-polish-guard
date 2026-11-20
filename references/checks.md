# Verification of edits (`ingest`) and of the document (`check`, `assemble`)

Severity: **error** = the edit is rejected and the original sentence stays; **warn** = accepted and listed in the change log as a risk.
Each edit is compared with the ORIGINAL sentence (not with the previous edit), so a chain of edits cannot drift.

| kind | severity | rule | known blind spots |
|---|---|---|---|
| `protected_changed` | error | the multiset of citations (`[12]`, `(Smith et al., 2020)`), figure / table / equation / section references (`Fig.` = `Figure`), LaTeX `\cite \ref \label \url`, math, code, URLs differs | a citation moved to another sentence is caught only by the whole-document integrity check |
| `number_changed` | error | the multiset of (number, unit) differs; spelled-out numbers count (three = 3); `uM` = `μM`; thousands separators ignored | numbers written as words above twelve; ordinals |
| `negation_changed` | error | the number of negation words differs (not, no, never, without, cannot, fail to, lack, unlikely, 不, 没有, 无 ...) | double negation rewritten with the same count |
| `quantifier_changed` | error | a quantifier class was added or removed: universal (all, every, each, always), existential (some, several, certain), majority (most, main), minority (few, little), exclusive (only, solely) | `many / a lot of` is only a warning (`quantity_changed`) |
| `bound_changed` | error | at least / at most / more than / less than / up to / about + number / approximately / exactly / exceeds ... changed (approximation words are interchangeable) | bounds without these words |
| `strengthened` / `weakened` | error | a hedge (may, might, could, can, suggest, indicate, probably, likely, seem) was removed or a booster (prove, certainly, obviously, definitely) added, or the opposite; `will / must / should / demonstrate` changes alone are a warning (`hedge_changed`) | strength carried by other words (verbs of reporting, adjectives) |
| `significance_changed` | error | `significant(ly)` / 显著 added or removed | - |
| `causal_added` / `correlation_to_causation` | error | causal wording (cause, lead to, result in, because, since, due to, induce, play a role in ...) added, or correlational wording (associated with, correlated with, linked to) replaced by causal wording | causal meaning without these words |
| `causal_removed` | warn | causal wording removed | - |
| `conditional_changed` | error | the number of conditional / temporal-conditional markers (if, unless, when, provided that, only if, 如果, 若, 除非 ...) differs | - |
| `direction_changed` | error / warn | error when the direction of change is inverted (increase <-> decrease, higher <-> lower, better <-> worse, 增加 <-> 降低); warn when a direction word was added or dropped | direction carried by nouns |
| `comparison_changed` | warn | the number of comparison markers (than, compared with, versus) differs | - |
| `rewrite` / `heavy_edit` | error / warn | more than 85% / 60% of the tokens changed (override: `rewrite: yes`) | - |
| `content_dropped` / `content_added` / `term_added` / `term_dropped` | warn | content words, named terms or abbreviations disappeared or appeared (no new information may be added) | - |
| `new_issue` | warn | the revision introduces a grammar / mechanical / claim-wording issue that the sentence did not have | - |
| whole-document integrity (`check`, `assemble`) | error | the document-level multiset of protected spans or numbers differs from the original (a deleted sentence, a moved citation) | numbers inside frozen paragraphs are not compared (they are never edited) |

Frozen paragraphs are never edited. Spelling slips in the original (`beacuse`, `incresed`) are read as the intended marker word, so correcting a typo does not look like a new claim.

## Measured behaviour (development tests; not platform scores)
`dev/jfleg_eval.py`, public data: **JFLEG** (Napoles et al. 2017; 1,501 learner sentences with four human fluency corrections each; CC BY-NC-SA 4.0) and 40 hand-written academic sentences with minimal legitimate polishes.

**Seeded meaning changes** (one change injected into a human correction; caught = any error-level flag):

| injected change | JFLEG corrections | academic sentences |
|---|---|---|
| negation dropped | 80 % (334 cases) | 100 % (7) |
| number changed / unit changed | 93 % (27) | 100 % (25) / 100 % (6) |
| quantifier swapped (all / some / most / few / only) | 100 % (227) | 100 % (9) |
| hedge strengthened (may / might / could -> will) | 100 % (94) | 100 % (7) |
| modal weakened (will / must -> may) | 98 % (254) | - |
| conditional dropped or changed | 100 % (87) | 100 % (5) |
| direction inverted | 95 % (184) | 100 % (13) |
| citation / figure reference changed | - | 100 % (10) |
| causal wording added to an association | - | 100 % (3) |
| bound changed (at least -> at most ...) | - | 100 % (6) |

**False alarms**: on the 40 correct academic polishes 0 are flagged as an error. On JFLEG's human corrections 15 % (779 of 5,175 pairs) carry an error-level flag. JFLEG is a hard test for a meaning guard: its editors rewrite learner sentences
freely and often change meaning-bearing words (a sample of 14 flagged pairs read by the author: about half were real changes of hedge, quantifier or causal wording, the rest equivalences such as *instead of / other than*, *every area / everywhere*).
The verifier was tuned after inspecting a random sample of flagged JFLEG pairs, so the 15 % is not an independent estimate.

**Detector precision** against the same human corrections (a hit counts as true when at least 2 of the 4 corrections change the phrase): `a_an` 100 % (17 hits), `informations` 100 % (9), `article_uncountable` 100 % (4), `double_connector` 100 % (3), `repeated_word` 73 % (11),
`lowercase_start` 70 % (175); `can_not` 36 % (25; the human editors often keep `can not`, so `can not only` is excluded and the rule is reported as mechanical). Rules with few hits (agreement patterns) cannot be assessed on this corpus.
