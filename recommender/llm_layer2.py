"""Can a language model replace Layer 2?

The recommender's ordering claim is that the semantic filter must run before the
performance ranking, because implementations are not interchangeable. The
obvious 2026 objection is that a language model already knows all of this, so
the oracle-backed knowledge base in ``data/capabilities.json`` is redundant
effort. This module measures that.

The protocol is deliberately fair to the model. For each implementation it is
given exactly what a practitioner would have -- the name and the *published*
description, as the authors and SPMF state it -- and asked whether the
implementation satisfies a stated requirement. It is not given the audit. It is
scored against the audit.

What separates the cases that matter is not model quality but **where the truth
lives**, and the results split three ways:

``documented``     the published description carries the distinguishing cue, so
                   a careful reader can answer correctly. Example:
                   HUCI-Miner-Generators is described as operating on
                   high-utility itemsets, and the model does say no.

``semantic``       the description contains the answer but the distinction is
                   subtle enough to be read past. Example: Arima mines *minimal
                   rare* itemsets -- minimal in the maximum-support region,
                   which is the opposite side of the support axis from
                   support-minimality. The model reads "minimal" and agrees.

``measured_only``  no document anywhere states the truth, because it was
                   discovered by running the code against an oracle. Talky-G
                   and its diffset variant return non-minimal itemsets on 7 of
                   the 57 configurations they complete -- up to 13.8% of the
                   output -- while every published source describes them as
                   generator miners.

The third category is Layer 2's justification, and it is a claim about the
knowledge rather than about the model.

Measured on two model sizes, the categories move in opposite directions:

    category        n     qwen2.5-7b            qwen2.5-14b
                          correct / unsafe      correct / unsafe
    documented     46        37 / 6                41 / 1
    semantic        3         2 / 1                 3 / 0
    measured_only   2         1 / 1                 0 / 2
    overall        51      78.4% agreement       86.3% agreement

Capability buys the categories whose answer exists in text and loses the one
whose answer does not -- and loses it *because* of capability: the larger model
is confident, at 0.9, that Talky-G mines generators, which is what the
literature says and what the audit refutes. Scale and retrieval both operate on
written sources, so neither addresses this.

The measured-only category holds only two cases, which is a limit of how many
such defects the audit found rather than of the design. It is reported as two
cases, not as a rate.

    python -m recommender.llm_layer2                 # needs a local Ollama
    python -m recommender.llm_layer2 --model qwen2.5:14b-instruct
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(_HERE, "out")
CAPS = os.path.join(_HERE, "data", "capabilities.json")

DEFAULT_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
DEFAULT_MODEL = "qwen2.5:7b-instruct"

#: The published description of each implementation, as its authors and SPMF
#: state it. This is the input a practitioner has. It deliberately excludes
#: every finding of the audit -- that is the quantity being measured.
PUBLISHED = {
    "DefMe": "Depth-first mining of minimal generators from transactional data (SPMF).",
    "Gr_growth": "Gr-tree depth-first miner for frequent generators; the released binary takes a third argument k (Li et al.).",
    "Talky_G": "Vertical IT-tree miner for frequent generators using tidset intersections (SPMF).",
    "TalkyG_Diffset": "Talky-G with the diffset optimisation for vertical mining (SPMF).",
    "Pascal": "Counting-inference miner that identifies key patterns (generators) while mining frequent itemsets (SPMF).",
    "Zart": "Extends Pascal to also produce closed itemsets and their generators (SPMF).",
    "Apriori_Gen_Borgelt": "Borgelt's Apriori with target type 'generators' (-tg), mining free/key itemsets.",
    "Eclat_Gen_Borgelt": "Borgelt's Eclat with target type 'generators' (-tg), mining free/key itemsets.",
    "FPgrowth_Gen_Borgelt": "Borgelt's FP-growth with target type 'generators' (-tg), mining free/key itemsets.",
    "FEAT": "Mines frequent generator patterns from sequence databases (SPMF).",
    "FSGP": "Frequent sequential generator pattern mining (SPMF).",
    "VGEN": "Vertical mining of frequent sequential generator patterns (SPMF).",
    "HUG_Miner": "Mines high-utility generators: itemsets that are generators and whose utility meets the threshold (SPMF).",
    "GHUI_Miner": "Mines generators of high-utility itemsets (SPMF).",
    "HUCI_Miner_Generators": "Mines closed high-utility itemsets and post-processes them to obtain their generators (SPMF).",
    "FGC_Stream": "Incremental mining of frequent generators and closed itemsets over a sliding window (ICDM'21).",
    "Arima": "AprioriRare variant that mines minimal rare itemsets (SPMF).",
}

#: Requirements to ask about, and the measured family each one demands.
TARGETS = {
    "minimal_generator": (
        "MINIMAL GENERATORS from a TRANSACTIONAL dataset: the support-minimal "
        "itemsets, i.e. itemsets X such that no proper subset of X has the same "
        "support as X."),
    "sequential_generator": (
        "MINIMAL SEQUENTIAL GENERATORS from a SEQUENCE database: the "
        "support-minimal sequential patterns."),
    "high_utility_generator": (
        "HIGH-UTILITY GENERATORS from a dataset with item utilities: itemsets "
        "that are support-minimal AND whose own utility meets the threshold."),
}

#: Why a correct answer is or is not reachable from public documents. Keyed by
#: (implementation, target) for the cases where the two disagree in an
#: interesting way; everything else is a plain family match or mismatch.
KNOWABILITY = {
    ("HUCI_Miner_Generators", "high_utility_generator"): "documented",
    ("HUCI_Miner_Generators", "minimal_generator"): "documented",
    ("Arima", "minimal_generator"): "semantic",
    ("GHUI_Miner", "high_utility_generator"): "semantic",
    ("FGC_Stream", "minimal_generator"): "semantic",
    ("Talky_G", "minimal_generator"): "measured_only",
    ("TalkyG_Diffset", "minimal_generator"): "measured_only",
}

#: Gr-growth is deliberately NOT in the measured-only set. Its audit finding --
#: the undocumented third argument that switches to the disjunction-free family
#: at k >= 2 -- is measurement-only, but the yes/no question asked here is about
#: the default invocation, where it is a generator miner and any published
#: description says so. Counting it would inflate the measured-only category
#: with a case whose binary answer is in fact documented.
CAVEAT_ONLY = {("Gr_growth", "minimal_generator"): "k >= 2 silently changes family"}

PROMPT = """You advise a data scientist choosing a pattern-mining implementation.

The user needs {requirement}

Implementation offered: "{name}"
Published description: {description}

Is this implementation suitable for that requirement, as stated?
Reply as JSON only: {{"suitable": true or false, "confidence": 0.0 to 1.0, "reason": "<one sentence>"}}"""


# ----------------------------------------------------------------------
def load_truth():
    """Measured family and soundness for each implementation."""
    with open(CAPS, encoding="utf-8") as fh:
        impls = json.load(fh)["implementations"]
    return {r["id"]: r for r in impls}


def expected(rec, target):
    """Ground truth: may this implementation be handed to a user asking for `target`?

    Two ways to be unsuitable, and the distinction is the point. A *family*
    mismatch means the implementation computes something else. A *defect* means
    it computes the right family but returns members that violate it on some
    inputs, which only running it can reveal.
    """
    fam = rec.get("emits", {}).get("family")
    sound = rec.get("soundness", {}).get("status")
    if fam != target:
        return False, "wrong_family"
    if sound == "defective":
        return False, "defective"
    return True, "ok"


def ask(host, model, prompt, timeout=180):
    body = {"model": model, "stream": False, "format": "json",
            "options": {"temperature": 0, "seed": 0},
            "messages": [{"role": "user", "content": prompt}]}
    req = urllib.request.Request(host.rstrip("/") + "/api/chat",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        out = json.loads(r.read())
    return out["message"]["content"]


# ----------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--host", default=DEFAULT_HOST)
    args = ap.parse_args(argv)

    truth = load_truth()
    os.makedirs(OUT_DIR, exist_ok=True)

    rows = []
    t0 = time.time()
    for target, requirement in TARGETS.items():
        for impl, desc in PUBLISHED.items():
            rec = truth.get(impl)
            if rec is None:
                continue
            want, why = expected(rec, target)
            prompt = PROMPT.format(requirement=requirement, name=rec.get("display", impl),
                                   description=desc)
            try:
                raw = ask(args.host, args.model, prompt)
                got = json.loads(raw)
                said = bool(got.get("suitable"))
                conf = got.get("confidence")
                reason = str(got.get("reason", ""))[:120]
                err = ""
            except (urllib.error.URLError, OSError) as exc:
                print("cannot reach Ollama at %s (%s).\nStart it with:\n"
                      "  ~/.local/opt/ollama/bin/ollama serve" % (args.host, exc))
                return 1
            except (ValueError, KeyError) as exc:
                said, conf, reason, err = None, None, "", str(exc)[:60]
            rows.append({"target": target, "impl": impl, "expected": want,
                         "expected_why": why, "said": said, "confidence": conf,
                         "reason": reason, "error": err,
                         "knowability": KNOWABILITY.get((impl, target),
                                                        "documented")})
    elapsed = time.time() - t0

    # --- report -------------------------------------------------------
    L = ["=" * 78,
         "LLM AS LAYER 2  (model %s, %d questions, %.0fs)" % (args.model, len(rows), elapsed),
         "=" * 78,
         "",
         "  The model is given the name and the PUBLISHED description of each",
         "  implementation -- what a practitioner has -- and scored against the",
         "  audit, which it is not given.",
         ""]

    ok = [r for r in rows if r["said"] is not None]
    correct = [r for r in ok if r["said"] == r["expected"]]
    L.append("  overall agreement with the audit: %d / %d (%.1f%%)"
             % (len(correct), len(ok), 100 * len(correct) / max(len(ok), 1)))
    L.append("")

    # The dangerous error is the false positive: handing the user an
    # implementation that does not compute what they asked for.
    fp = [r for r in ok if r["said"] and not r["expected"]]
    fn = [r for r in ok if not r["said"] and r["expected"]]
    L.append("  UNSAFE answers (said yes, audit says no): %d" % len(fp))
    L.append("  over-cautious    (said no, audit says yes): %d" % len(fn))
    L.append("")

    L.append("  By where the truth lives:")
    L.append("  %-16s %8s %8s %9s   %s" % ("knowability", "n", "correct", "unsafe", "meaning"))
    L.append("  " + "-" * 74)
    meaning = {
        "documented": "description states it",
        "semantic": "stated but easy to misread",
        "measured_only": "in NO document; found by running the code",
    }
    for k in ("documented", "semantic", "measured_only"):
        grp = [r for r in ok if r["knowability"] == k]
        if not grp:
            continue
        c = sum(1 for r in grp if r["said"] == r["expected"])
        u = sum(1 for r in grp if r["said"] and not r["expected"])
        L.append("  %-16s %8d %8d %9d   %s" % (k, len(grp), c, u, meaning[k]))
    L.append("")

    if fp:
        L.append("  Every unsafe answer:")
        L.append("  %-22s %-22s %5s  %s" % ("implementation", "asked for", "conf", "why the audit says no"))
        L.append("  " + "-" * 92)
        for r in sorted(fp, key=lambda r: r["knowability"]):
            L.append("  %-22s %-22s %5s  %s [%s]"
                     % (r["impl"], r["target"], r["confidence"],
                        r["expected_why"], r["knowability"]))
        L.append("")

    mo = [r for r in ok if r["knowability"] == "measured_only"]
    if mo:
        n_bad = sum(1 for r in mo if r["said"] != r["expected"])
        L.append("  Of the %d measured-only cases the model gets %d wrong. These are"
                 % (len(mo), n_bad))
        L.append("  not failures of model capability: no document states the answer,")
        L.append("  so retrieval or a larger model cannot supply it. This is what")
        L.append("  Layer 2 is for, and it is a claim about the knowledge rather")
        L.append("  than about the model.")
    text = "\n".join(L) + "\n"
    print(text)
    tag = args.model.replace(":", "_").replace("/", "_")
    with open(os.path.join(OUT_DIR, "llm_layer2_%s.txt" % tag), "w", encoding="utf-8") as fh:
        fh.write(text)
    with open(os.path.join(OUT_DIR, "llm_layer2_%s.json" % tag), "w", encoding="utf-8") as fh:
        json.dump({"model": args.model, "rows": rows}, fh, indent=2)
    print("written: out/llm_layer2_%s.{txt,json}" % tag)
    return 0


if __name__ == "__main__":
    sys.exit(main())
