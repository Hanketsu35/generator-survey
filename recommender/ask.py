"""Point it at your data, ask in your own words, get an implementation.

    python -m recommender.ask --data mydata.txt \
        --ask "which items are bought together, with the fewest conditions?"

The existing CLI asks the user to already know the answer: it wants
``--family minimal_generator --data-type transactional --threshold 0.05``.
Someone who has a CSV and a question does not know any of those. This entry
point closes that gap, and the division of labour inside it is the one the
benchmark's own measurements force:

    the model UNDERSTANDS            free text + a sample of the file
                                     -> a MiningTask, validated against the
                                        formal schema

    measurement DECIDES              Layer 2 eligibility from the oracle-backed
                                     capability base; Layer 3 ranking from 667
                                     recorded runs

    the model EXPLAINS               the decision and the refusals, in the
                                     user's terms

The model is never allowed to decide eligibility. ``llm_layer2.py`` measures
why: asked whether an implementation satisfies a requirement, and given exactly
what a practitioner has, a model returns unsafe answers -- and a third of them
concern facts that appear in no document, because they were found by running
the code against an oracle. Talky-G returns non-minimal itemsets on 7 of 57
configurations; Gr-growth's undocumented third argument changes the pattern
family at k >= 2. No model can retrieve what nothing has written down.

Everything the model produces is checked before use: a family it invents is
rejected against ``spec.FAMILIES``, and the threshold it suggests is replaced
by one COMPUTED from the user's own file, because the support profile is
measurable and guessing it is unnecessary.

Without a local model this still works. ``--no-llm``, or simply having no
Ollama running, falls back to the rule extractor in ``nl.py``, and the
recommendation itself is unchanged -- only the parsing and the prose are.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

from . import landmarks as lm
from . import metafeatures as mf
from . import nl
from . import spec

_HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
DEFAULT_MODEL = os.environ.get("RECOMMENDER_LLM", "qwen2.5:7b-instruct")


# ----------------------------------------------------------------------
# 1. Look at the actual file. No model involved.
# ----------------------------------------------------------------------
def sniff_format(path, n_lines=200):
    """Guess the SPMF layout from the file's own content.

    Deterministic and cheap, and it precedes the model deliberately: the data
    type is a fact about the file, so asking a model to infer it from prose
    would be replacing a measurement with a guess.
    """
    seq = util = plain = 0
    with open(path, encoding="utf-8", errors="ignore") as fh:
        for i, line in enumerate(fh):
            if i >= n_lines:
                break
            s = line.strip()
            if not s or s.startswith("#") or s.startswith("@"):
                continue
            if s.count(":") >= 2:
                util += 1
            elif " -1" in s or s.endswith("-2"):
                seq += 1
            else:
                plain += 1
    if util > max(seq, plain):
        return "utility"
    if seq > max(util, plain):
        return "sequential"
    return "transactional"


def profile(path, data_type):
    """Structural summary plus a support profile, for the user and the model."""
    feats = mf.extract(path, data_type)
    out = {"data_type": data_type, "n_tx": feats["n_tx"], "n_items": feats["n_items"],
           "avg_len": round(feats["avg_len"], 2),
           "density": round(feats["density"], 4),
           "sup_gini": round(feats["sup_gini"], 3),
           "max_sup_ratio": round(feats["max_sup_ratio"], 3)}
    if data_type in ("transactional", "sequential"):
        probe = lm.DatasetProbe.build(path, data_type)
        rows = []
        for sigma in (0.5, 0.2, 0.1, 0.05, 0.02, 0.01):
            a = probe.at(sigma)
            rows.append({"sigma": sigma,
                         "frequent_items": int(round(a["frac_freq1"] * feats["n_items"])),
                         "frequent_pairs": int(round(10 ** a["log_n_freq2"] - 1)),
                         "generator_pairs_pct": round(100 * a["n_gen2_frac"], 1)})
        out["support_profile"] = rows
    return out


#: A threshold is worth suggesting when the level-2 sub-problem is neither
#: empty nor enormous. 100 frequent pairs is the smallest count at which the
#: output is a pattern set rather than a handful of coincidences.
MIN_USEFUL_PAIRS = 100


def suggest_threshold(prof, min_pairs=MIN_USEFUL_PAIRS):
    """A sigma that leaves a workable sub-problem, computed rather than guessed.

    Returns the LARGEST sigma whose frequent-pair count reaches ``min_pairs``:
    largest because a higher threshold is cheaper to mine and yields a smaller
    result, so the user should start there and lower it if they want more. The
    user cannot know what minsup means for *their* data, and neither can a
    model, but the file answers it directly -- which is why this is computed
    rather than asked of the model.
    """
    rows = prof.get("support_profile") or []
    if not rows:
        return None, "no support profile for this data type"
    for r in rows:
        if r["frequent_pairs"] >= min_pairs:
            return r["sigma"], ("%d of %d items and about %d item pairs are "
                                "frequent at this threshold"
                                % (r["frequent_items"], prof["n_items"],
                                   r["frequent_pairs"]))
    r = rows[-1]
    return r["sigma"], ("even at %g only %d item pairs are frequent; this data "
                        "may be too sparse for pattern mining"
                        % (r["sigma"], r["frequent_pairs"]))


# ----------------------------------------------------------------------
# 2. The model understands. Its output is validated, never trusted.
# ----------------------------------------------------------------------
UNDERSTAND_PROMPT = """You turn a data-mining question into a formal specification.

The user's data has already been measured, so do NOT guess these:
  data_type: {data_type}
  {n_tx} records, {n_items} distinct items, average record length {avg_len}

First lines of their file:
{sample}

Their question: {question}

Choose the pattern family that answers their question. The families are:
  minimal_generator      smallest itemsets identifying a group of records;
                         use for "fewest conditions", "minimal rules",
                         "simplest description"
  closed_itemset         largest itemsets with a given support
  generator_closure_pairs  both of the above, for association rules
  sequential_generator   as minimal_generator, but order matters
  high_utility_generator minimal itemsets whose VALUE (price, profit) is high
  minimal_rare_itemset   patterns that are RARE rather than frequent

Reply as JSON only:
{{"family": "<one of the names above>",
  "objective": "runtime" or "memory" or "balanced",
  "reason": "<one sentence, in the user's own terms>"}}"""


def ask_model(host, model, prompt, timeout=180):
    body = {"model": model, "stream": False, "format": "json",
            "options": {"temperature": 0, "seed": 0},
            "messages": [{"role": "user", "content": prompt}]}
    req = urllib.request.Request(host.rstrip("/") + "/api/chat",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())["message"]["content"]


def understand(question, prof, sample, host, model):
    """free text -> (MiningTask fields, how it was obtained, any complaint)."""
    prompt = UNDERSTAND_PROMPT.format(
        data_type=prof["data_type"], n_tx=prof["n_tx"], n_items=prof["n_items"],
        avg_len=prof["avg_len"], sample=sample, question=question)
    try:
        got = json.loads(ask_model(host, model, prompt))
    except (urllib.error.URLError, OSError) as exc:
        return None, "unavailable", "no model at %s (%s)" % (host, exc)
    except (ValueError, KeyError) as exc:
        return None, "unparseable", "model did not return usable JSON (%s)" % exc

    fam = got.get("family")
    if fam not in spec.FAMILIES:
        # Rejected rather than passed through: an invented family would be a
        # hard constraint nothing can satisfy, and the failure would surface as
        # "no implementation is eligible" rather than as a parsing error.
        return None, "rejected", ("model proposed family %r, which is not one of "
                                  "the measured families" % fam)
    obj = got.get("objective")
    fields = {"family": fam, "data_type": prof["data_type"]}
    if obj in spec.OBJECTIVES:
        fields["objective"] = obj
    return fields, "llm", got.get("reason", "")


EXPLAIN_PROMPT = """Explain a tool's recommendation to the person who asked.

Their question: {question}
Their data: {n_tx} records, {n_items} distinct items, {data_type}

The tool recommends: {choice}
Because: {why}
It ruled out: {excluded}
Suggested threshold: {threshold} ({threshold_why})

Write 3-4 sentences, plain language, addressed to them. Do not add facts, do
not name algorithms other than those above, and do not soften the exclusions --
they are measured, not opinions. Reply as JSON: {{"text": "<your explanation>"}}"""


# ----------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", required=True, help="path to the user's dataset")
    ap.add_argument("--ask", default="", help="the question, in plain language")
    ap.add_argument("--threshold", type=float, help="override the computed threshold")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--host", default=DEFAULT_HOST)
    ap.add_argument("--no-llm", action="store_true",
                    help="use the rule extractor instead of a model")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if not os.path.exists(args.data):
        print("no such file: %s" % args.data)
        return 1

    # --- 1. measure -------------------------------------------------
    data_type = sniff_format(args.data)
    prof = profile(args.data, data_type)
    with open(args.data, encoding="utf-8", errors="ignore") as fh:
        sample = "".join([next(fh, "") for _ in range(3)]).strip()

    # --- 2. understand ----------------------------------------------
    note = ""
    fields, source = None, "rules"
    if args.ask and not args.no_llm:
        fields, source, note = understand(args.ask, prof, sample, args.host, args.model)
    if fields is None:
        got = nl.RuleExtractor().extract(args.ask) if args.ask else {}
        fields = {k: v for k, v in got.items() if v is not None}
        fields.setdefault("family", "minimal_generator")
        fields["data_type"] = prof["data_type"]
        source = "rules" if source in ("rules", None) else source

    thr = args.threshold
    thr_why = "given on the command line"
    if thr is None:
        thr, thr_why = suggest_threshold(prof)

    # --- 3. decide: unchanged, measurement-backed -------------------
    from .engine import Recommender, format_report
    kw = {k: v for k, v in fields.items()
          if k in spec.MiningTask.__dataclass_fields__}
    kw["dataset_path"] = args.data
    kw["threshold"] = thr
    task = spec.MiningTask(**kw)
    recs, rejected, feats = Recommender().recommend(task)
    report = format_report(task, recs, rejected, feats)

    if args.json:
        print(json.dumps({"profile": prof, "task": fields, "threshold": thr,
                          "source": source, "note": note,
                          "recommended": recs[0].algorithm if recs else None,
                          "eligible": [r.algorithm for r in recs],
                          "rejected": {v.algorithm: v.reasons for v in rejected}},
                         indent=2, default=str))
        return 0

    print("=" * 78)
    print("YOUR DATA  (measured, not guessed)")
    print("=" * 78)
    print("  format %s | %d records | %d distinct items | average length %.1f"
          % (prof["data_type"], prof["n_tx"], prof["n_items"], prof["avg_len"]))
    if prof.get("support_profile"):
        print()
        print("  %-10s %16s %16s %18s" % ("threshold", "frequent items",
                                          "frequent pairs", "of which minimal"))
        for r in prof["support_profile"]:
            mark = "  <- suggested" if r["sigma"] == thr else ""
            print("  %-10g %16d %16d %17.1f%%%s"
                  % (r["sigma"], r["frequent_items"], r["frequent_pairs"],
                     r["generator_pairs_pct"], mark))
    print()
    print("  suggested threshold %s -- %s" % (thr, thr_why))
    print()
    print("=" * 78)
    print("WHAT YOU ASKED FOR  (parsed by: %s)" % source)
    print("=" * 78)
    if note:
        print("  %s" % note)
    for k, v in sorted(fields.items()):
        print("  %-12s %s" % (k, v))
    print()
    print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
