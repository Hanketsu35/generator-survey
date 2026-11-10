"""Title-and-snippet screening of the Google Scholar records (Publish or Perish).

    python tools/scholar_screen.py

Reads results/litsearch/db/raw/scholar_*.csv (Publish or Perish exports,
200 results per query; kept locally, not redistributed), drops records whose normalised title or DOI is among the
works already screened (merged.csv, merged_supp.csv), and writes
results/litsearch/db/scholar_screening.csv with one code per remaining work.
Codes are those of SCREENING_DB.md: X1 outside pattern mining, X2 another
pattern class, X3 no mining algorithm, X4 another data model or language,
X5 not refereed, X6 heuristic; FT full text needed; K a version of an
algorithm already decided. Decisions written by hand are in DECISIONS; the
rest are coded by the title rule below and every one was read.
"""
import glob
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "results" / "litsearch" / "db"


def norm(t):
    return re.sub(r"[^a-z0-9]", "", str(t).lower())


#: normalised-title prefix -> (code, note)
DECISIONS = {
    "algorithmminingminimalgeneratorsofclosedrareitemsets": ("FT", "minimal generators of closed rare itemsets, item weights (Huan)"),
    "khaiphatpsinhtithiucatphimong": ("FT", "same work in Vietnamese (minimal generators of closed rare itemsets)"),
    "highperformancealgorithminmininggeneratorsofclosedfrequent": ("FT", "generators of closed frequent itemsets (Huan 2020)"),
    "anefficientlatticebasedapproachforgeneratormining": ("FT", "generator mining, lattice-based (may take a lattice as input)"),
    "baccle": ("FT", "Vo & Nguyen 2017, minimal generators of frequent closed itemsets (chapter)"),
    "bacle": ("FT", "Vo & Nguyen 2017, minimal generators of frequent closed itemsets (chapter)"),
    "amethodforcomputingfrequentkeyandcloseditemsetsinonephase": ("FT", "frequent key and closed itemsets (Phan-Luong)"),
    "findingminimalinfrequentitemsetsonacluster": ("FT", "parallel minimal infrequent itemsets (Le 2007)"),
    "aparallelalgorithmforcomputingborders": ("FT", "borders of the frequent itemsets; negative border = minimal infrequent"),
    "towardsimprovingsolutiondominancewithincomparabilityconditions": ("FT", "constraint-programming generator itemset mining (preprint of the ECAI paper)"),
    "exploitingincomparabilityinsolutiondominance": ("FT", "constraint-programming mining of generator and minimal rare itemsets (ECAI 2020)"),
    "miningassociationrulesforclassificationusingfrequentgeneratoritemsetsinarules": ("FT", "frequent generator itemsets in the arules package (GrAFCI+ implementation?)"),
    "interactivesearchbyusingminimalgenerators": ("FT", "minimal generators in FCA from implications (likely EC2)"),
    "exactandapproximateminimal": ("FT", "Soulet & Rioult 2016, extended DefMe (listed as unreachable)"),
    "efficientminingofnewconciserepresentationsofrarecorrelatedpatterns": ("FT", "rare correlated patterns; MinRP (minimal rare patterns) defined"),
    "afastalgorithmforminingrareitemsets": ("FT", "Rarity; may return all rare itemsets (IC2)"),
    "towardsrareitemsetmining": ("K", "AprioriRare and MRG-Exp, ICTAI 2007 (counted)"),
    "miningfrequentpatternswithcountinginference": ("K", "Pascal (counted)"),
    "anefficienthybridalgorithmforminingfrequentclosuresandgenerators": ("K", "Touch, CLA 2008 (counted with Talky-G)"),
    "efficientverticalminingoffrequentcloseditemsetsandgenerators": ("K", "Talky-G/Touch (counted)"),
    "efficientverticalminingoffrequentclosuresandgenerators": ("K", "Talky-G/Touch (counted)"),
    "fastdiscoveryofuniqueandminimaldatapatterns": ("K", "Kyiv (recorded: not refereed)"),
    "efficientverticalminingofminimalrareitemsets": ("K", "Walky-G (counted)"),
    "prinzextraction": ("K", "Prince (counted)"),
    "princeextractionoptimisee": ("K", "Prince (counted)"),
    "nouvellesrepresentationsconcisesexactesdesmotifsrares": ("X5", "arXiv thesis chapter"),
    "keycorrelationminingbysimultaneousmonotone": ("X2", "key correlated patterns: minimality on the bond measure (EC4)"),
    "miningconciserepresentationsoffrequentpatternsthroughconjunctive": ("X3", "summary of a thesis, no new algorithm"),
    "adaptiveandfastpredictionsbyminimalitemsetscreation": ("X3", "applies MG-CHARM"),
    "privacypreservationoncategoricaldatasetsthroughminimalinfrequent": ("X5", "student thesis; applies existing MII mining"),
    "efficientalgorithmstomineconciserepresentationsoffrequenthighutilityoccupancy": ("FT", "Duong et al. 2024, concise representations of HUO patterns (same group as Gen-FHUOIM, EC4 there)"),
}

MATH = re.compile(r"sum-?free|progression-?free|product-?free|corner-?free|bifix|lattice-?free|"
                  r"line-?free|solution-?free|incidence-?free|zero-?sum|sidon|context-?free|"
                  r"free sets of|alliance|abelian|integers|groups|ramsey|semimodule|polynomial|"
                  r"perfect hashing|encryption|key sets of|fermions|epidemic|delta free-form|"
                  r"free choice|reverse mathematics|hitting triangle|square-difference|"
                  r"cyclotomy|matroid|automorphisms|barriers|set mappings|oriented|subshifts|"
                  r"pseudo-?random|random sequence|binary sequence|m-sequence|shift register|"
                  r"cellular automata|cipher|keystream|built-in self-test|de bruijn|quasirandom",
                  re.I)
MINING = re.compile(r"itemset|pattern|association|rule|mining|closed|concept|"
                    r"border|transversal|condensed|concise|frequent|rare|infrequent|apriori|eclat",
                    re.I)


def code(title):
    t = norm(title)
    for k, v in DECISIONS.items():
        if t.startswith(k):
            return v
    if MATH.search(str(title)) or not MINING.search(str(title)):
        return ("X1", "title rule: outside pattern mining")
    return ("X2", "title rule: pattern mining, another pattern class or task")


def main():
    files = sorted(glob.glob(str(DB / "raw" / "scholar_*_2026-11-*.csv")))
    d = pd.concat([pd.read_csv(f).assign(file=Path(f).name) for f in files], ignore_index=True)
    seen_t, seen_d = set(), set()
    for f in ("merged.csv", "merged_supp.csv"):
        m = pd.read_csv(DB / f, dtype=str)
        seen_t |= set(m.title.map(norm))
        seen_d |= set(m.doi.dropna().str.lower())
    d["nt"] = d.Title.map(norm)
    u = d.drop_duplicates("nt").copy()
    known = u.nt.isin(seen_t) | (u.DOI.fillna("").str.lower().isin(seen_d) & u.DOI.notna())
    new = u[~known].copy()
    new[["code", "note"]] = new.Title.map(code).apply(pd.Series)
    new[["code", "note", "Year", "Title", "Authors", "Source", "DOI", "ArticleURL", "file"]].to_csv(
        DB / "scholar_screening.csv", index=False)
    print("records %d, unique %d, already screened %d, new %d" % (len(d), len(u), known.sum(), len(new)))
    print(new.code.value_counts().to_string())


if __name__ == "__main__":
    main()
