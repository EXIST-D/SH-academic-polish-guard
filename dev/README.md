# dev/ - tests and evaluations of academic-polish-guard (not part of the Skill runtime)

| file | what |
|---|---|
| `test_all.py` | 18 regression tests (stdlib `unittest`): verifier pass / reject cases, detector rules, protected spans untouched by autofix, Markdown round trip with untouched text identical, unsafe edit rejected and original kept, term / spelling unification, LaTeX command protection and environment freezing, Chinese, Word tracked changes (XML accept-all / reject-all, frozen hyperlink paragraph), contract fields. `python3 dev/test_all.py` |
| `jfleg_eval.py` | false alarms, seeded meaning changes and detector precision on JFLEG + the academic set; result in `jfleg_eval_result.txt` |
| `academic_set.py` | 40 hand-written academic sentences with a minimal legitimate polish each, and the mutation tables used to seed meaning changes |
| `make_docx.py` | builds a small .docx with the standard library (heading, bold run, hyperlink paragraph, table paragraph) for the tests |
| `make_example.py`, `make_docs.py` | regenerate `examples/minimal-example.md`, `examples/example_output/` and `references/rules.md` from real runs / the rule tables |

## Reproduce the JFLEG evaluation
JFLEG (Napoles, Sakaguchi, Tetreault 2017; https://github.com/keisks/jfleg; CC BY-NC-SA 4.0): download `dev/` and `test/` files (`*.src`, `*.ref0` ... `*.ref3`) into `dev/ref/jfleg/` as `dev.src`, `dev.ref0`, ..., `test.src`, ... (the file names without the leading folder),
then `python3 dev/jfleg_eval.py`. The data is not redistributed here. The verifier thresholds were tuned after reading a random sample of flagged JFLEG pairs: the false-alarm rate is not an independent estimate.
