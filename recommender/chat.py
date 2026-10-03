"""A local chat interface: bring your data, ask in your own words.

    python -m recommender.chat            # then open http://127.0.0.1:8765

Everything stays on the machine -- the uploaded file, the models, the language
model (Ollama). No dependency beyond the standard library is added: the pinned
numerical stack (numpy < 2) rules out the usual UI frameworks, and a single
page served by http.server is enough.

The conversation keeps the recommender's division of labour, and adds nothing
the model is trusted with:

  file      measured, never asked: format sniffed, CSV converted (ingest.py),
            meta-features and the support profile computed, a threshold
            suggested from that profile
  question  first turn: ask.understand_consistent -- the path scored on the
            held-out split (96.6% family accuracy, asks back on goal-less
            questions). A goal-less question returns the options as buttons,
            filtered to the families this file's data type can serve.
            Later turns: a REVISE prompt extracts only what changed (family,
            objective, threshold, budgets); every value is validated before
            use and anything invalid is dropped with a note.
  decision  Layer 2 and Layer 3, unchanged -- the engine, with its tiers,
            refusals and "not installed here" markers.
  prose     the model explains the decision in the user's language, from the
            decision's own facts only. The explanation is then CHECKED: if it
            names an implementation that is neither recommended nor among the
            refusals, or writes a number it was not given, it is thrown away
            and a template explanation is used instead. A reason invented
            without a name or a number still passes -- the page says what was
            checked, not "verified".

If Ollama is not running, understanding falls back to the rule extractor and
the explanation to the template; the page says so.
"""
import argparse
import json
import os
import re
import shutil
import sys
import tempfile
import threading
import uuid
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import ask
from . import ingest
from . import metafeatures as mf
from . import nl
from . import spec

_HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(_HERE, "web")
_ROOT = os.path.dirname(_HERE)
MAX_UPLOAD = 400 * 1024 * 1024

#: The goal-less options, as outcomes rather than family names, keyed by the
#: data type that can serve them. Offering a family the file cannot serve would
#: only produce "no eligible implementation" one click later.
OPTIONS = {
    "transactional": [
        ("minimal_generator", "the shortest description that identifies each group of records",
         "her kayıt grubunu ayırt eden en kısa tanım"),
        ("closed_itemset", "the complete set of items each group of records shares",
         "her kayıt grubunun ortak olarak içerdiği tüm ürünler"),
        ("generator_closure_pairs", "exact rules: \"if these are present, those always are too\"",
         "kesin kurallar: \"bunlar varsa, şunlar da hep vardır\""),
        ("minimal_rare_itemset", "combinations that are unusually rare",
         "alışılmadık derecede nadir görülen birliktelikler"),
    ],
    "sequential": [("sequential_generator", "the shortest ordered patterns that identify each group",
                    "her grubu ayırt eden en kısa sıralı örüntüler")],
    "utility": [("high_utility_generator", "the shortest combinations worth the most",
                 "en çok değer getiren en kısa birliktelikler")],
}

#: How each implementation may be named in prose, for the explanation check.
#: Word boundaries matter: "feat" must not match "feature".
NAME_PATTERNS = {
    "FPgrowth_Gen_Borgelt": r"fp-?growth", "Eclat_Gen_Borgelt": r"\beclat\b",
    "Apriori_Gen_Borgelt": r"\bapriori\b", "Gr_growth": r"\bgr-?growth\b",
    "DefMe": r"\bdefme\b", "Pascal": r"\bpascal\b", "Zart": r"\bzart\b",
    "Talky_G": r"\btalky", "TalkyG_Diffset": r"\btalky", "Arima": r"\barima\b",
    "HUCI_Miner_Generators": r"\bhuci", "GHUI_Miner": r"\bghui", "HUG_Miner": r"\bhug-?miner",
    "FEAT": r"\bfeat\b", "FSGP": r"\bfsgp\b", "VGEN": r"\bvgen\b", "FGC_Stream": r"\bfgc",
}

REVISE_PROMPT = """A user is refining a data-mining request. Report ONLY what their
new message changes; use null for anything it does not change.

Their data (measured): {data_type}, {n_tx} records, {n_items} items.
Current request: family={family}, objective={objective}, threshold={threshold},
max_memory_mb={max_memory_mb}, max_runtime_s={max_runtime_s}

Families: minimal_generator (shortest identifying descriptions),
closed_itemset (complete shared item sets), generator_closure_pairs (exact
rules), minimal_rare_itemset (rare combinations), sequential_generator,
high_utility_generator (combinations ranked by value).
A threshold is a support fraction between 0 and 1 (e.g. "5%" is 0.05), except
for high_utility_generator, where it is a minimum utility amount.

Their message (any language): {message}

Reply as JSON only:
{{"family": null or a family name, "objective": null or "runtime" or "memory" or "balanced",
  "threshold": null or a number, "max_memory_mb": null or a number,
  "max_runtime_s": null or a number}}"""

EXPLAIN_PROMPT = """Explain a recommendation to the person who asked. Write in
{language}. 3 to 5 sentences, plain words, no headings.

Their message: {message}
Their data: {n_tx} records, {n_items} distinct items ({data_type}); read as: {how}
What they asked for: {goal}; optimising {objective}{budget}
Threshold used: {threshold} -- {threshold_why}

Recommended: {top} -- {top_cost}
Equally good (the data cannot separate them): {ties}
{runnable}
{caveats}
Excluded, and why: {excluded}

Rules:
- State only the facts above. Do NOT explain WHY an algorithm is faster or
  smaller, and do not describe the data beyond the numbers given: no reasons
  that are not listed here.
- Name no algorithm other than the ones above.
- Any number you write must be one of the numbers above.
- The exclusions are measured, not opinions: do not soften them.
- Every caveat listed above must be stated plainly.
Reply as JSON: {{"text": "..."}}"""


def _turkish(text):
    return bool(re.search(r"[ğüşıöçĞÜŞİÖÇ]|\b(ve|bir|bu|hangi|için|mi|mı|ne)\b", text or ""))


# ----------------------------------------------------------------------
# Keyword reading of a request when no language model is running, in both
# languages of the interface. nl.RuleExtractor is English only, and the
# chat used to take nothing from it but the family: "en az bellek" and even
# "optimise for memory" left the objective at balanced, and a follow-up was
# not read at all. Its rules are scored in the Layer-1 experiments, so they
# are not changed; this reads what the chat needs on top of them.
_MEM = r"(memory|ram\b|bellek|hafıza|hafiza)"
_FAST = r"(fast|speed|quick|runtime|hızlı|hizli|hız\b|hiz\b|çabuk|cabuk|süre|sure\b|zaman)"
_DONT = r".{0,25}(önemli değil|onemli degil|umurumda değil|fark etmez|farketmez|" \
        r"don't care|do not care|doesn't matter|does not matter|not important)"
_NUM = r"(\d+(?:[.,]\d+)?)"


def _f(x):
    return float(x.replace(",", "."))


def keyword_fields(text):
    """Objective, threshold and budgets read from ``text`` by keywords.

    Returns only what the text states; an empty dict when it states nothing.
    """
    t = text.lower()
    got = {k: v for k, v in nl.RuleExtractor().extract(text).items()
           if k in ("objective", "threshold", "max_memory_mb", "max_runtime_s")
           and v is not None}
    mem = re.search(_MEM, t) and not re.search(_MEM + _DONT, t)
    fast = re.search(_FAST, t) and not re.search(_FAST + _DONT, t)
    if re.search(_MEM + _DONT, t) and re.search(_FAST, t):
        fast, mem = True, False
    # a memory BUDGET mentions memory without asking to minimise it
    if mem and re.search(_NUM + r"\s*(gb|mb|giga|mega)", t) and not re.search(
            r"en az|az bellek|least|lowest|minimi|düşük|dusuk|kısıtlı|kisitli|tight|"
            r"limited|sınırlı|sinirli", t):
        mem = False
    if re.search(r"denge|dengeli|balance", t) or (mem and fast):
        got["objective"] = "balanced"
    elif mem:
        got["objective"] = "memory"
    elif fast:
        got["objective"] = "runtime"
    m = re.search(_NUM + r"\s*(gb|gigabayt|gigabyte)", t)
    if m:
        got["max_memory_mb"] = _f(m.group(1)) * 1024
    else:
        m = re.search(_NUM + r"\s*(mb|megabayt|megabyte)", t)
        if m:
            got["max_memory_mb"] = _f(m.group(1))
    for unit, mult in ((r"(saniye|sn\b|seconds?|secs?\b|s\b)", 1), (r"(dakika|dk\b|minutes?|mins?\b)", 60),
                       (r"(saat|hours?)", 3600)):
        m = re.search(_NUM + r"\s*" + unit, t)
        if m:
            got["max_runtime_s"] = _f(m.group(1)) * mult
            break
    m = re.search(r"%\s*" + _NUM, t) or re.search(_NUM + r"\s*(%|percent|yüzde)", t) \
        or re.search(r"yüzde\s*" + _NUM, t)
    if m:
        got["threshold"] = _f(m.group(1)) / 100.0
    else:
        m = re.search(r"(destek|eşik|esik|support|minsup|threshold)\D{0,15}?" + _NUM, t) \
            or re.search(_NUM + r"\s*(destek|eşik|esik|support|minsup)", t)
        if m:
            got["threshold"] = _f(m.group(2) if m.group(1).isalpha() else m.group(1))
    return got


def _num(x):
    """A number as the explanation prompt shows it -- and as the check expects it."""
    if x is None:
        return "?"
    x = float(x)
    return "%d" % round(x) if abs(x) >= 100 else ("%.2g" % x if abs(x) < 1 else "%.1f" % x)


def _cost(r):
    """The predicted cost as the explanation may quote it -- or not at all.

    Outside the training data the numbers are extrapolations; given to the
    model they would be repeated as predictions, so they are withheld.
    """
    if r.extrapolated:
        return "costs not predicted: this data is outside what it was measured on"
    return "predicted %s s, %s MB" % (_num(r.runtime_s), _num(r.memory_mb))


def _caveats(r):
    out = []
    if r.extrapolated and any("budget" in n for n in r.budget_notes if n):
        # The budget check compares an extrapolated number with the budget;
        # quoting either side would present the extrapolation as a prediction.
        out.append("CAVEAT: whether %s fits the stated budget cannot be predicted "
                   "for this data" % r.display)
    elif not r.within_budget:
        out.append("CAVEAT: %s is predicted to exceed the stated budget (%s); nothing "
                   "eligible is predicted to fit it" % (r.display, "; ".join(
                       n for n in r.budget_notes if "budget" in n)))
    if r.extrapolated:
        out.append("CAVEAT: the ranking is an extrapolation -- the data is outside "
                   "the range the costs were measured on (%s)" % "; ".join(r.extrapolated))
    return "\n".join(out)


def _checked(text, facts, allowed, must_mention=()):
    """Does an explanation stay within what it was given?

    Two mechanical checks, both of which the model's first explanations failed
    in testing: it named no forbidden algorithm, but it did add reasons of its
    own ("the others produce unnecessary data"). Neither check can catch every
    invented reason -- a sentence with no name and no number passes -- so the
    interface labels the text as model-written with names and numbers checked,
    not as verified.

      names    every implementation it mentions is recommended, tied, or
               among the exclusions it was shown;
      numbers  every number it writes appears in the facts it was given;
      caveats  each group in ``must_mention`` is named by one of its words --
               added because the first explanation of an over-budget pick
               left the budget out entirely.
    """
    low = text.lower()
    if any(not any(w in low for w in words) for words in must_mention):
        return False
    for algo, pat in NAME_PATTERNS.items():
        if algo in allowed or any(NAME_PATTERNS.get(b) == pat for b in allowed):
            continue
        if re.search(pat, text, re.I):
            return False
    given = set(re.findall(r"\d+(?:[.,]\d+)?", facts))
    given |= {g.replace(".", ",") for g in given} | {g.replace(",", ".") for g in given}
    for n in re.findall(r"\d+(?:[.,]\d+)?", text):
        if n not in given:
            return False
    return True


class Session:
    def __init__(self, sid, workdir):
        self.id = sid
        self.lang = "en"
        self.probes = {}
        self.dir = workdir
        self.path = None
        self.info = {}
        self.profile = None
        self.sample = ""
        self.task = None               # dict of MiningTask fields, or None
        self.threshold = None
        self.threshold_why = ""
        self.pending = None            # "family" | "utility_threshold" | None
        self.history = []
        self.lock = threading.Lock()


class App:
    def __init__(self, model, host, samples, use_llm=True):
        self.model, self.host, self.samples = model, host, samples
        self.use_llm = use_llm
        self.sessions = {}
        self.workdir = tempfile.mkdtemp(prefix="recommender_chat_")
        self._rec = None
        self._rec_err = None
        self._rec_ready = threading.Event()
        threading.Thread(target=self._load_engine, daemon=True).start()

    # --- engine: fitted (or loaded from cache) once, in the background -------
    def _load_engine(self):
        try:
            from .engine import Recommender
            self._rec = Recommender()
        except Exception as exc:                        # noqa: BLE001
            self._rec_err = "%s: %s" % (type(exc).__name__, exc)
        self._rec_ready.set()

    def engine(self):
        self._rec_ready.wait()
        if self._rec is None:
            raise RuntimeError("the recommender could not be loaded: %s" % self._rec_err)
        return self._rec

    def llm_up(self):
        if not self.use_llm:
            return False
        import urllib.request
        try:
            with urllib.request.urlopen(self.host.rstrip("/") + "/api/version", timeout=2):
                return True
        except Exception:                               # noqa: BLE001
            return False

    # --- sessions ------------------------------------------------------------
    def new_session(self, filename=None, data=None, dataset=None):
        sid = uuid.uuid4().hex[:12]
        s = Session(sid, os.path.join(self.workdir, sid))
        os.makedirs(s.dir, exist_ok=True)
        if dataset:
            src = mf.dataset_path(dataset)
            if not os.path.exists(src):
                raise ValueError("no such benchmark dataset on this machine: %s" % dataset)
            raw = src
            label = dataset
        else:
            safe = re.sub(r"[^A-Za-z0-9._-]", "_", filename or "upload.txt")[:80]
            raw = os.path.join(s.dir, "raw_" + safe)
            with open(raw, "wb") as fh:
                fh.write(data)
            label = filename
        info = ingest.to_spmf(raw, os.path.join(s.dir, "data.txt"))
        s.path, s.info = info["path"], info
        dtype = ask.sniff_format(s.path)
        s.profile = ask.profile(s.path, dtype)
        with open(s.path, encoding="utf-8", errors="ignore") as fh:
            s.sample = "".join([next(fh, "") for _ in range(3)]).strip()
        thr, why = ask.suggest_threshold(s.profile)
        s.threshold, s.threshold_why = thr, why
        self.sessions[sid] = s
        return s, {"session": sid, "name": label, "how": info["how"],
                   "profile": s.profile, "threshold": thr, "threshold_why": why,
                   "top_items": self._top_items(s)}

    def _top_items(self, s, k=8):
        names = s.info.get("item_names")
        if not names:
            return None
        freq = Counter()
        with open(s.path, encoding="utf-8") as fh:
            for line in fh:
                freq.update(int(t) for t in line.split())
        n = s.profile["n_tx"]
        return [(names[i], round(100.0 * c / n, 1)) for i, c in freq.most_common(k)]

    # --- a turn --------------------------------------------------------------
    def message(self, sid, text, choice=None, lang=None):
        s = self.sessions.get(sid)
        if s is None:
            raise ValueError("unknown session; upload the data again")
        with s.lock:
            # The page's language switch decides; without one, the message
            # does, and an option click (no text) keeps the last language.
            if lang in ("tr", "en"):
                s.lang = lang
            elif text:
                s.lang = "tr" if _turkish(text) else "en"
            s.history.append(("user", text or ("(chose option %s)" % choice)))
            reply = self._turn(s, text or "", choice)
            s.history.append(("assistant", reply.get("type")))
            return reply

    def _turn(self, s, text, choice):
        dtype = s.profile["data_type"]
        notes = []
        llm = self.llm_up()

        if choice is not None and s.pending == "family":
            fam = OPTIONS[dtype][int(choice)][0]
            s.task = {"family": fam, "data_type": dtype, "objective": "balanced"}
            s.pending = None
        elif s.pending == "utility_threshold":
            m = re.search(r"\d+(?:[.,]\d+)?", text)
            if not m:
                return {"type": "question", "text": self._say(s,
                        "Hangi en düşük fayda (kâr) değerinin üstündeki kombinasyonlar ilgini çekiyor? Bir sayı yaz.",
                        "Above what minimum utility (profit) should a combination count? Please give a number.")}
            s.threshold = float(m.group(0).replace(",", "."))
            s.threshold_why = "given by you"
            s.pending = None
        elif s.task is None:
            if llm:
                fields, source, note = ask.understand_consistent(
                    text, s.profile, s.sample, self.host, self.model, k=self.samples)
                if source == "unavailable":
                    llm = False
            if not llm:
                got = nl.RuleExtractor().extract(text)
                fields = {"family": got.get("family", ask.ANALOGUE.get(
                              ("minimal_generator", dtype), "minimal_generator")),
                          "data_type": dtype}
                if ask.reconcile(fields["family"], dtype) is None:
                    fields = None
                if fields is not None:
                    kw = keyword_fields(text)
                    fields.update({k: v for k, v in kw.items() if k != "threshold"})
                    notes += self._apply_threshold(s, kw.get("threshold"), fields["family"])
                source, note = ("rules", "language model offline; keyword rules used")
            if fields is None:
                s.pending = "family"
                opts = OPTIONS[dtype]
                if len(opts) == 1:                       # nothing to ask
                    s.task = {"family": opts[0][0], "data_type": dtype,
                              "objective": "balanced"}
                    s.pending = None
                else:
                    return {"type": "clarify", "note": note,
                            "text": self._say(s,
                                "Sorun ne bulmak istediğini söylemiyor, bu yüzden her cevap bir tahmin olurdu. Hangisi daha yakın?",
                                "Your question does not say what you want to find, so any answer would be a guess. Which is closest?"),
                            "options": [tr if s.lang == "tr" else en for _, en, tr in opts]}
            else:
                s.task = dict(fields)
                s.task.setdefault("objective", "balanced")
                notes.append(note)
                # The first-turn prompt is the frozen, test-scored one, and it
                # reads only the family and objective: "at most 50 MB" in the
                # first message was silently lost. The revise step picks up the
                # numbers, and only the numbers -- the family and objective
                # stay the self-consistent reading. No digit, nothing to find.
                if llm and re.search(r"\d", text):
                    notes += self._revise(s, text, numbers_only=True)
        else:
            if llm:
                notes += self._revise(s, text)
            else:
                kw = keyword_fields(text)
                if kw:
                    s.task.update({k: v for k, v in kw.items() if k != "threshold"})
                    notes += self._apply_threshold(s, kw.get("threshold"), s.task.get("family"))
                    notes.append("language model offline; keyword rules used")
                else:
                    notes.append("language model offline; the request was not changed")

        if dtype == "utility" and s.threshold is None:
            s.pending = "utility_threshold"
            return {"type": "question", "text": self._say(s,
                    "Faydalı (kâr) kombinasyonlar için bir alt sınır gerekiyor. Hangi değerin üstü ilgini çekiyor?",
                    "High-utility mining needs a minimum utility. Above what value should a combination count?")}
        if s.task.get("family") == "minimal_rare_itemset" and s.threshold_why != "given by you":
            s.threshold, s.threshold_why = 0.1, "a maximum support of 10%, the benchmark's default for rare patterns"
        return self._recommend(s, text, notes, llm)

    @staticmethod
    def _apply_threshold(s, thr, family):
        """Set a threshold read from the text, if it is in range."""
        if thr is None:
            return []
        util = family == "high_utility_generator"
        if (util and thr > 0) or (not util and 0 < thr <= 1):
            s.threshold, s.threshold_why = float(thr), "given by you"
            return []
        return ["ignored threshold %r: out of range" % thr]

    def _revise(self, s, text, numbers_only=False):
        """Apply what a follow-up message changes; drop anything invalid."""
        t = s.task
        prompt = REVISE_PROMPT.format(
            data_type=s.profile["data_type"], n_tx=s.profile["n_tx"],
            n_items=s.profile["n_items"], family=t.get("family"),
            objective=t.get("objective"), threshold=s.threshold,
            max_memory_mb=t.get("max_memory_mb"), max_runtime_s=t.get("max_runtime_s"),
            message=text)
        try:
            got = json.loads(ask.ask_model(self.host, self.model, prompt))
        except Exception as exc:                        # noqa: BLE001
            return ["could not read the change (%s); request unchanged" % type(exc).__name__]
        notes = []
        if numbers_only:
            got["family"] = got["objective"] = None
        fam = got.get("family")
        if fam:
            rec = ask.reconcile(fam, s.profile["data_type"]) if fam in spec.FAMILIES else None
            if rec:
                t["family"] = rec
            else:
                notes.append("ignored family %r: not one this data can serve" % fam)
        obj = got.get("objective")
        if obj in spec.OBJECTIVES:
            t["objective"] = obj
        thr = got.get("threshold")
        if isinstance(thr, (int, float)):
            util = t.get("family") == "high_utility_generator"
            if (util and thr > 0) or (not util and 0 < thr <= 1):
                s.threshold, s.threshold_why = float(thr), "given by you"
            else:
                notes.append("ignored threshold %r: out of range" % thr)
        for k in ("max_memory_mb", "max_runtime_s"):
            v = got.get(k)
            if isinstance(v, (int, float)) and v > 0:
                t[k] = float(v)
        return notes

    def _recommend(self, s, text, notes, llm):
        kw = {k: v for k, v in s.task.items() if k in spec.MiningTask.__dataclass_fields__}
        kw["dataset_path"] = s.path
        kw["threshold"] = s.threshold
        task = spec.MiningTask(**kw)
        # A memory request on a transactional file is probed: the four
        # native miners run briefly on the user's own data (see
        # recommender/probe.py and Recommender.should_probe for why memory
        # and not runtime). The probe's result is kept per threshold.
        pr = None
        if self.engine().should_probe(task):
            from . import probe as _probe
            key = round(float(s.threshold), 9)
            pr = s.probes.get(key)
            if pr is None:
                pr = _probe.probe(s.path, float(s.threshold))
                s.probes[key] = pr
            notes.append("native miners %s on your file in %.1f s"
                         % ("measured" if pr.mode == "direct" else "probed on samples",
                            pr.wall_s))
            if _probe.none_finished(pr):
                notes.append(_probe.NONE_FINISHED)
        recs, rejected, _feats = self.engine().recommend(task, probe=pr)
        rows = [{"algorithm": r.algorithm, "display": r.display, "tier": r.tier,
                 "runtime_s": r.runtime_s, "memory_mb": r.memory_mb,
                 "p_complete": r.p_complete, "installed": r.installed,
                 "match": r.match, "warnings": r.warnings,
                 "source": r.prediction_source,
                 "memory_interval": r.memory_interval, "runtime_interval": r.runtime_interval,
                 "memory_level": r.memory_interval_level, "runtime_level": r.runtime_interval_level,
                 "within_budget": r.within_budget, "budget_notes": r.budget_notes,
                 "extrapolated": r.extrapolated} for r in recs]
        refused = [{"algorithm": v.algorithm, "display": v.display,
                    "reason": (v.reasons[0] if v.reasons else "")}
                   for v in rejected if not v.reasons or "reads" not in v.reasons[0]]
        top = recs[0] if recs else None
        runnable = next((r for r in recs if r.installed), None)
        out = {"type": "recommendation", "task": task.describe(),
               "family": s.task["family"], "threshold": s.threshold,
               "threshold_why": s.threshold_why, "rows": rows, "refused": refused,
               "top": top.display if top else None,
               "runnable": runnable.display if runnable else None,
               "notes": [n for n in notes if n]}
        out["explanation"], out["explanation_source"] = self._explain(
            s, text, task, recs, refused, llm)
        return out

    # --- explanation, checked ------------------------------------------------
    def _explain(self, s, text, task, recs, refused, llm):
        if not recs:
            return self._say(s,
                "Bu isteği karşılayan doğrulanmış bir implementasyon yok. Reddedilenler ve nedenleri aşağıda.",
                "No verified implementation satisfies this request. The refusals and their reasons are below."), "template"
        tier1 = [r for r in recs if r.tier == recs[0].tier]
        allowed = {r.algorithm for r in recs} | {r["algorithm"] for r in refused}
        if llm:
            top = recs[0]
            runnable = next((r for r in recs if r.installed), None)
            pick = top if top.installed or runnable is None else runnable
            if top.installed:
                run_line = ""
            elif runnable:
                run_line = ("%s is NOT installed on this machine. Best that CAN run "
                            "here: %s -- %s" % (top.display, runnable.display, _cost(runnable)))
            else:
                run_line = "%s is NOT installed on this machine, and nothing eligible is." % top.display
            budget = "".join(", at most %s %s" % (_num(task.__dict__[k]), u)
                             for k, u in (("max_memory_mb", "MB"), ("max_runtime_s", "s"))
                             if task.__dict__.get(k))
            prompt = EXPLAIN_PROMPT.format(
                language="Turkish" if s.lang == "tr" else "English",
                message=text or "(chose an option)", n_tx=s.profile["n_tx"],
                n_items=s.profile["n_items"], data_type=s.profile["data_type"],
                how=s.info.get("how", ""), goal=task.family, objective=task.objective,
                budget=budget, threshold=s.threshold, threshold_why=s.threshold_why,
                top=top.display, top_cost=_cost(top), caveats=_caveats(pick),
                ties=", ".join(r.display for r in tier1[1:]) or "none",
                runnable=run_line,
                excluded="; ".join("%s: %s" % (r["display"], r["reason"][:120])
                                   for r in refused[:4]) or "none")
            try:
                txt = json.loads(ask.ask_model(self.host, self.model, prompt)).get("text", "")
            except Exception:                           # noqa: BLE001
                txt = ""
            must = [("budget", "bütçe")] if not pick.within_budget else []
            if txt and _checked(txt, prompt, allowed, must):
                return txt, "llm"
        top = recs[0]
        ties = [r.display for r in tier1[1:]]
        tr = s.lang == "tr"
        parts = [("Önerim %s." if tr else "Recommended: %s.") % top.display]
        if ties:
            parts.append(("Veri, bunu %s ile ayırt edemiyor; aralarında istediğini seçebilirsin."
                          if tr else "The data cannot separate it from %s; either is fine.")
                         % ", ".join(ties))
        if refused:
            parts.append(("%d implementasyon, istediğin işi doğru yapmadığı ölçüldüğü için elendi."
                          if tr else "%d implementations were excluded because they were measured "
                          "not to compute what you asked for.") % len(refused))
        if not top.installed:
            parts.append(("%s bu makinede kurulu değil." if tr
                          else "%s is not installed on this machine.") % top.display)
        pick = top if top.installed else next((r for r in recs if r.installed), top)
        if not pick.within_budget and pick.extrapolated:
            parts.append(("Bütçene sığıp sığmayacağı bu veri için tahmin edilemiyor."
                          if tr else "Whether it fits your budget cannot be predicted for this data."))
        elif not pick.within_budget:
            parts.append(("Uygun hiçbir implementasyonun belirttiğin bütçeye sığması beklenmiyor."
                          if tr else "No eligible implementation is predicted to fit your budget."))
        if pick.extrapolated:
            parts.append(("Verin, maliyetlerin ölçüldüğü veri aralığının dışında; sıralama bir tahmin, "
                          "süre ve bellek değerleri güvenilir değil."
                          if tr else "Your data is outside the range the costs were measured "
                          "on; the ranking is an extrapolation and the predicted time and "
                          "memory are not reliable."))
        return " ".join(parts), "template"

    @staticmethod
    def _say(s, tr, en):
        return tr if s.lang == "tr" else en


# ----------------------------------------------------------------------
def make_handler(app):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):             # keep the console quiet
            pass

        def _json(self, code, obj):
            body = json.dumps(obj, default=str).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path in ("/", "/index.html"):
                with open(os.path.join(WEB, "index.html"), "rb") as fh:
                    body = fh.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            elif self.path == "/api/status":
                self._json(200, {"llm": app.llm_up(), "model": app.model,
                                 "engine_ready": app._rec_ready.is_set(),
                                 "engine_error": app._rec_err,
                                 "datasets": sorted(d for d in mf.DATASET_TYPES
                                                    if os.path.exists(mf.dataset_path(d)))})
            else:
                self._json(404, {"error": "not found"})

        def do_POST(self):
            try:
                n = int(self.headers.get("Content-Length", "0"))
                if n > MAX_UPLOAD:
                    return self._json(413, {"error": "file larger than %d MB" % (MAX_UPLOAD >> 20)})
                body = self.rfile.read(n)
                if self.path == "/api/upload":
                    name = self.headers.get("X-Filename", "upload.txt")
                    from urllib.parse import unquote
                    _s, info = app.new_session(filename=unquote(name), data=body)
                    return self._json(200, info)
                req = json.loads(body or b"{}")
                if self.path == "/api/dataset":
                    _s, info = app.new_session(dataset=req.get("dataset"))
                    return self._json(200, info)
                if self.path == "/api/message":
                    return self._json(200, app.message(req.get("session"), req.get("text"),
                                                       req.get("choice"), req.get("lang")))
                return self._json(404, {"error": "not found"})
            except ingest.IngestError as exc:
                return self._json(400, {"error": "could not read the file: %s" % exc})
            except Exception as exc:                    # noqa: BLE001
                return self._json(400, {"error": "%s: %s" % (type(exc).__name__, exc)})
    return Handler


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--model", default=ask.DEFAULT_MODEL)
    ap.add_argument("--host", default=ask.DEFAULT_HOST, help="Ollama address")
    ap.add_argument("--samples", type=int, default=ask.SC_SAMPLES)
    ap.add_argument("--no-llm", action="store_true")
    args = ap.parse_args(argv)
    app = App(args.model, args.host, args.samples, use_llm=not args.no_llm)
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(app))
    print("recommender chat on http://127.0.0.1:%d   (model %s, Ollama %s)"
          % (args.port, args.model, "up" if app.llm_up() else "DOWN -- rules only"))
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        shutil.rmtree(app.workdir, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
