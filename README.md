# academic-polish-guard · 学术语言润色（改得对 · 说得像 · 没改坏 · 讲得清）

面向「写作02｜学术语言润色」：润色由模型完成，**「没改坏」由脚本证明**。工具先用规则找出机械错误、语法模式、翻译腔/冗余、语域问题、夸大措辞和全篇不一致（术语写法、中美式拼写、缩写先用后定义、数字格式），
安全的机械错误直接修复并记录；模型写的每一处修改都与**原句**逐项核对（引用编号、图表公式指向、数字与单位、否定、量词与界限、限定强度、因果/相关、条件句、变化方向、改动幅度），
改变了含义的修改会被拒绝、保留原句；结果按**原文件格式**写回（未改动的字符逐字不变；Word 输出修订痕迹），并给出修改记录（原文/改文/类型/理由/风险）、事实映射表、术语表和人工复核清单。

> 文中数字都来自开发自测（公开数据集 JFLEG + 40 个手写学术句），**不是平台成绩**；没有与「不加载 Skill 的模型」做过对照，因此不宣称相对基线的提升；未在评测模型（DeepSeek）和真实预算下实跑。

## 对应题面的四个问题
| 题面问题 | 做法 | 自查手段 |
|---|---|---|
| 改得对 | 机械错误由规则修复且经验证（空格/标点、重复词、a/an、`informations`、`discuss about`、`can not`、`1 uM`；中文全角标点、助词重复、`基于…的基础上`）；语法模式（主谓一致、this/these、less/fewer、冠词+不可数名词、`consist` 被动、双重连接词）只报告命中文本；**只换说法的改写（>85% 词元被改）会被拒绝** | `scan`、`autofix`、改动幅度检查 `rewrite` / `heavy_edit` |
| 说得像 | 文体参数（journal / thesis / grant / response / abstract）；语域词表（缩写形式、very/quite、a lot of、感叹号）；翻译腔与冗余表（with the development of、more and more、play an important role、it can be seen that、because…so；中文「随着…的发展」「进行了研究」）；全篇术语变体、中美式拼写混用、缩写定义（Schwartz-Hearst）、数字格式；`=== term` 一次统一全篇 | `scan` 的 DOCUMENT-LEVEL、`check`、`glossary.json` |
| 没改坏 | 逐句对**原文**核对：受保护片段（`[12]`、`(Smith et al., 2020)`、`Fig. 3`、`图3`、`\cite{}`、公式、链接）、数字与单位、否定个数、全称/存在/多数/少数/唯一量词与「至少/至多/约/超过」、弱化词（may/suggest/probably）与强化词（clearly/prove）、`significant`、因果↔相关、条件句、变化方向；原稿里的拼写错误按本意词计，纠正拼写不会被误当作新增论断；断言强度类措辞（always、completely、breakthrough、完美、颠覆性）**不擅自改，只标记给作者** | `ingest` 即时拒绝、`check` 的全文完整性、`facts_map.json` |
| 讲得清 | 每处修改：句号、原文、改文、类型、理由、由谁改（autofix / term / model）、改动比例、风险标记；`redline.md/html`、Word 修订痕迹版；事实映射表（每个数字与引用在原文/改文中的位置）；人工复核清单 | `changes.md/json`、`redline.*`、`facts_map.json`、`review_checklist.md` |

## 目录
```
SKILL.md                         Agent 入口：何时用、步骤、修改块格式、验证规则、冻结与格式处理、异常处理
README.md                        本文件
scripts/pg.py                    命令行：prepare / scan / show / autofix / ingest / next / check / revert / status / assemble
scripts/protect.py               受保护片段与含义清单（数字/否定/量词/限定强度/因果/条件/方向）和 verify_edit 验证器
scripts/detect.py                机械修复、语法/冗余/语域/夸大措辞规则、全篇一致性（术语/拼写/缩写/格式）
scripts/segment.py               读取 md/txt/tex/docx/pdf，句子级定位，写回原格式（Word 修订痕迹）
scripts/nlib.py, parse_pdf.py    句子切分、归一化；PDF 文本抽取
references/                      字段字典、检查规则（含实测）、检测规则表、文体指南、故障处置、方法说明
examples/                        有缺陷的英文/中文/LaTeX 草稿、示例修改文件、真实运行输出 minimal-example.md、example_output/
GITHUB_URL.txt                   作品的 GitHub 公开链接
dev/ （仅仓库）                  回归测试、JFLEG 评测、手写学术句集、生成脚本
```

## 依赖与安装
- Python 3.8+，只用标准库（`.docx` 用 zipfile/XML 读写；已在系统 Python 3.9 上跑通）。PDF 输入需要 `pymupdf`（可回退 `pdfplumber` / `pypdf`），结果以 Markdown 交付。运行时不联网。
- 输入：`.md` `.txt` `.tex` `.docx` `.pdf`（有文本层），或 `/input/case.json` 中的一段文字；英文与中文。

## 使用步骤
```bash
python3 scripts/pg.py prepare draft.docx --work W --genre journal      # 分段、分句、冻结不可改段落、统计问题
python3 scripts/pg.py autofix W                                        # 安全的机械修复 + 一种拼写惯例 + 一种百分号写法
python3 scripts/pg.py scan W                                           # 需要决定的问题 + 全篇一致性
python3 scripts/pg.py ingest W < edits.txt                             # 修改块：每处与原句核对，不通过则保留原句
python3 scripts/pg.py check W && python3 scripts/pg.py assemble W --out out
```
修改块：
```
=== edit S012
revised: 修改后的完整句子（LaTeX 命令、[12]、Fig. 3 原样保留）
type: grammar          reason: 主谓一致
=== term
canonical: dataset     variants: data set; data-set
=== keep S028
rule: claim_wording    reason: 作者的论断，不是文体问题
```
完整示例（真实运行输出，含一处被拒绝的越权修改）见 `examples/minimal-example.md`，导出文件见 `examples/example_output/`。

## 输出
`polished.<ext>`（Word：`polished.docx` 与 `polished_tracked_changes.docx`）· `changes.md/json` · `redline.md/html` · `facts_map.json` · `glossary.json` · `issues_remaining.json` · `review_checklist.md` · `check_report.json` ·
`result.json`（契约字段 + `case_id` + `status` + `polished_text` + `change_log` + `facts_map` + `glossary` + `human_review` + `uncertainty`；推导不出的字段置 `null` 并列出，不编造）。
状态：`success`（完整性无损、无遗留机械问题、无高严重度问题）/ `partial`。

## 实测（开发自测，非平台成绩；`dev/jfleg_eval.py`）
数据：**JFLEG**（公开，1,501 个学习者句子，每句 4 份人工流利度修改，CC BY-NC-SA 4.0）与 40 个手写学术句（各带一份合格的最小润色）。向合格润色里植入一处改变含义的修改，看能否被错误级拦截：

| 植入的含义改变 | JFLEG 人工修改上 | 手写学术句上 |
|---|---|---|
| 删除否定 | 80 %（334 例） | 100 %（7） |
| 改数字 / 改单位 | 93 %（27） | 100 %（25）/ 100 %（6） |
| 量词互换（all/some/most/few/only） | 100 %（227） | 100 %（9） |
| 弱化词变强化词（may→will） | 100 %（94） | 100 %（7） |
| 强化变弱化（will/must→may） | 98 %（254） | - |
| 条件句改动 | 100 %（87） | 100 %（5） |
| 变化方向颠倒 | 95 %（184） | 100 %（13） |
| 引用编号 / 图表编号改动 | - | 100 %（10） |
| 相关改成因果 | - | 100 %（3） |
| 界限改动（at least→at most 等） | - | 100 %（6） |

**误报**：40 个合格学术润色中 0 个被判错误。JFLEG 的人工修改里 15 %（5,175 对中的 779 对）带错误级标记——JFLEG 的编辑会自由重写学习者的句子并常常改动含义词（作者抽读 14 对：约一半确是弱化词/量词/因果措辞的改变，其余是
*instead of / other than*、*every area / everywhere* 这类等价说法）。验证器在抽读 JFLEG 标记样本后做过调整，所以 15 % 不是独立估计。
**检测规则的精度**（以 ≥2/4 份人工修改改动了该处文本为「真」）：`a_an` 100 %（17）、`informations` 100 %（9）、`article_uncountable` 100 %（4）、`double_connector` 100 %（3）、`repeated_word` 73 %（11）、`lowercase_start` 70 %（175）；
`can_not` 36 %（25；人工编辑常保留 `can not`，已排除 `can not only` 并按机械问题报告）。命中很少的规则（主谓一致等）无法在此语料上评估。
**回归测试**（`dev/test_all.py`，18 项）：验证器的放行/拦截、检测规则、受保护片段不被改动、Markdown 往返未改字符不变、越权修改被拒并保留原句、术语/拼写统一、LaTeX 命令保护与环境冻结、中文、
Word 修订痕迹（accept-all / reject-all 结构验证、超链接段落冻结）、契约字段。

## 已知限制
- 检查是词汇与结构层面的：没有标记词的含义改变（主谓宾互换、单位名改动）只有在数字/受保护片段/内容词变化时才会被发现；弱化/强化只看词表。
- 语法规则是模式，不是句法分析：会漏掉需要解析的错误，也会误报合法用法（如 `data is`）；所有语法/冗余命中都只是建议。
- 英文词表为主；中文规则较少（没有 a/an、一致性检查）；其他语言未覆盖。术语漂移只统一大小写/连字符/空格不同的 1–3 词术语，不统一近义词。
- Word：编辑过的段落只保留第一个 run 的字符格式；含超链接/域/脚注/图片的段落冻结；修订痕迹只做了 XML 结构验证，没有在 Word 里实际打开。PDF 只抽取文本。
- 改动幅度阈值（85 % / 60 %）、验证器规则是在 JFLEG 与自写句子上调的默认值。未在评测模型（DeepSeek）和真实预算下实跑；请求数（约 10–16 次）是按流程推算，不是实测。

## 版本与维护
`pg.py` 1.0.0 · schema `polish-guard/1` · 问题与改进请在 GitHub 仓库提 issue。
