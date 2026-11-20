#!/usr/bin/env python3
"""Regenerate submission/examples/example_output/ and examples/minimal-example.md from REAL runs on the flawed example drafts."""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..", "submission")
PG = os.path.join(ROOT, "scripts", "pg.py")
EX = os.path.join(ROOT, "examples")
WORK = os.path.join(HERE, "..", "work", "example_work")
OUT = os.path.join(EX, "example_output")
shutil.rmtree(WORK, ignore_errors=True)
shutil.rmtree(OUT, ignore_errors=True)
os.makedirs(WORK)


def run(*args, cut=None, maxlines=None):
    r = subprocess.run([sys.executable, "-W", "ignore", PG, *args], capture_output=True, text=True, cwd=EX)
    out = (r.stdout + r.stderr).strip().replace(WORK, "W")
    lines = out.splitlines()
    if maxlines:
        lines = lines[:maxlines] + (["..."] if len(out.splitlines()) > maxlines else [])
    return "\n".join((l[:cut] if cut else l) for l in lines)


md = ["# Minimal example (real output of the tool on FLAWED, INVENTED drafts)", "",
      "`draft_en.md`, `draft_zh.md` and `draft_tex.tex` are invented manuscripts with deliberate problems; the findings and numbers are not real. Everything below is the output of the commands (long lines shortened with `...`). "
      "`example_output/` holds the files `assemble` wrote for the English draft. Nothing here is a result of a platform case.", ""]
w = os.path.join(WORK, "en")
steps = [("1. Prepare the English draft", ["prepare", "draft_en.md", "--work", w], "pg.py prepare draft_en.md --work W", 420, None),
         ("2. Safe mechanical fixes (verified and logged)", ["autofix", w], "pg.py autofix W", 400, None),
         ("3. What still needs a decision", ["scan", w, "--limit", "12"], "pg.py scan W --limit 12", 230, 60),
         ("4. Submit edits (`edits_en.txt`). Note the REJECTED line: that edit dropped 'always' from the author's claim, so the original sentence is kept", ["ingest", w, "edits_en.txt"], "pg.py ingest W edits_en.txt", 330, None),
         ("5. Whole-document check", ["check", w], "pg.py check W", 230, None),
         ("6. Assemble", ["assemble", w, "--out", "example_output"], "pg.py assemble W --out example_output", 420, None)]
for title, args, shown, cut, ml in steps:
    md += ["## " + title, "```bash", "python3 scripts/" + shown, "```", "```text", run(*args, cut=cut, maxlines=ml), "```", ""]
md += ["## What changed (`example_output/changes.md`, first rows)", "```text"] + open(os.path.join(OUT, "changes.md"), encoding="utf-8").read().splitlines()[:11] + ["```", "",
       "## Redline of one paragraph (`example_output/redline.md`)", "```text", [l for l in open(os.path.join(OUT, "redline.md"), encoding="utf-8").read().splitlines() if l.startswith("**P5**")][0][:900], "```", ""]
for name, f in (("Chinese draft", "draft_zh.md"), ("LaTeX draft", "draft_tex.tex")):
    ww = os.path.join(WORK, f.split(".")[0])
    md += ["## %s: prepare, autofix, scan" % name, "```bash", "python3 scripts/pg.py prepare %s --work W2" % f, "python3 scripts/pg.py autofix W2", "python3 scripts/pg.py scan W2 --limit 5", "```", "```text",
           run("prepare", f, "--work", ww, cut=300), run("autofix", ww, cut=300), run("scan", ww, "--limit", "5", cut=200, maxlines=24), "```", ""]
open(os.path.join(EX, "minimal-example.md"), "w", encoding="utf-8").write("\n".join(md))
print("example written; files:", sorted(os.listdir(OUT)))
