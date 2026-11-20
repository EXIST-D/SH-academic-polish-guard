#!/usr/bin/env python3
"""Build a small .docx (stdlib only) for tests: heading, body paragraphs with a bold run, a paragraph with a hyperlink (must stay frozen), a table cell paragraph."""
import sys
import zipfile

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def para(runs, style=None):
    ppr = '<w:pPr><w:pStyle w:val="%s"/></w:pPr>' % style if style else ""
    body = "".join('<w:r>%s<w:t xml:space="preserve">%s</w:t></w:r>' % ("<w:rPr><w:b/></w:rPr>" if b else "", t) for t, b in runs)
    return "<w:p>%s%s</w:p>" % (ppr, body)


def build(path):
    ps = [para([("Effect of soft substrates", False)], "Heading1"),
          para([("The results ", False), ("shows", True), (" that drug A may reduce tumour volume by 40% in mice (Fig. 2) [3]. We didn't test other doses.", False)]),
          para([("See ", False)]) .replace("</w:p>", '<w:hyperlink r:id="rId5"><w:r><w:t>the website</w:t></w:r></w:hyperlink></w:p>'),
          "<w:tbl><w:tr><w:tc>" + para([("In order to compare the groups, a one-way ANOVA were used.", False)]) + "</w:tc></w:tr></w:tbl>"]
    doc = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="%s" xmlns:r="%s"><w:body>%s</w:body></w:document>' % (W, R, "".join(ps))
    ct = '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>'
    rels = '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>'
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", doc)


if __name__ == "__main__":
    build(sys.argv[1])
