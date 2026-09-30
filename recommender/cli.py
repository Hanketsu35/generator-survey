"""Command-line front end.

    python -m recommender.cli --dataset mushroom --threshold 0.05
    python -m recommender.cli --dataset foodmart --data-type utility \\
        --family high_utility_generator --threshold 50
    python -m recommender.cli --data-path mydata.txt --threshold 0.1 \\
        --max-memory 512 --objective memory
    python -m recommender.cli --dataset chess --threshold 0.3 --trust allow_defective
"""
import argparse
import json
import sys

from .spec import MiningTask, FAMILIES, DATA_TYPES, TRUST_LEVELS, OBJECTIVES
from .engine import Recommender, format_report


def build_parser():
    p = argparse.ArgumentParser(
        prog="python -m recommender.cli",
        description="Semantics-aware algorithm recommendation for minimal-generator mining.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__)
    g = p.add_argument_group("instance")
    g.add_argument("--ask", metavar="TEXT",
                   help="state the request in natural language; Layer 1 converts "
                        "it to a specification, which explicit flags then override")
    g.add_argument("--dataset", help="named benchmark dataset (meta-features cached)")
    g.add_argument("--data-path", help="path to a dataset to profile directly")
    g.add_argument("--threshold", type=float, help="minsup / maxsup / min_utility")

    s = p.add_argument_group("semantic requirements")
    s.add_argument("--data-type", default="transactional", choices=DATA_TYPES)
    s.add_argument("--family", default="minimal_generator", choices=FAMILIES)
    s.add_argument("--boundary", default="any", choices=["floor", "ceil", "any"],
                   help="required threshold-rounding convention")
    s.add_argument("--empty-set", default="any", choices=["yes", "no", "any"],
                   help="must the empty pattern be present in the output?")
    s.add_argument("--trust", default="verified_only", choices=TRUST_LEVELS)
    s.add_argument("--no-post-filter", action="store_true",
                   help="reject implementations that need a post-filter")

    b = p.add_argument_group("operational budget")
    b.add_argument("--max-runtime", type=float, metavar="S")
    b.add_argument("--max-memory", type=float, metavar="MB")
    b.add_argument("--objective", default="balanced", choices=OBJECTIVES)

    o = p.add_argument_group("output")
    o.add_argument("--top", type=int, help="show only the top N")
    o.add_argument("--json", action="store_true", help="emit JSON instead of a report")
    o.add_argument("--no-probe", action="store_true",
                   help="do not probe the native miners on --data-path (by default a "
                        "memory request on a transactional file is probed; see "
                        "recommender/probe.py)")
    o.add_argument("--hide-rejected", action="store_true")
    o.add_argument("--exclude-dataset", metavar="NAME",
                   help="train the performance model without this dataset "
                        "(leave-one-dataset-out honesty check)")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    if not args.dataset and not args.data_path:
        print("error: give --dataset or --data-path", file=sys.stderr)
        return 2

    empty = {"yes": True, "no": False, "any": None}[args.empty_set]
    fields = dict(
        data_type=args.data_type, family=args.family, boundary=args.boundary,
        include_empty=empty, trust=args.trust,
        allow_post_filter=not args.no_post_filter,
        threshold=args.threshold,
        max_runtime_s=args.max_runtime, max_memory_mb=args.max_memory,
        objective=args.objective)

    if args.ask:
        from .nl import RuleExtractor
        extracted = RuleExtractor().extract(args.ask)
        # An explicit flag always wins over the parsed text; only fields the
        # user left at their default are taken from the request.
        defaults = build_parser().parse_args(["--dataset", "_"])
        for k, v in extracted.items():
            if k == "include_empty":
                if args.empty_set == "any":
                    fields["include_empty"] = v
            elif k == "allow_post_filter":
                if not args.no_post_filter:
                    fields["allow_post_filter"] = v
            elif k in fields:
                cli_name = {"max_runtime_s": "max_runtime",
                            "max_memory_mb": "max_memory"}.get(k, k)
                if getattr(args, cli_name, None) == getattr(defaults, cli_name, None):
                    fields[k] = v
        print("Layer 1 parsed: %s\n" % json.dumps(extracted, sort_keys=True))

    task = MiningTask(dataset=args.dataset, dataset_path=args.data_path, **fields)

    rec = Recommender(exclude_dataset=args.exclude_dataset)
    pr = None
    if not args.no_probe and rec.should_probe(task):
        from .probe import probe
        pr = probe(task.dataset_path, float(task.threshold))
        if not args.json:
            print("probe: native miners %s on %s in %.1f s"
                  % ("measured" if pr.mode == "direct" else "sampled", task.dataset_path,
                     pr.wall_s))
            from .probe import none_finished, NONE_FINISHED
            if none_finished(pr):
                print("probe: ! %s" % NONE_FINISHED)
    recs, rejected, feats = rec.recommend(task, top=args.top, probe=pr)

    if args.json:
        payload = {
            "request": task.to_dict(),
            "meta_features": feats,
            "recommendations": [
                {"algorithm": r.algorithm, "display": r.display, "match": r.match,
                 "predicted_runtime_s": round(r.runtime_s, 4),
                 "predicted_memory_mb": round(r.memory_mb, 2),
                 "memory_interval_90": ([round(x, 2) for x in r.memory_interval]
                                        if r.memory_interval else None),
                 "runtime_interval_90": ([round(x, 4) for x in r.runtime_interval]
                                         if r.runtime_interval else None),
                 "p_complete": round(r.p_complete, 4),
                 "expected_par10_cost": round(r.expected_cost, 3),
                 "on_pareto_front": r.on_pareto_front,
                 "within_budget": r.within_budget,
                 "prediction_source": r.prediction_source,
                 "reasons": r.reasons, "warnings": r.warnings,
                 "budget_notes": r.budget_notes, "post_filter": r.post_filter}
                for r in recs],
            "excluded": [
                {"algorithm": v.algorithm, "display": v.display, "reasons": v.reasons}
                for v in rejected],
        }
        print(json.dumps(payload, indent=2))
    else:
        print(format_report(task, recs, rejected, feats,
                            show_rejected=not args.hide_rejected))
    return 0


if __name__ == "__main__":
    sys.exit(main())
