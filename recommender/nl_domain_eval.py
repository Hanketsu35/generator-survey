"""Layer 1 on questions a real user would ask, against honest baselines.

``nl.py --eval`` scores the extractors on a set written in the field's own
vocabulary, which the keyword rules saturate at 100% -- so it cannot tell
whether a language model adds anything. This script uses
``data/nl_queries_domain.json`` instead: domain-phrased requests, half in
Turkish, with every word the rules key on banned (checked mechanically below,
before anything is scored).

Four systems, weakest first. The second is the one that matters:

``rules``         the existing keyword extractor, unchanged.
``type-default``  ignore the question; pick the family implied by the file's
                  data type. It is the majority-class baseline, and it is
                  strong here because ask.py measures the data type from the
                  file -- so every sequential and utility query is answered
                  correctly by knowing nothing about the question.
``rules+type``    a matched keyword if there is one, else type-default. The
                  strongest thing achievable without a model.
``llm:<name>``    ``ask.understand`` with the production prompt, through a
                  local Ollama model.

The model is only worth running if it beats ``rules+type``, and the place it
can is the transactional queries, where four families share one data type and
the question is the only evidence.

Scoring. Family accuracy over the queries that state a goal; a model's answer
that ask.py would reject as outside ``spec.FAMILIES`` counts as wrong. Queries
with no goal are reported separately with what each system *said*, because the
right behaviour there is to ask rather than to guess, and none of these systems
can ask yet.

    python -m recommender.nl_domain_eval                       # dev split
    python -m recommender.nl_domain_eval --split test          # score once
    python -m recommender.nl_domain_eval --models qwen2.5:14b-instruct
"""
import argparse
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict

from . import ask
from . import nl

_HERE = os.path.dirname(os.path.abspath(__file__))
QUERIES = os.path.join(_HERE, "data", "nl_queries_domain.json")
OUT_DIR = os.path.join(_HERE, "out")

#: Words the rule extractor matches on. A query containing one would test the
#: keyword list rather than language understanding, so the set is refused.
BANNED = (r"generator", r"\bclosed\b", r"\brare\b", r"utility", r"sequen",
          r"clickstream", r"event log", r"minimal", r"itemset", r"minsup")

TYPE_DEFAULT = {"transactional": "minimal_generator",
                "sequential": "sequential_generator",
                "utility": "high_utility_generator"}

#: What ask.py would measure from each kind of file, so the model sees the same
#: context it sees in production. The values are typical, not tuned.
CONTEXT = {
    "transactional": ({"data_type": "transactional", "n_tx": 10000, "n_items": 120,
                       "avg_len": 12.4}, "12 45 78 102 119\n3 12 45 88\n7 12 45 66 78 90"),
    "sequential": ({"data_type": "sequential", "n_tx": 5000, "n_items": 300,
                    "avg_len": 9.1}, "3 -1 7 -1 12 -1 -2\n7 -1 12 -1 3 -1 -2\n3 -1 12 -2"),
    "utility": ({"data_type": "utility", "n_tx": 8000, "n_items": 400,
                 "avg_len": 6.2}, "4 9 17:52:10 24 18\n9 17 31:40:22 12 6\n4 31:15:9 6"),
}


def load(split):
    with open(QUERIES, encoding="utf-8") as fh:
        return json.load(fh)["splits"][split]


def check_banned(queries):
    hits = []
    for q in queries:
        for pat in BANNED:
            if re.search(pat, q["text"].lower()):
                hits.append((q["id"], pat))
    return hits


# ----------------------------------------------------------------------
def sys_rules(q):
    return nl.RuleExtractor().extract(q["text"]).get("family")


def sys_type_default(q):
    return TYPE_DEFAULT[q["data_type"]]


def sys_rules_type(q):
    """Keyword if one matched, else the family the file's data type implies."""
    t = q["text"].lower()
    for fam, pat in nl.RuleExtractor.FAMILY_PATTERNS:
        if re.search(pat, t):
            return fam
    return TYPE_DEFAULT[q["data_type"]]


def make_llm(model, host, prompt_version, repair=False, sc=False):
    """One configuration of the ablation: prompt, type repair, self-consistency."""
    def run(q):
        prof, sample = CONTEXT[q["data_type"]]
        if sc:
            fields, source, note = ask.understand_consistent(
                q["text"], prof, sample, host, model, prompt_version=prompt_version)
        else:
            fields, source, note = ask.understand(q["text"], prof, sample, host, model,
                                                  prompt_version=prompt_version,
                                                  repair=repair)
        run.last_objective = None
        if fields is None:
            if source == "unavailable":
                raise RuntimeError(note)
            return "UNCLEAR" if source == "unclear" else "REJECTED"
        run.last_objective = fields.get("objective")
        return fields["family"]
    run.last_objective = None
    return run


# ----------------------------------------------------------------------
def evaluate(name, fn, queries):
    rows = []
    t0 = time.time()
    for q in queries:
        got = fn(q)
        obj = getattr(fn, "last_objective", None)
        rows.append({"id": q["id"], "lang": q["lang"], "data_type": q["data_type"],
                     "gold": q["family"], "got": got,
                     "gold_obj": q.get("objective"), "got_obj": obj})
    return rows, time.time() - t0


def summarise(name, rows, secs, L):
    """One line per system. The column that matters is SILENT: a wrong family
    returned as if it were right. Asking back (UNCLEAR) is unhelpful but safe;
    a silent error hands the user a confident wrong answer, and Layer 2 cannot
    catch it -- Layer 2 guarantees the output matches the SPEC, not the intent.
    """
    goal = [r for r in rows if r["gold"] is not None]
    nogoal = [r for r in rows if r["gold"] is None]
    ok = [r for r in goal if r["got"] == r["gold"]]
    silent = [r for r in goal if r["got"] not in (r["gold"], "UNCLEAR")]
    asked = [r for r in goal if r["got"] == "UNCLEAR"]
    ng_ok = [r for r in nogoal if r["got"] == "UNCLEAR"]
    tr = [r for r in goal if r["data_type"] == "transactional"]
    tr_ok = [r for r in tr if r["got"] == r["gold"]]
    trl = [r for r in goal if r["lang"] == "tr"]
    L.append("  %-30s %5.1f%%  %6.1f%%  %6.1f%%   %5.1f%%    %d/%d        %5.1f%%  %5.1fs"
             % (name, 100 * len(ok) / len(goal), 100 * len(silent) / len(goal),
                100 * len(asked) / len(goal),
                100 * len(tr_ok) / max(len(tr), 1),
                len(ng_ok), len(nogoal),
                100 * sum(r["got"] == r["gold"] for r in trl) / max(len(trl), 1),
                secs))
    return {"acc": len(ok) / len(goal), "silent": len(silent) / len(goal),
            "asked": len(asked) / len(goal),
            "transactional_acc": len(tr_ok) / max(len(tr), 1),
            "nogoal_asked": len(ng_ok), "nogoal_n": len(nogoal)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--split", default="dev", choices=("dev", "test"))
    ap.add_argument("--models", nargs="*",
                    default=["qwen2.5:7b-instruct", "qwen2.5:14b-instruct"])
    ap.add_argument("--host", default=ask.DEFAULT_HOST)
    ap.add_argument("--configs", nargs="*",
                    default=["v1", "v2", "v2+type", "v2+type+sc"])
    args = ap.parse_args(argv)

    queries = load(args.split)
    hits = check_banned(queries)
    if hits:
        print("REFUSED: queries contain words the rule extractor keys on, so they")
        print("would test the keyword list rather than understanding:")
        for qid, pat in hits:
            print("   %s  %s" % (qid, pat))
        return 1

    systems = [("rules", sys_rules), ("type-default", sys_type_default),
               ("rules+type", sys_rules_type)]
    # The ablation, each step adding one mechanism to the one before:
    #   v1               the prompt as first shipped
    #   v2               definitions instead of cues; "unclear" allowed
    #   v2+type          ... plus reconciling the family with the measured type
    #   v2+type+sc       ... plus voting over sampled readings, abstaining if split
    ablation = [("v1", "v1", False, False), ("v2", "v2", False, False),
                ("v2+type", "v2", True, False), ("v2+type+sc", "v2", True, True)]
    for m in args.models:
        for label, pv, rep, sc in ablation:
            if label not in args.configs:
                continue
            systems.append(("llm:%s %s" % (m.split(":")[-1].replace("-instruct", ""), label),
                            make_llm(m, args.host, pv, repair=rep, sc=sc)))

    L = ["=" * 100,
         "LAYER 1 ON DOMAIN-PHRASED QUESTIONS  (split %s, %d queries, %d with a goal)"
         % (args.split, len(queries), sum(q["family"] is not None for q in queries)),
         "=" * 100,
         "  keyword ban: passed -- no query contains a word the rules match on",
         "",
         "  %-30s %6s  %7s  %7s   %7s  %11s   %7s" % ("system", "right", "SILENT",
                                                        "asked", "transact.",
                                                        "no-goal ok", "turkish"),
         "  " + "-" * 96]
    results, all_rows = {}, {}
    for name, fn in systems:
        try:
            rows, secs = evaluate(name, fn, queries)
        except RuntimeError as exc:
            L.append("  %-26s unavailable: %s" % (name, exc))
            continue
        results[name] = summarise(name, rows, secs, L)
        all_rows[name] = rows

    # --- where the systems go wrong -----------------------------------
    L.append("")
    L.append("  CONFUSIONS on transactional queries (gold -> answered, count)")
    for name, rows in all_rows.items():
        c = Counter((r["gold"], r["got"]) for r in rows
                    if r["gold"] and r["data_type"] == "transactional"
                    and r["got"] != r["gold"])
        if c:
            L.append("    %s" % name)
            for (g, a), n in c.most_common():
                L.append("      %-24s -> %-24s %d" % (g, a, n))

    # --- objectives ---------------------------------------------------
    L.append("")
    L.append("  OBJECTIVE on the queries that state one")
    for name, rows in all_rows.items():
        if not name.startswith("llm:"):
            continue
        got = [(r["id"], r["gold_obj"], r["got_obj"]) for r in rows if r["gold_obj"]]
        L.append("    %-26s %s" % (name, "  ".join("%s:%s->%s" % g for g in got)))

    # --- no goal given ------------------------------------------------
    L.append("")
    L.append("  NO GOAL GIVEN -- the right answer is a question back, not a family")
    ids = [q["id"] for q in queries if q["family"] is None]
    for name, rows in all_rows.items():
        said = {r["id"]: r["got"] for r in rows}
        L.append("    %-26s %s" % (name, "  ".join("%s:%s" % (i, said[i]) for i in ids)))

    text = "\n".join(L) + "\n"
    print(text)
    os.makedirs(OUT_DIR, exist_ok=True)
    base = os.path.join(OUT_DIR, "nl_domain_%s" % args.split)
    with open(base + ".txt", "w", encoding="utf-8") as fh:
        fh.write(text)
    with open(base + ".json", "w", encoding="utf-8") as fh:
        json.dump({"results": results, "rows": all_rows}, fh, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
