# Genre guide (`prepare --genre`)

The genre decides which register rules fire. The default is guessed from the task text (grant / proposal, response to reviewers, thesis / dissertation, short text without headings = abstract; otherwise journal).

| genre | person | other expectations the rules check |
|---|---|---|
| `journal` | `we` for several authors, passive or `this study` as the field prefers; first-person singular `I` is reported (low); `I think / we feel` is reported (opinion verb) | no contractions, no intensifiers (very, quite), no informal quantifiers (a lot of), no exclamation marks; claim-strength wording is flagged for the author |
| `abstract` | like journal | additionally: abbreviations must be defined (checked at document level); no citations expected; short sentences preferred (long relative clauses reported) |
| `thesis` | `I` is allowed in some disciplines (reported as low: check the house style) | same as journal; consistency of terms and abbreviations across chapters matters most (document-level scan) |
| `grant` | `we` / `I` allowed (not reported) | promotional wording is still flagged: reviewers read superlatives as unsupported claims; priority and novelty claims need support |
| `response` | `we` allowed; polite phrases are kept | contractions and informal wording are reported; never change what the authors say they changed (numbers, section references, line numbers stay) |
| `general` | not judged | only mechanical, grammar and consistency rules |

Chinese manuscripts use the Chinese rule set: full-width punctuation, duplicated particles / punctuation, `基于...的基础上`, nominalisation (`进行了研究`), template openings (`随着...的发展`), colloquial words, absolute wording (flagged, not changed).
For English drafts translated from Chinese the wordiness table covers the usual translationese: with the development of, more and more, play an important role, it can be seen that, according to ... it can be concluded, because ... so, although ... but.
