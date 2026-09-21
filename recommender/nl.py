"""Layer 1 - natural language to a formal MiningTask.

Two extractors share one interface:

  ``RuleExtractor``  keyword and regular-expression matching. It is the
                     BASELINE, and it exists so that the LLM has something to
                     beat. A front end that cannot beat regular expressions on
                     this task is decoration, and should be reported as such.

  ``LLMExtractor``   an Anthropic model prompted with the field schema. It
                     needs ANTHROPIC_API_KEY in the environment; without one
                     it raises rather than silently degrading.

``python -m recommender.nl --eval`` scores whichever extractors are available
against ``data/nl_queries.json``, field by field, and prints a per-field
breakdown so that a headline accuracy cannot hide a field the extractor
never gets right.
"""
import argparse
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
QUERIES = os.path.join(_HERE, "data", "nl_queries.json")

SCORED_FIELDS = ("data_type", "family", "threshold", "boundary", "include_empty",
                 "trust", "objective", "max_runtime_s", "max_memory_mb",
                 "allow_post_filter")

SCHEMA_DOC = """
data_type        : transactional | sequential | utility | graph
family           : minimal_generator | disjunction_free | sequential_generator
                 | generator_closure_pairs | closed_itemset
                 | high_utility_generator | ghui | utility_minimal
                 | minimal_rare_itemset
threshold        : number (relative support, max support, or absolute utility)
boundary         : floor | ceil | any     (which side of a non-integral
                                           absolute threshold is kept)
include_empty    : true | false | null    (must the empty pattern be reported?)
trust            : verified_only | allow_unvalidated | allow_defective
objective        : runtime | memory | balanced
max_runtime_s    : number of seconds, or null
max_memory_mb    : number of megabytes, or null
allow_post_filter: true | false
""".strip()


# ======================================================================
class RuleExtractor:
    name = "rules"

    FAMILY_PATTERNS = [
        ("utility_minimal", r"minimal with respect to utility|utility[- ]minimal"),
        ("ghui", r"\bghui\b|high[- ]utility.*closure|closure.*high[- ]utility"),
        ("high_utility_generator", r"high[- ]?utility"),
        ("minimal_rare_itemset", r"rare\b|maximum support|max support"),
        ("disjunction_free", r"disjunction[- ]free"),
        ("generator_closure_pairs", r"generators? and (the )?closed|closed sets? of each|"
                                    r"both the generators?"),
        ("closed_itemset", r"\bclosed itemsets?\b|\bclosed sets?\b"),
        ("sequential_generator", r"sequen|subsequence|clickstream|event log|corpus"),
        ("minimal_generator", r"minimal generator|generator"),
    ]

    def extract(self, text):
        t = text.lower()
        out = {}

        # --- family first: it usually implies the data type --------------
        for fam, pat in self.FAMILY_PATTERNS:
            if re.search(pat, t):
                out["family"] = fam
                break

        # --- data type ----------------------------------------------------
        if re.search(r"sequen|subsequence|clickstream|event log|corpus|"
                     r"sequences of events", t):
            out["data_type"] = "sequential"
        elif re.search(r"utility|price|profit|basket data with", t):
            out["data_type"] = "utility"
        else:
            out["data_type"] = "transactional"
        # An unstated family is not an extraction failure: within a
        # generator-mining tool the default for each input type is
        # well-defined, and MiningTask uses the same defaults.
        if "family" not in out:
            out["family"] = {"sequential": "sequential_generator",
                             "utility": "high_utility_generator",
                             "transactional": "minimal_generator"}[out["data_type"]]
        fam = out.get("family")
        if fam in ("high_utility_generator", "ghui", "utility_minimal"):
            out["data_type"] = "utility"
        elif fam == "sequential_generator":
            out["data_type"] = "sequential"
        elif fam in ("minimal_generator", "disjunction_free",
                     "generator_closure_pairs", "closed_itemset",
                     "minimal_rare_itemset"):
            out["data_type"] = "transactional"

        # --- threshold ----------------------------------------------------
        thr = None
        m = re.search(r"(\d+(?:\.\d+)?)\s*(?:%|percent)", t)
        if m:
            thr = float(m.group(1)) / 100.0
        if thr is None:
            m = re.search(r"(?:minsup|min support|minimum support|maxsup|"
                          r"maximum support|max support|support|utility|threshold)"
                          r"\D{0,20}?(\d*\.?\d+)", t)
            if m:
                thr = float(m.group(1))
        if thr is None:
            m = re.search(r"threshold\s+(?:of\s+)?(\d*\.?\d+)", t)
            if m:
                thr = float(m.group(1))
        if thr is None:
            # the number can precede the keyword: "0.3 minsup", "50 utility"
            m = re.search(r"(\d*\.?\d+)\s*(?:minsup|maxsup|min(?:imum)? support|"
                          r"max(?:imum)? support|support|utility)", t)
            if m:
                thr = float(m.group(1))
        if thr is None and re.search(r"half a percent", t):
            thr = 0.005
        if thr is not None:
            out["threshold"] = thr

        # --- boundary -----------------------------------------------------
        if re.search(r"round(ed)?[- ]down|floor|rounded-down", t):
            out["boundary"] = "floor"
        elif re.search(r"ceil|round(ed)?[- ]up", t):
            out["boundary"] = "ceil"

        # --- empty set ----------------------------------------------------
        if re.search(r"empty set", t):
            neg = re.search(r"(not|no|without|exclude|absent)\b[^.]{0,30}empty set|"
                            r"empty set[^.]{0,30}\b(not|absent|excluded)", t)
            out["include_empty"] = not bool(neg)

        # --- trust --------------------------------------------------------
        if re.search(r"known bugs?|even.*bugg|including.*bug|compare.*bug", t):
            out["trust"] = "allow_defective"
        elif re.search(r"verified|validated|oracle|trust", t):
            out["trust"] = "verified_only"

        # --- objective ----------------------------------------------------
        if re.search(r"fastest|don't care about memory|optimi[sz]e for speed|"
                     r"as fast as", t):
            out["objective"] = "runtime"
        elif re.search(r"memory is|optimi[sz]e for memory|tight.*memory|"
                       r"memory.*tight|lowest memory", t):
            out["objective"] = "memory"
        elif re.search(r"balance", t):
            out["objective"] = "balanced"

        # --- budgets ------------------------------------------------------
        m = re.search(r"(\d+(?:\.\d+)?)\s*(gb|gigabytes?)", t)
        if m:
            out["max_memory_mb"] = float(m.group(1)) * 1024
        else:
            m = re.search(r"(?:under|below|at most|max(?:imum)?|less than)?\s*"
                          r"(\d+(?:\.\d+)?)\s*(mb|megabytes?)", t)
            if m:
                out["max_memory_mb"] = float(m.group(1))
        if re.search(r"half a gig", t):
            out["max_memory_mb"] = 512.0

        m = re.search(r"(\d+(?:\.\d+)?)\s*(seconds?|s\b)", t)
        if m:
            out["max_runtime_s"] = float(m.group(1))
        else:
            m = re.search(r"(\d+(?:\.\d+)?)\s*(minutes?|mins?)", t)
            if m:
                out["max_runtime_s"] = float(m.group(1)) * 60
            elif re.search(r"two minutes", t):
                out["max_runtime_s"] = 120.0
            elif re.search(r"half an hour", t):
                out["max_runtime_s"] = 1800.0
            elif re.search(r"an hour", t):
                out["max_runtime_s"] = 3600.0

        # --- post-filter --------------------------------------------------
        if re.search(r"no post[- ]?process|without post[- ]?process|direct miner|"
                     r"don't want anything that needs a post", t):
            out["allow_post_filter"] = False

        return out


# ======================================================================
class LLMExtractor:
    name = "llm"

    PROMPT = """You convert a data-mining request into a formal specification.

Return ONLY a JSON object. Use exactly these fields, and use null for any field
the request does not determine. Do not guess.

%s

Request: %%s
JSON:""" % SCHEMA_DOC

    def __init__(self, model="claude-opus-5"):
        self.model = model
        try:
            import anthropic          # noqa: F401
        except ImportError:
            raise RuntimeError("pip install anthropic")
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise RuntimeError("ANTHROPIC_API_KEY is not set")
        import anthropic
        self.client = anthropic.Anthropic()

    def extract(self, text):
        msg = self.client.messages.create(
            model=self.model, max_tokens=512,
            messages=[{"role": "user", "content": self.PROMPT % text}])
        raw = msg.content[0].text.strip()
        raw = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.M).strip()
        got = json.loads(raw)
        return {k: v for k, v in got.items() if v is not None}


# ======================================================================
def score(extractor, queries):
    """Field-level accuracy over the fields each query actually determines."""
    per_field = {f: [0, 0] for f in SCORED_FIELDS}   # [correct, total]
    exact, rows = 0, []
    for q in queries:
        try:
            got = extractor.extract(q["text"])
            err = None
        except Exception as e:                        # an extractor may fail
            got, err = {}, str(e)
        want = q["spec"]
        ok_all = True
        detail = {}
        for f, v in want.items():
            if f not in SCORED_FIELDS or v is None:
                continue
            g = got.get(f)
            hit = (g == v) or (
                isinstance(v, (int, float)) and isinstance(g, (int, float))
                and abs(float(g) - float(v)) < 1e-9)
            per_field[f][0] += int(hit)
            per_field[f][1] += 1
            detail[f] = (v, g, hit)
            ok_all &= hit
        exact += int(ok_all)
        rows.append({"id": q["id"], "text": q["text"], "exact": ok_all,
                     "detail": detail, "error": err})
    return {"exact_match": exact / max(len(queries), 1),
            "per_field": {f: (c / t if t else None) for f, (c, t) in per_field.items()},
            "per_field_n": {f: t for f, (c, t) in per_field.items()},
            "rows": rows}


def load_queries(path=QUERIES):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)["queries"]


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m recommender.nl")
    ap.add_argument("--eval", action="store_true", help="score the extractors")
    ap.add_argument("--llm", action="store_true", help="include the LLM extractor")
    ap.add_argument("--model", default="claude-opus-5")
    ap.add_argument("--text", help="parse one request and print the spec")
    args = ap.parse_args(argv)

    if args.text:
        print(json.dumps(RuleExtractor().extract(args.text), indent=2))
        return 0

    if not args.eval:
        ap.print_help()
        return 0

    queries = load_queries()
    extractors = [RuleExtractor()]
    if args.llm:
        try:
            extractors.append(LLMExtractor(args.model))
        except RuntimeError as e:
            print("LLM extractor unavailable: %s" % e)

    results = {}
    for ex in extractors:
        r = score(ex, queries)
        results[ex.name] = r
        print("\n" + "=" * 70)
        print("extractor: %s   (%d queries)" % (ex.name, len(queries)))
        print("=" * 70)
        print("  exact-match on all determined fields : %.1f%%"
              % (100 * r["exact_match"]))
        print("\n  %-20s %8s %8s" % ("field", "n", "accuracy"))
        print("  " + "-" * 38)
        for f in SCORED_FIELDS:
            n = r["per_field_n"][f]
            if n:
                print("  %-20s %8d %7.1f%%" % (f, n, 100 * r["per_field"][f]))
        if r["exact_match"] >= 0.95:
            print("")
            print("  WARNING -- the baseline saturates this query set. Two things")
            print("  follow, and both must be reported rather than hidden:")
            print("   1. An LLM front end cannot be justified by accuracy on this")
            print("      set; there is no headroom. Either the set gets harder or")
            print("      Layer 1 is presentation, not contribution.")
            print("   2. The set was written by the same author as the rules. A")
            print("      credible Layer 1 evaluation needs queries authored")
            print("      independently -- ideally collected from real users -- and")
            print("      containing genuinely ambiguous and underspecified requests.")
        misses = [x for x in r["rows"] if not x["exact"]]
        if misses:
            print("\n  misses (%d):" % len(misses))
            for m in misses:
                bad = {k: v for k, v in m["detail"].items() if not v[2]}
                print("    %-5s %s" % (m["id"], m["text"][:62]))
                for k, (want, got, _) in bad.items():
                    print("          %-16s want %-24r got %r" % (k, want, got))

    out = os.path.join(_HERE, "out")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "nl_eval.json"), "w", encoding="utf-8") as fh:
        json.dump({k: {kk: vv for kk, vv in v.items() if kk != "rows"}
                   for k, v in results.items()}, fh, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
