"""Hand-written academic sentences (original, each with a minimal legitimate polish) used by jfleg_eval.py to seed meaning changes.
Each pair is (draft, polish): the polish fixes grammar / wording only. Mutations are injected into the POLISH and must be caught; the polish itself must not be flagged."""
import re

PAIRS = [
    ("The results shows that drug A may reduce tumor volume by 40% in mice (Fig. 2) [3].", "The results show that drug A may reduce tumour volume by 40% in mice (Fig. 2) [3]."),
    ("Serum cortisol was associated with lower sleep quality in older adults [4,5].", "Serum cortisol was associated with lower sleep quality in older adults [4, 5]."),
    ("We did not observed any difference between the 10 mg/kg and the 20 mg/kg groups.", "We did not observe any difference between the 10 mg/kg and the 20 mg/kg groups."),
    ("If the temperature exceeds 80 °C , the polymer degrades within 2 h.", "If the temperature exceeds 80 °C, the polymer degrades within 2 h."),
    ("All participants (n = 120) completed the survey and most of them preferred the new interface.", "All participants (n = 120) completed the survey, and most of them preferred the new interface."),
    ("Only 12 of 30 samples were positive for the marker (Table 1).", "Only 12 of 30 samples were positive for the marker (Table 1)."),
    ("The model achieve an accuracy of 91.3% on the test set, which is higher than the baseline [7].", "The model achieves an accuracy of 91.3% on the test set, which is higher than the baseline [7]."),
    ("Higher temperature lead to faster degradation of the enzyme.", "Higher temperature leads to faster degradation of the enzyme."),
    ("These findings suggest that sleep deprivation might impair memory consolidation.", "These findings suggest that sleep deprivation might impair memory consolidation."),
    ("The correlation between income and health was weak (r = 0.12, p = 0.04).", "The correlation between income and health was weak (r = 0.12, p = 0.04)."),
    ("Because the sample is small , the effect can not be generalised to other populations.", "Because the sample is small, the effect cannot be generalised to other populations."),
    ("At least 200 nuclei per gel was scored by two independent observers.", "At least 200 nuclei per gel were scored by two independent observers."),
    ("The treatment reduced the number of lesions by approximately 30% compared with placebo (p < 0.01).", "The treatment reduced the number of lesions by approximately 30% compared with placebo (p < 0.01)."),
    ("Our method is slower than the baseline but requires less memory (Section 4.2).", "Our method is slower than the baseline but requires less memory (Section 4.2)."),
    ("Smoking is a leading cause of lung cancer, and quitting reduces the risk substantially [1].", "Smoking is a leading cause of lung cancer, and quitting reduces the risk substantially [1]."),
    ("No significant difference was found between the groups (p = 0.31).", "No significant difference was found between the groups (p = 0.31)."),
    ("The effect was observed only when the dose exceeded 5 mg.", "The effect was observed only when the dose exceeded 5 mg."),
    ("Mice fed a high-fat diet gained more weight than controls, probably because of increased food intake.", "Mice fed a high-fat diet gained more weight than controls, probably because of increased food intake."),
    ("Several studies have reported that exercise improves mood in adolescents [2-4].", "Several studies have reported that exercise improves mood in adolescents [2–4]."),
    ("The proposed network outperform the state of the art by 2.1 points on CIFAR-10 (Table 2).", "The proposed network outperforms the state of the art by 2.1 points on CIFAR-10 (Table 2)."),
    ("Interleukin-6 was upregulated in tumours and correlated with poor survival.", "Interleukin-6 was upregulated in tumours and correlated with poor survival."),
    ("When the load was removed, the beam returned to its original shape within 3 s.", "When the load was removed, the beam returned to its original shape within 3 s."),
    ("Few patients (5%) reported side effects, and none required hospitalisation.", "Few patients (5%) reported side effects, and none required hospitalisation."),
    ("It is possible that the observed decline reflects a change in sampling rather than a true decrease.", "It is possible that the observed decline reflects a change in sampling rather than a true decrease."),
    ("The data indicates a clear relationship between dose and response (Fig. 4a).", "The data indicate a clear relationship between dose and response (Fig. 4a)."),
    ("Accuracy increased from 80% to 90% when the learning rate was halved.", "Accuracy increased from 80% to 90% when the learning rate was halved."),
    ("The catalyst is stable at pH 7 but decomposes rapidly below pH 4.", "The catalyst is stable at pH 7 but decomposes rapidly below pH 4."),
    ("We assumed that the noise is Gaussian , which holds for most sensors.", "We assumed that the noise is Gaussian, which holds for most sensors."),
    ("Patients who received the drug had a lower risk of relapse (hazard ratio 0.62; 95% CI 0.45-0.85).", "Patients who received the drug had a lower risk of relapse (hazard ratio 0.62; 95% CI 0.45–0.85)."),
    ("The two variables are unrelated in this cohort.", "The two variables are unrelated in this cohort."),
    ("Increasing the dropout rate reduced overfitting, but it also decreased accuracy slightly.", "Increasing the dropout rate reduced overfitting, but it also decreased accuracy slightly."),
    ("The authors concluded that the intervention was effective in reducing anxiety (Smith et al., 2019).", "The authors concluded that the intervention was effective in reducing anxiety (Smith et al., 2019)."),
    ("Each sample was measured three times and the mean was used.", "Each sample was measured three times, and the mean was used."),
    ("The concentration was lower than 0.5 mM in all samples.", "The concentration was lower than 0.5 mM in all samples."),
    ("Without the regularisation term the model fails to converge.", "Without the regularisation term, the model fails to converge."),
    ("Rainfall exceeding 50 mm per day triggered landslides in the region [6].", "Rainfall exceeding 50 mm per day triggered landslides in the region [6]."),
    ("This suggests, but does not prove, that the pathway is involved.", "This suggests, but does not prove, that the pathway is involved."),
    ("The difference was not statistically significant, so we cannot exclude a small effect.", "The difference was not statistically significant, so we cannot exclude a small effect."),
    ("Both methods perform equally well on short texts but diverge on long ones.", "Both methods perform equally well on short texts but diverge on long ones."),
    ("Heavy metals can accumulate in soil and may enter the food chain.", "Heavy metals can accumulate in soil and may enter the food chain."),
]
SUBS = {
    "negation dropped": [(r"\b(did not|does not|do not|cannot|can not|not|No|no|none|unrelated|fails)\b", lambda m: {"unrelated": "related", "fails": "fails", "No": "A", "no": "a"}.get(m.group(0), ""))],
    "number changed": [(r"\b(\d+(?:\.\d+)?)\b", lambda m: str(float(m.group(1)) + 1).rstrip("0").rstrip(".") if "." in m.group(1) else str(int(m.group(1)) + 1))],
    "unit changed": [(r"\b(mg/kg|mg|mM|mm|°C|%|s|h)\b", lambda m: {"mg/kg": "g/kg", "mg": "g", "mM": "M", "mm": "cm", "°C": "°F", "%": "‰", "s": "min", "h": "min"}[m.group(1)])],
    "citation changed": [(r"\[(\d+)(?:[-,–]\s?\d+)?\]", lambda m: "[%d]" % (int(m.group(1)) + 1)), (r"\b(?:Fig\.|Table|Section) (\d+(?:\.\d+)?[a-z]?)", lambda m: m.group(0).replace(m.group(1), str(int(re.match(r"\d+", m.group(1)).group(0)) + 1)))],
    "quantifier changed": [(r"\b(All|all|most|Most|Each|each|Several|Few|few|Both|only|Only)\b", lambda m: {"All": "Some", "all": "some", "most": "few", "Most": "Few", "Each": "Some", "each": "some", "Several": "All", "Few": "Most", "few": "most", "Both": "Neither", "only": "also", "Only": "Also"}[m.group(1)])],
    "hedge strengthened": [(r"\b(may|might|probably|possible|suggests|suggest|indicate|can)\b", lambda m: {"may": "will", "might": "will", "probably": "certainly", "possible": "certain", "suggests": "proves", "suggest": "prove", "indicate": "prove", "can": "must"}[m.group(1)])],
    "causal wording added": [(r"\b(associated with|correlated with|relationship between|linked to)\b", lambda m: {"associated with": "caused by", "correlated with": "caused by", "relationship between": "causal effect of", "linked to": "caused by"}[m.group(1)])],
    "conditional changed": [(r"\b(If|if|When|when|Without|Unless|unless)\b", lambda m: {"If": "Since", "if": "since", "When": "Because", "when": "because", "Without": "With", "Unless": "Since", "unless": "since"}[m.group(1)])],
    "direction inverted": [(r"\b(higher|lower|faster|slower|increased|decreased|upregulated|more|less|reduced|improves|reduces|gained)\b", lambda m: {"higher": "lower", "lower": "higher", "faster": "slower", "slower": "faster", "increased": "decreased", "decreased": "increased", "upregulated": "downregulated", "more": "less", "less": "more", "reduced": "increased", "improves": "worsens", "reduces": "increases", "gained": "lost"}[m.group(1)])],
    "bound changed": [(r"\b(At least|at least|approximately|lower than|exceeding|exceeded|below|more than)\b", lambda m: {"At least": "At most", "at least": "at most", "approximately": "exactly", "lower than": "higher than", "exceeding": "below", "exceeded": "fell below", "below": "above", "more than": "less than"}[m.group(1)])],
}


def run(errors):
    rows = {k: [0, 0, 0] for k in SUBS}
    fa = 0
    for draft, polish in PAIRS:
        if errors(draft, polish):
            fa += 1
        for name, subs in SUBS.items():
            for pat, fn in subs:
                if re.search(pat, polish):
                    mutated = re.sub(pat, fn, polish, count=1)
                    if mutated != polish:
                        rows[name][0] += 1
                        rows[name][1] += bool(errors(polish, mutated))
                    break
    return {"rows": {k: v for k, v in rows.items()}, "fa": fa, "fa_n": len(PAIRS)}
