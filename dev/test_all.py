#!/usr/bin/env python3
"""Regression tests (stdlib unittest): python3 dev/test_all.py   (uses submission/examples; no network)"""
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
import zipfile
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
SUB = os.path.join(HERE, "..", "submission")
sys.path.insert(0, os.path.join(SUB, "scripts"))
sys.path.insert(0, HERE)
import detect  # noqa: E402
import protect  # noqa: E402
import make_docx  # noqa: E402

PG = os.path.join(SUB, "scripts", "pg.py")
EX = os.path.join(SUB, "examples")


def pg(*args, stdin=None):
    r = subprocess.run([sys.executable, PG, *args], input=stdin, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def kinds(a, b, **kw):
    return {i["kind"] for i in protect.verify_edit(a, b, **kw) if i["severity"] == "error"}


class Verifier(unittest.TestCase):
    def test_clean_polish_passes(self):
        self.assertEqual(kinds("The results shows that drug A may reduce tumor volume by 40% in mice (Fig. 2) [3].", "The results show that drug A may reduce tumour volume by 40% in mice (Figure 2) [3]."), set())

    def test_meaning_changes_are_errors(self):
        cases = [("may reduce", "will reduce", "strengthened"), ("did not observe an effect", "observed an effect", "negation_changed"), ("Only 12 of 30 samples", "12 of 30 samples", "quantifier_changed"),
                 ("associated with lower mortality", "caused lower mortality", "causal_added"), ("accuracy increased from 80% to 90%", "accuracy decreased from 90% to 80%", "direction_changed"),
                 ("40% of mice [3]", "40% of mice [4]", "protected_changed"), ("at least 200 nuclei", "at most 200 nuclei", "bound_changed"), ("The effect was significant.", "The effect was large.", "significance_changed"),
                 ("If it is heated, it melts.", "It melts.", "conditional_changed"), ("dose of 5 mg", "dose of 5 g", "number_changed")]
        for a, b, k in cases:
            with self.subTest(k):
                self.assertIn(k, kinds(a, b))

    def test_equivalent_wording_passes(self):
        self.assertEqual(kinds("There are a lot of samples.", "There are many samples."), set())
        self.assertEqual(kinds("We found three groups.", "We found 3 groups."), set())
        self.assertEqual(kinds("it can not be used", "It cannot be used."), set())

    def test_rewrite_is_flagged(self):
        self.assertIn("rewrite", kinds("The big dog ran fast to the old red barn.", "A quick hound sprinted toward a weathered crimson stable yesterday."))

    def test_typo_corrections_are_not_new_claims(self):
        self.assertEqual(kinds("We stopped because of the beacuse of cost.", "We stopped because of the cost."), set())

    def test_chinese(self):
        self.assertIn("negation_changed", kinds("实验结果没有显著差异。", "实验结果存在显著差异。"))
        self.assertEqual(kinds("结果表明，10 kPa 凝胶上的面积是 40 kPa 的 2.3 倍 [3]。", "结果表明，10 kPa 凝胶上的面积为 40 kPa 的 2.3 倍 [3]。"), set())


class Detectors(unittest.TestCase):
    def test_autofix(self):
        new, ap = detect.autofix_sentence("The the sample was dosed at 1 uM and can not be reused ,so a obvious fix .")
        self.assertEqual(new, "The sample was dosed at 1 μM and cannot be reused, so an obvious fix.")

    def test_protected_spans_untouched(self):
        s = "See Fig. 2 , Eq. (3) and [1,2] ; $a  ,  b$ stay ."
        new, _ = detect.autofix_sentence(s)
        self.assertIn("$a  ,  b$", new)
        self.assertIn("Fig. 2", new)

    def test_grammar_patterns(self):
        rules = {i["rule"] for i in detect.scan_sentence("This results shows that the data are good and the area on gels were large.", "en", "journal")}
        self.assertTrue({"this_plural", "agree_pl_subject2", "agree_sg_head_pl_verb"} <= rules)

    def test_doc_level(self):
        sents = [("S1", "We built a dataset of cells."), ("S2", "The data set was split."), ("S3", "Localization was measured and cells were analysed."), ("S4", "We used a convolutional neural network (CNN). The CNN works."),
                 ("S5", "The SVM was trained.")]
        kinds_ = {d["kind"] for d in detect.scan_doc(sents)}
        self.assertTrue({"term_variants", "spelling_mix", "abbr_undefined"} & kinds_ or {"term_variants", "spelling_mix"} <= kinds_)

    def test_spelling_conversion(self):
        self.assertEqual(detect.convert_spelling("localisation", "US"), "localization")
        self.assertEqual(detect.convert_spelling("Analyze", "UK"), "Analyse")
        self.assertIsNone(detect.convert_spelling("rise", "UK"))


class Pipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()

    def run_flow(self, name, edits, ext_files=()):
        w = os.path.join(self.tmp, name)
        rc, out = pg("prepare", os.path.join(EX, name), "--work", w)
        self.assertEqual(rc, 0, out)
        rc, out = pg("autofix", w)
        self.assertEqual(rc, 0, out)
        return w

    def test_markdown_roundtrip_keeps_untouched_text(self):
        w = self.run_flow("draft_en.md", None)
        rc, out = pg("ingest", w, stdin="=== edit S003\nrevised: With advances in tissue engineering, researchers are increasingly interested in substrate stiffness.\ntype: wording\nreason: template opening\n")
        self.assertEqual(rc, 0, out)
        rc, out = pg("assemble", w, "--out", os.path.join(self.tmp, "out_md"))
        self.assertEqual(rc, 0, out)
        orig = open(os.path.join(EX, "draft_en.md"), encoding="utf-8").read()
        new = open(os.path.join(self.tmp, "out_md", "polished.md"), encoding="utf-8").read()
        self.assertTrue(new.startswith("# Effect of soft substrates on osteoblast mineralisation\n\n## Abstract\n\nWith advances in tissue engineering"))
        res = json.loads(out.splitlines()[0])
        self.assertTrue(res["integrity_ok"])
        for f in ("changes.md", "changes.json", "redline.md", "redline.html", "facts_map.json", "glossary.json", "review_checklist.md", "result.json", "check_report.json"):
            self.assertTrue(os.path.isfile(os.path.join(self.tmp, "out_md", f)), f)
        # the reference list / numbers / citations of the original are all still present
        for tok in ("[3]", "[1,2]", "2.3-fold", "p = 0.004", "Table 1", "(Fig. 2)"):
            self.assertIn(tok, new)

    def test_unsafe_edit_is_rejected_and_original_kept(self):
        w = self.run_flow("draft_en.md", None)
        rc, out = pg("ingest", w, stdin="=== edit S006\nrevised: Nuclear YAP localisation was lower on soft gels, which shows that YAP signalling mediates part of the stiffness response [3].\ntype: wording\nreason: x\n")
        self.assertEqual(rc, 2)
        self.assertIn("REJECTED", out)
        self.assertIn("strengthened", out)
        rc, out = pg("show", w, "--ids", "S006")
        self.assertIn("suggests that YAP signalling may mediate", out)

    def test_terms_and_spelling(self):
        w = self.run_flow("draft_en.md", None)
        rc, out = pg("ingest", w, stdin="=== term\ncanonical: dataset\nvariants: data set; data-set\n")
        self.assertEqual(rc, 0, out)
        rc, out = pg("scan", w)
        self.assertNotIn("spelling_mix", out)
        self.assertNotIn("data-set", out)

    def test_latex_commands_protected(self):
        w = self.run_flow("draft_tex.tex", None)
        rc, out = pg("ingest", w, stdin="=== edit S001\nrevised: With advances in deep learning, researchers are increasingly interested in model compression \\cite{han2016}.\ntype: wording\nreason: x\n")
        self.assertEqual(rc, 2)
        self.assertIn("protected_changed", out)
        rc, out = pg("ingest", w, stdin="=== edit S001\nrevised: With advances in deep learning, researchers are increasingly interested in model compression \\cite{han2016,hinton2015}.\ntype: wording\nreason: x\n")
        self.assertEqual(rc, 0, out)
        rc, out = pg("assemble", w, "--out", os.path.join(self.tmp, "out_tex"))
        t = open(os.path.join(self.tmp, "out_tex", "polished.tex"), encoding="utf-8").read()
        self.assertIn("\\begin{equation}\nE = mc^2 \\label{eq:e}\n\\end{equation}", t)
        self.assertIn("\\documentclass{article}", t)

    def test_chinese(self):
        w = self.run_flow("draft_zh.md", None)
        rc, out = pg("scan", w)
        self.assertIn("zh_", out)

    def test_docx_tracked_changes(self):
        d = os.path.join(self.tmp, "t.docx")
        make_docx.build(d)
        w = os.path.join(self.tmp, "dx")
        rc, out = pg("prepare", d, "--work", w)
        self.assertEqual(rc, 0, out)
        self.assertIn("frozen_paragraphs", out)
        rc, out = pg("ingest", w, stdin="=== edit S002\nrevised: The results show that drug A may reduce tumour volume by 40% in mice (Fig. 2) [3].\ntype: grammar\nreason: agreement\n=== edit S004\nrevised: To compare the groups, a one-way ANOVA was used.\ntype: grammar\nreason: agreement\n")
        self.assertEqual(rc, 0, out)
        rc, out = pg("assemble", w, "--out", os.path.join(self.tmp, "dx_out"))
        self.assertEqual(rc, 0, out)
        x = zipfile.ZipFile(os.path.join(self.tmp, "dx_out", "polished_tracked_changes.docx")).read("word/document.xml").decode()
        ET.fromstring(x)
        self.assertIn("<w:ins ", x)
        self.assertIn("<w:del ", x)
        self.assertIn("w:hyperlink", x)
        accepted = re.sub(r"<[^>]+>", "", re.sub(r"</w:p>", "\n", re.sub(r"<w:del .*?</w:del>", "", x, flags=re.S)))
        self.assertIn("The results show that drug A", accepted)
        rejected = re.sub(r"<[^>]+>", "", re.sub(r"</w:p>", "\n", re.sub(r"<w:ins .*?</w:ins>", "", x, flags=re.S).replace("w:delText", "w:t")))
        self.assertIn("The results shows that drug A", rejected.replace("shows", "shows"))
        z = zipfile.ZipFile(os.path.join(self.tmp, "dx_out", "polished.docx"))
        self.assertIn("[Content_Types].xml", z.namelist())

    def test_case_contract(self):
        case = os.path.join(self.tmp, "case.json")
        json.dump({"case_id": "c1", "file": os.path.join(EX, "draft_en.md"), "task": "Polish this journal manuscript", "output_contract": {"fields": ["case_id", "polished_text", "change_log", "facts_map", "human_review", "status", "mystery"]}}, open(case, "w"))
        w = os.path.join(self.tmp, "cw")
        rc, out = pg("prepare", "--work", w, "--case", case)
        self.assertEqual(rc, 0, out)
        pg("autofix", w)
        rc, out = pg("assemble", w, "--out", os.path.join(self.tmp, "cout"), "--case", case)
        self.assertEqual(rc, 2)
        res = json.load(open(os.path.join(self.tmp, "cout", "result.json"), encoding="utf-8"))
        self.assertEqual(res["case_id"], "c1")
        self.assertIsNone(res["mystery"])
        self.assertIn("mystery", res["_meta"]["unfilled_fields"])
        self.assertTrue(res["change_log"] and res["polished_text"]["text"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
