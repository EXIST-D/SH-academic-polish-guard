#!/usr/bin/env python3
"""Generate references/rules.md from the rule tables of detect.py so that the documentation cannot drift from the code."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "submission", "scripts"))
import detect  # noqa: E402

L = ["# Detector rules", "", "All rules are plain data in `scripts/detect.py`: add or change entries for a field or a house style. Protected spans (citations, references, math, code, URLs) are masked before any rule runs.", "",
     "## Mechanical rules with a safe fix (`autofix`)", "| rule | what | example of the match |", "|---|---|---|"]
for r in detect.AUTO_EN:
    L.append("| `%s` | %s | `%s` |" % (r["id"], r["msg"], r["rx"].pattern[:60].replace("|", "\\|")))
L += ["| `repeated_word` | repeated word (except had had / that that / is is ...) | `the the` |", "| `a_an` | a / an by the sound of the next word (acronyms by letter name: an FPGA, a CNN; digits: an 8, a 10) | `a obvious` |", "",
      "Chinese: " + "; ".join("`%s` %s" % (r["id"], r["msg"]) for r in detect.AUTO_ZH) + ".", "",
      "## Grammar patterns (reported, you decide)", "| rule | severity | what |", "|---|---|---|"]
for r in detect.SUGGEST_EN:
    L.append("| `%s` | %s | %s |" % (r["id"], r["sev"], r["msg"]))
L += ["", "## Wordiness / translationese patterns (reported with a suggestion)", "| pattern | suggestion | category |", "|---|---|---|"]
for pat, sug, cat, sev in detect.WORDY_EN:
    L.append("| `%s` | %s | %s/%s |" % (pat.replace("|", "\\|"), sug, cat, sev))
L += ["", "## Register", "| pattern | message | severity |", "|---|---|---|"]
for pat, msg, cat, sev in detect.REGISTER_EN:
    L.append("| `%s` | %s | %s |" % (pat[:70].replace("|", "\\|"), msg, sev))
L += ["", "## Claim-strength wording (never changed by the polish; flagged for the author)", "| pattern | message |", "|---|---|"]
for pat, msg in detect.CLAIM_EN:
    L.append("| `%s` | %s |" % (pat[:80].replace("|", "\\|"), msg))
L += ["", "## Chinese suggestions", "| pattern | message | category |", "|---|---|---|"]
for pat, msg, cat, sev in detect.SUGGEST_ZH:
    L.append("| `%s` | %s | %s/%s |" % (pat[:60].replace("|", "\\|"), msg, cat, sev))
L += ["", "## Document-level consistency (`scan`)", "- **term_variants**: the same 1-3 word term written in different ways (case, hyphen, spacing; singular / plural alone are not drift). Resolve with `=== term`.",
      "- **spelling_mix**: US (-ize, -yze, color, center, modeling ...) and UK (-ise, -yse, colour, centre, modelling ...) conventions in one document; `autofix` converts the minority to the majority (or `--spelling US|UK`).",
      "- **abbr_before_definition / abbr_redefined / abbr_conflict / abbr_undefined**: abbreviations defined as `Long Form (ABBR)` (Schwartz-Hearst matching), used before the definition, defined twice, expanded in two ways, or used repeatedly without a definition.",
      "- **format_mix**: `10%` vs `10 %`, `Fig.` vs `Figure`, `et al.` vs `et al` (percent format is unified by `autofix`).", ""]
open(os.path.join(HERE, "..", "submission", "references", "rules.md"), "w", encoding="utf-8").write("\n".join(L))
print("written")
