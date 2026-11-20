# Detector rules

All rules are plain data in `scripts/detect.py`: add or change entries for a field or a house style. Protected spans (citations, references, math, code, URLs) are masked before any rule runs.

## Mechanical rules with a safe fix (`autofix`)
| rule | what | example of the match |
|---|---|---|
| `double_space` | more than one space | `(?<=\S)[ \t]{2,}(?=\S)` |
| `space_before_punct` | space before punctuation | `(?<=[A-Za-z0-9\)⦄])[ \t]+([,;:!?])(?=\s\|$)` |
| `space_before_period` | space before the full stop | `(?<=[a-z\)⦄])[ \t]+\.(?=\s\|$)` |
| `space_before_comma_nospace_after` | space before comma and none after | `(?<=[A-Za-z0-9\)\u2984])[ \t]+,(?=[A-Za-z])` |
| `no_space_after_comma` | missing space after comma | `(?<=[A-Za-z]),(?=[A-Za-z])` |
| `no_space_after_semicolon` | missing space after semicolon | `(?<=[A-Za-z]);(?=[A-Za-z])` |
| `no_space_after_period` | missing space after full stop | `(?<=[a-z]{3})\.(?=[A-Z][a-z]{2})` |
| `can_not` | 'can not' is written 'cannot' | `\bcan\s+not\b(?!\s+only\b)` |
| `micro_sign` | micro prefix written as latin u | `(?<=\d)(\s?)u(M\|L\|g\|m\|mol\|s)\b` |
| `space_in_brackets` | space after opening bracket | `\(\s+(?=\S)` |
| `space_in_brackets2` | space before closing bracket | `(?<=\S)\s+\)` |
| `etc_dots` | double full stop after etc. | `\betc\.\.(?!\.)` |
| `double_comma` | double comma | `,\s*,` |
| `ie_eg_period` | i.e. / e.g. needs the final full stop | `\b(i\.e\|e\.g)(?=[\s,])` |
| `informations` | uncountable noun used in the plural | `\b(information\|equipment\|knowledge\|software\|hardware\|furnitu` |
| `discuss_about` | 'discuss' takes a direct object | `\bdiscuss(es\|ed\|ing)?\s+about\b` |
| `mention_about` | 'mention' takes a direct object | `\bmention(s\|ed\|ing)?\s+about\b` |
| `emphasize_on` | 'emphasize' takes a direct object | `\bemphasi([sz]e[sd]?\|ing)\s+on\b` |
| `other_hand` | fixed phrase: on the other hand | `\bin\s+the\s+other\s+hand\b` |
| `contrary` | fixed phrase: on the contrary | `\bin\s+the\s+contrary\b` |
| `can_able` | 'can able to' | `\bcan\s+able\s+to\b` |
| `different_with` | collocation: different from | `\bdifferent\s+with\b` |
| `similar_with` | collocation: similar to | `\bsimilar\s+with\b` |
| `depend_of` | collocation: depend on | `\bdepends?\s+(of\|from)\b` |
| `reason_because` | 'the reason is because' | `\bthe\s+reason\s+(is\|was)\s+because\b` |
| `amongst_fix` | informal idiom | `\bin\s+a\s+nutshell\b` |
| `repeated_word` | repeated word (except had had / that that / is is ...) | `the the` |
| `a_an` | a / an by the sound of the next word (acronyms by letter name: an FPGA, a CNN; digits: an 8, a 10) | `a obvious` |

Chinese: `zh_comma` 半角逗号用在中文句子里; `zh_semicolon` 半角分号用在中文句子里; `zh_colon` 半角冒号用在中文句子里; `zh_period_end` 半角句号结束中文句子; `zh_question` 半角问号用在中文句子里; `zh_dup_particle` 助词/连词重复; `zh_dup_punct` 标点重复; `zh_space_between` 汉字之间多余空格; `zh_ji_yu` 「基于…的基础上」杂糅.

## Grammar patterns (reported, you decide)
| rule | severity | what |
|---|---|---|
| `agree_pl_subject` | med | possible subject-verb disagreement (plural subject with a singular verb after a prepositional phrase) |
| `agree_sg_head_pl_verb` | med | singular head noun with a plural verb after a prepositional phrase |
| `agree_pl_subject2` | high | plural subject with a singular verb |
| `agree_sg_subject` | med | singular subject with a plural verb (unless 'result' etc. is a modifier) |
| `this_plural` | high | this / that with a plural noun (these / those?) |
| `these_singular` | high | these / those with a singular noun |
| `less_count` | med | 'less' with a countable plural (fewer?) |
| `much_count` | high | 'much' with a countable plural (many?) |
| `article_uncountable` | med | article before an uncountable noun |
| `perfect_past` | med | present perfect with a definite past year (simple past?) |
| `consist_passive` | high | 'consist of' is not used in the passive |
| `composed_by` | med | composed of |
| `comprise_of` | med | 'comprise' takes no 'of' (consist of / comprise) |
| `double_connector` | med | two connectors for one relation (although ... but / because ... so) |
| `not_only_but` | low | 'not only ... but' without 'also' (check parallel structure) |
| `dangling` | low | possible dangling modifier (the subject of the main clause is not the doer of the opening phrase) |
| `missing_subject` | high | sentence without subject |
| `which_comma` | low | long relative clause: consider splitting the sentence |

## Wordiness / translationese patterns (reported with a suggestion)
| pattern | suggestion | category |
|---|---|---|
| `with the development of` | As X develops / Advances in X | wording/med |
| `more and more` | increasingly | wording/med |
| `plays? an important role in` | is important for / contributes to (say what it does) | wording/med |
| `it is well known that` | delete, or cite the source | wording/med |
| `as we all know\|as is known to all\|as everyone knows` | delete, or cite the source | wording/high |
| `in order to` | to | concision/low |
| `due to the fact that` | because | concision/med |
| `a large number of` | many | concision/low |
| `a great deal of` | much | concision/low |
| `has the ability to\|have the ability to` | can | concision/med |
| `is able to\|are able to` | can | concision/low |
| `so as to` | to | concision/low |
| `take(?:s\|n)? into consideration` | consider | concision/med |
| `carry out` | perform / conduct | wording/low |
| `it can be seen (?:from [^,.]{1,40} )?that` | Figure X shows that ... | wording/med |
| `according to [^,.]{1,60}, it can be (?:seen\|found\|concluded) that` | state the result directly | wording/high |
| `in a word` | in summary | wording/med |
| `in recent years,? [^.]{0,80}(?:has\|have) attracted (?:more and more\|much\|great) attention` | say what changed and cite it | wording/med |
| `pay(?:s\|ing)? (?:much\|great\|more) attention to` | focus on / investigate | wording/med |
| `nowadays` | currently / at present | register/med |
| `with the rapid development of` | Advances in X | wording/med |
| `is widely used in many fields` | name the fields | wording/med |
| `have a good effect on\|has a good effect on` | improve / benefit | wording/med |
| `in the process of` | while / during | concision/low |
| `there (?:is\|are) (?:a lot of\|lots of)` | state the quantity | register/med |
| `be used to do\|be used to doing` | check 'used to' structure | grammar/med |
| `on the basis of` | based on | concision/low |
| `at the same time of` | while | wording/med |
| `for the purpose of` | to / for | concision/low |
| `in terms of` | check whether a simpler preposition works | concision/low |

## Register
| pattern | message | severity |
|---|---|---|
| `\b(?:very\|quite\|really\|extremely\|pretty\|rather(?!\s+than))\s+(?=[a-z]+` | intensifier: quantify or drop | low |
| `\ba lot of\b\|\blots of\b\|\btons of\b\|\bkind of\b\|\bsort of\b` | informal quantifier | med |
| `\b(?:gonna\|wanna\|gotta\|kinda\|sorta\|ok\|okay\|stuff\|guys)\b` | informal word | high |
| `\b(?:get\|gets\|got\|getting)\b(?!\s+(?:better\|worse\|larger\|smaller\|highe` | informal verb: obtain / receive / become | low |
| `\b(?:big\|huge\|tiny)\b` | vague size word: give the size | low |
| `\b(?:good\|bad\|nice)\s+(?:results?\|performance\|effects?\|properties)\b` | vague evaluative adjective: give the measure | med |
| `\bthings?\b` | vague noun | low |
| `\b(?:don't\|doesn't\|didn't\|can't\|won't\|isn't\|aren't\|wasn't\|weren't\|hasn` | contraction in formal writing | med |
| `!(?=\s\|$)` | exclamation mark in academic text | med |
| `\byou\b\|\byour\b` | second person in academic text | med |
| `\band so on\b\|\band so forth\b` | vague list ending: say what else | low |

## Claim-strength wording (never changed by the polish; flagged for the author)
| pattern | message |
|---|---|
| `\b(?:perfect(?:ly)?\|revolutionary\|groundbreaking\|unprecedented\|amazing\|remarkabl` | promotional wording |
| `\b(?:best\|optimal)\b(?!\s+(?:fit\|practice\|performing))` | superlative: needs a comparison |
| `\b(?:always\|never\|completely\|totally\|fully\|entirely\|undoubtedly\|obviously\|certai` | absolute wording |
| `\bfor the first time\b\|\bthe first (?:to\|study\|paper\|work)\b\|\bnovel\b` | priority / novelty claim: needs support |
| `\b(?:prove[sd]?\|proof)\b` | 'prove' is strong: show / demonstrate / suggest? |
| `\b(?:solve[sd]?\|eliminat(?:e\|es\|ed))\s+(?:the\|this\|all)\b` | absolute claim |

## Chinese suggestions
| pattern | message | category |
|---|---|---|
| `进行了?[^，。；]{0,6}(?:研究\|分析\|讨论\|探讨\|调查\|实验\|评估\|比较)` | 名词化：「进行研究/分析」可改为动词「研究/分析」 | wording/med |
| `众所周知\|不言而喻\|毋庸置疑\|显而易见` | 绝对化/套话：删除或给出依据 | wording/med |
| `随着[^，。]{2,20}的(?:快速\|不断\|飞速)?发展` | 套话开头：说明具体变化并给出依据 | wording/med |
| `(?:由于\|因为)[^。；]{2,60}，所以` | 「由于…所以」双重连接词 | wording/med |
| `不难(?:发现\|看出\|得出)\|可以看出\|可以发现` | 「可以看出」可直接陈述结果 | wording/low |
| `[挺特超老]\s*[好大多快慢高低强弱]\|搞定\|弄出\|咱们\|牛[的]\|很多很多\|非常非常` | 口语化 | register/high |
| `起到了?[^，。；]{0,4}重要的?作用\|具有[^，。；]{0,8}的作用` | 套话：说明具体作用 | wording/med |
| `完美\|革命性\|颠覆性\|史无前例\|绝对\|彻底解决\|一定\|必然\|永远\|从不` | 绝对化/宣传化措辞：需要证据支撑，润色不得擅自加强或削弱 | claim_strength/med |
| `被[^，。；]{1,15}所` | 「被…所」欧化句式 | wording/low |
| `关于[^，。；]{2,20}的(?:问题\|研究)进行` | 欧化长定语/名词化 | wording/med |

## Document-level consistency (`scan`)
- **term_variants**: the same 1-3 word term written in different ways (case, hyphen, spacing; singular / plural alone are not drift). Resolve with `=== term`.
- **spelling_mix**: US (-ize, -yze, color, center, modeling ...) and UK (-ise, -yse, colour, centre, modelling ...) conventions in one document; `autofix` converts the minority to the majority (or `--spelling US|UK`).
- **abbr_before_definition / abbr_redefined / abbr_conflict / abbr_undefined**: abbreviations defined as `Long Form (ABBR)` (Schwartz-Hearst matching), used before the definition, defined twice, expanded in two ways, or used repeatedly without a definition.
- **format_mix**: `10%` vs `10 %`, `Fig.` vs `Figure`, `et al.` vs `et al` (percent format is unified by `autofix`).
