#!/usr/bin/env python3
"""
Analisi inferenziali e di stabilità riportate nelle Tabelle A2-A7 dell'articolo.

Legge i 15 file di annotations/ e scrive i risultati in results/revisione/.

    python scripts/analisi_revisione.py            # 2.000 ricampionamenti bootstrap
    python scripts/analisi_revisione.py --boot 200 # esecuzione rapida di prova

Dipendenze: pandas, numpy, scipy, scikit-learn, statsmodels
"""
import argparse
import json
import re
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats
from sklearn.metrics import cohen_kappa_score as kappa
from statsmodels.discrete.conditional_models import ConditionalLogit

warnings.filterwarnings("ignore")

BASE = Path(__file__).resolve().parent.parent
ANN, OUT = BASE / "annotations", BASE / "results" / "revisione"
MODELS = {"claude_sonnet46": "Claude Sonnet 4.6", "gpt55": "GPT-5.5",
          "gemini35flash": "Gemini 3.5 Flash", "qwen3_35b": "Qwen3-35B-A3B",
          "gpt_oss_120b": "GPT-OSS-120B"}
PERIODS = ([1820, 1870, 1900, 1935], ["1830-1870", "1871-1900", "1901-1930"])
PREVALENCE = 865 / 29293
SEED = 42


def load():
    rows = []
    for key, name in MODELS.items():
        for p in "ABC":
            df = pd.read_csv(ANN / f"{key}_prompt{p}_annotated.csv")
            pred = df[f"DIL_{key}_prompt{p}"].astype(str).str.lower()
            conf = df[f"confidence_{key}_prompt{p}"].astype(str).str.lower()
            year = pd.to_numeric(df.doc_id.str.extract(r"[-_](\d{4})\.txt$")[0])
            rows.append(pd.DataFrame({
                "block_id": [f"b{i:04d}" for i in range(len(df))],
                "doc_id": df.doc_id, "year": year, "model": name, "prompt": p,
                "gold": (df.DIL.str.lower() == "yes").astype(int),
                "pred": pred.map({"yes": 1, "no": 0}), "high": conf == "high"}))
    d = pd.concat(rows, ignore_index=True).dropna(subset=["pred"])  # 6 risposte non valide
    d["pred"] = d.pred.astype(int)
    d["correct"] = (d.pred == d.gold).astype(int)
    d["period"] = pd.cut(d.year, PERIODS[0], labels=PERIODS[1]).astype(str)
    return d


def doc_bootstrap(d, n_boot):
    """Kappa per condizione e contrasti appaiati, ricampionando i romanzi."""
    wide = d.pivot_table(index="block_id", columns=["model", "prompt"], values="pred")
    meta = d.drop_duplicates("block_id").set_index("block_id").loc[wide.index]
    gold, doc = meta.gold.values, meta.doc_id.values
    idx = {u: np.where(doc == u)[0] for u in np.unique(doc)}
    def k(col, ii):
        v = wide[col].values[ii]; ok = ~np.isnan(v)
        return kappa(gold[ii][ok], v[ok].astype(int))
    contrasts = [((a, "C"), (b, "C")) for a, b in [
        ("Claude Sonnet 4.6", "GPT-5.5"), ("Claude Sonnet 4.6", "Gemini 3.5 Flash"),
        ("GPT-5.5", "Gemini 3.5 Flash"), ("Claude Sonnet 4.6", "Qwen3-35B-A3B"),
        ("GPT-5.5", "Qwen3-35B-A3B"), ("Gemini 3.5 Flash", "Qwen3-35B-A3B")]]
    for m in MODELS.values():
        contrasts += [((m, "C"), (m, "A")), ((m, "B"), (m, "A"))]
    rng = np.random.default_rng(SEED)
    bk = {c: [] for c in wide.columns}; bd = {c: [] for c in contrasts}
    for _ in range(n_boot):
        ii = np.concatenate([idx[u] for u in rng.choice(list(idx), len(idx))])
        ks = {c: k(c, ii) for c in wide.columns}
        for c in wide.columns: bk[c].append(ks[c])
        for c in contrasts: bd[c].append(ks[c[0]] - ks[c[1]])
    allii = np.arange(len(gold))
    a2 = pd.DataFrame([[c[0], c[1], k(c, allii), *np.percentile(bk[c], [2.5, 97.5])]
                       for c in wide.columns], columns=["modello", "prompt", "kappa", "ic_inf", "ic_sup"])
    rows = []
    for c in contrasts:
        a = np.array(bd[c])
        rows.append([f"{c[0][0]} {c[0][1]} - {c[1][0]} {c[1][1]}", k(c[0], allii) - k(c[1], allii),
                     *np.percentile(a, [2.5, 97.5]), min(1, 2 * min((a <= 0).mean(), (a >= 0).mean()))])
    a3 = pd.DataFrame(rows, columns=["contrasto", "delta_kappa", "ic_inf", "ic_sup", "p"])
    order = np.argsort(a3.p.values); adj = np.empty(len(a3)); run = 0
    for j, i in enumerate(order):
        run = max(run, min(1, (len(a3) - j) * a3.p.values[i])); adj[i] = run
    a3["p_holm"] = adj
    return a2, a3


def dummies(s, cols):
    return pd.get_dummies(s[cols].astype(str), drop_first=True).astype(float)


def lr_interaction(s, a, b):
    A, B = dummies(s, [a]), dummies(s, [b])
    X = pd.concat([A, B], axis=1)
    I = pd.DataFrame({f"{x}:{y}": A[x] * B[y] for x in A for y in B})
    m0 = ConditionalLogit(s.correct, X, groups=s.block_id).fit(disp=0)
    m1 = ConditionalLogit(s.correct, pd.concat([X, I], axis=1), groups=s.block_id).fit(
        disp=0, method="bfgs", maxiter=2000)
    lr = 2 * (m1.llf - m0.llf)
    return lr, I.shape[1], stats.chi2.sf(lr, I.shape[1])


def interactions(d):
    rows = []
    for lab, s in [("tutti", d), ("positivi", d[d.gold == 1]), ("negativi", d[d.gold == 0])]:
        rows.append(["modello x prompt", lab, *lr_interaction(s.reset_index(drop=True), "model", "prompt")])
    c = d[d.prompt == "C"]
    for lab, g in [("positivi", 1), ("negativi", 0)]:
        s = c[c.gold == g].reset_index(drop=True)
        M = dummies(s, ["model"]); V = dummies(s, ["period"])
        I = pd.DataFrame({f"{x}:{y}": M[x] * V[y] for x in M for y in V})
        m0 = ConditionalLogit(s.correct, M, groups=s.block_id).fit(disp=0)
        m1 = ConditionalLogit(s.correct, pd.concat([M, I], axis=1), groups=s.block_id).fit(
            disp=0, method="bfgs", maxiter=2000)
        lr = 2 * (m1.llf - m0.llf)
        rows.append(["modello x periodo (prompt C)", lab, lr, I.shape[1], stats.chi2.sf(lr, I.shape[1])])
    a4 = pd.DataFrame(rows, columns=["test", "osservazioni", "chi2", "gl", "p"])
    rows = []
    for m in MODELS.values():
        s = d[d.model == m]
        f = ConditionalLogit(s.correct, pd.get_dummies(s.prompt, drop_first=True).astype(float),
                             groups=s.block_id).fit(disp=0)
        ci = np.exp(f.conf_int())
        v = s.groupby("block_id").correct.agg(["min", "max"])
        for p in ["B", "C"]:
            rows.append([m, f"{p} vs A", np.exp(f.params[p]), ci.loc[p, 0], ci.loc[p, 1],
                         f.pvalues[p], int((v["min"] != v["max"]).sum())])
    a5 = pd.DataFrame(rows, columns=["modello", "confronto", "odds_ratio", "ic_inf", "ic_sup", "p", "blocchi_informativi"])
    return a4, a5


def stability(d):
    c = d[d.prompt == "C"].copy()
    rules = {m: (c.model == m, c.pred == 1) for m in MODELS.values()}
    rows = []
    def add(name, flag, sub):
        x = sub.assign(f=flag.astype(int))
        r = {"regola": name, "recall": x[x.gold == 1].f.mean()}
        for p in PERIODS[1]:
            r[f"sp_{p}"] = 1 - x[(x.gold == 0) & (x.period == p)].f.mean()
            r[f"rec_{p}"] = x[(x.gold == 1) & (x.period == p)].f.mean()
        r["delta_sp"] = r[f"sp_{PERIODS[1][-1]}"] - r[f"sp_{PERIODS[1][0]}"]
        r["effetto_equivalente_punti"] = -r["delta_sp"] * (1 - 0.03) / r["recall"] * 100
        rows.append(r)
    for m in MODELS.values():
        s = c[c.model == m]; add(m, s.pred == 1, s)
    for m in ["Claude Sonnet 4.6", "GPT-5.5", "Gemini 3.5 Flash", "GPT-OSS-120B"]:
        s = c[c.model == m]; add(f"{m}, solo alta confidenza", (s.pred == 1) & s.high, s)
    w = c.pivot_table(index="block_id", columns="model", values="pred")
    meta = c.drop_duplicates("block_id").set_index("block_id").loc[w.index]
    com = ["Claude Sonnet 4.6", "GPT-5.5", "Gemini 3.5 Flash"]
    for name, flag in [("maggioranza tre commerciali", w[com].sum(1) >= 2),
                       ("unanimità tre commerciali", w[com].sum(1) == 3),
                       ("unanimità cinque modelli", w.sum(1) == 5)]:
        add(name, flag.values, meta.reset_index())
    a6 = pd.DataFrame(rows)
    # controlli di robustezza sulla specificità e sul recall
    rob = {}
    for lab, g in [("specificita", 0), ("recall", 1)]:
        s = d[d.gold == g]
        f = smf.logit("correct ~ C(model)*C(prompt) + year", data=s).fit(
            disp=0, cov_type="cluster", cov_kwds={"groups": pd.factorize(s.doc_id)[0]})
        rob[f"trend_anno_{lab}"] = {"beta": float(f.params["year"]), "p": float(f.pvalues["year"])}
    per = c.groupby("doc_id").apply(lambda g: pd.Series({
        "year": g.year.iloc[0], "nneg": (g.gold == 0).sum() / 5,
        "sp": g[g.gold == 0].correct.mean()}), include_groups=False)
    pn = per[per.nneg >= 5]
    r = stats.spearmanr(pn.year, pn.sp)
    rob["spearman_anno_specificita"] = {"rho": float(r[0]), "p": float(r[1]), "romanzi": int(len(pn))}
    ds = []
    for u in c.doc_id.unique():
        s = c[c.doc_id != u]
        sp = s[s.gold == 0].groupby("period").correct.mean()
        ds.append(sp[PERIODS[1][-1]] - sp[PERIODS[1][0]])
    rob["leave_one_out_delta_sp"] = [float(min(ds)), float(max(ds))]
    return a6, rob


def ppv(d):
    c = d[d.prompt == "C"]; rows = []
    for m in MODELS.values():
        s = c[c.model == m]
        se, sp = s[s.gold == 1].correct.mean(), s[s.gold == 0].correct.mean()
        rows.append([m, se, sp, se * PREVALENCE / (se * PREVALENCE + (1 - sp) * (1 - PREVALENCE)),
                     round(865 * se), round(28428 * (1 - sp))])
    return pd.DataFrame(rows, columns=["modello", "recall", "specificita", "ppv_prevalenza_reale",
                                       "blocchi_dil_recuperati_su_865", "segnalazioni_non_confermate"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--boot", type=int, default=2000)
    n = ap.parse_args().boot
    OUT.mkdir(parents=True, exist_ok=True)
    d = load()
    print(f"Esiti validi: {len(d)}")
    a2, a3 = doc_bootstrap(d, n)
    a4, a5 = interactions(d)
    a6, rob = stability(d)
    a7 = ppv(d)
    for name, t in [("A2_kappa_intervalli", a2), ("A3_contrasti", a3), ("A4_interazioni", a4),
                    ("A5_odds_ratio_prompt", a5), ("A6_stabilita_per_periodo", a6), ("A7_ppv", a7)]:
        t.round(4).to_csv(OUT / f"{name}.csv", index=False)
        print(f"\n=== {name} ===\n{t.round(3).to_string(index=False)}")
    json.dump(rob, open(OUT / "A6_controlli_robustezza.json", "w"), indent=2)
    print("\n=== controlli di robustezza ===\n", json.dumps(rob, indent=2))
