"""Simulated A/B test: flexible free-cancellation rate vs standard rate.

SIMULATED data (seed 42), built to be analysed, not to be sold as real:
20,000 booking-flow users, 50/50. Primary metric = booking conversion.
Guardrails = cancellation rate among bookers and revenue per user.
The treatment is designed with a real trade-off: conversion rises but
free cancellation also raises cancellations, so the readout is a
decision problem, not a victory lap.
"""
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.proportion import proportions_ztest

RNG = np.random.default_rng(42)
N, P_C, P_T = 20_000, 0.120, 0.131
CXL_C, CXL_T, ADR, NIGHTS = 0.37, 0.41, 105.0, 3.2


def simulate() -> pd.DataFrame:
    users = pd.DataFrame({
        "user_id": np.arange(1, N + 1),
        "variant": RNG.choice(["control", "treatment"], size=N, p=[0.5, 0.5]),
    })
    users["booked"] = [RNG.random() < (P_T if v == "treatment" else P_C)
                        for v in users["variant"]]
    users["cancelled"] = [
        bool(b) and (RNG.random() < (CXL_T if v == "treatment" else CXL_C))
        for b, v in zip(users["booked"], users["variant"])]
    users["revenue_per_user_eur"] = np.where(
        users["booked"] & ~users["cancelled"], ADR * NIGHTS, 0.0)
    return users


def analyse(users: pd.DataFrame) -> pd.DataFrame:
    g = users.groupby("variant")
    conv = g["booked"].mean()
    counts = g["booked"].sum().reindex(["control", "treatment"]).to_numpy()
    ns = g.size().reindex(["control", "treatment"]).to_numpy()
    _, p_conv = proportions_ztest(counts, ns)
    srm_chi2, srm_p = stats.chisquare(ns)
    bookers = users[users["booked"]]
    cxl = bookers.groupby("variant")["cancelled"].mean()
    c_counts = bookers.groupby("variant")["cancelled"].sum().reindex(
        ["control", "treatment"]).to_numpy()
    c_ns = bookers.groupby("variant").size().reindex(["control", "treatment"]).to_numpy()
    _, p_cxl = proportions_ztest(c_counts, c_ns)
    rpu_c = users[users["variant"] == "control"]["revenue_per_user_eur"]
    rpu_t = users[users["variant"] == "treatment"]["revenue_per_user_eur"]
    _, p_rpu = stats.ttest_ind(rpu_t, rpu_c, equal_var=False)
    lift = conv["treatment"] / conv["control"] - 1
    if p_conv < 0.05 and p_cxl < 0.05 and cxl["treatment"] > cxl["control"]:
        decision = ("DO NOT SHIP as-is: conversion lift is real but the "
                    "cancellation guardrail is breached. Ship only with a "
                    "deposit for lead times over 90 days, then re-test.")
    elif p_conv < 0.05 and p_cxl >= 0.05:
        decision = ("SHIP with monitoring: conversion lift is significant "
                    "and the cancellation guardrail is NOT significantly "
                    "breached, but its point estimate moved the wrong way "
                    "and the guardrail test is underpowered at this sample "
                    "of bookers. Monitor cancellation weekly for 4 weeks "
                    "with a pre-set stop rule.")
    else:
        decision = "See memo: decision follows the pre-registered rules."
    rows = [
        {"metric": "users_control", "value": int(ns[0])},
        {"metric": "users_treatment", "value": int(ns[1])},
        {"metric": "srm_p_value", "value": round(float(srm_p), 4)},
        {"metric": "conversion_control", "value": round(float(conv["control"]), 4)},
        {"metric": "conversion_treatment", "value": round(float(conv["treatment"]), 4)},
        {"metric": "conversion_lift_pct", "value": round(float(lift * 100), 2)},
        {"metric": "conversion_p_value", "value": round(float(p_conv), 4)},
        {"metric": "cancel_rate_bookers_control", "value": round(float(cxl["control"]), 4)},
        {"metric": "cancel_rate_bookers_treatment", "value": round(float(cxl["treatment"]), 4)},
        {"metric": "cancel_rate_p_value", "value": round(float(p_cxl), 4)},
        {"metric": "revenue_per_user_control_eur", "value": round(float(rpu_c.mean()), 2)},
        {"metric": "revenue_per_user_treatment_eur", "value": round(float(rpu_t.mean()), 2)},
        {"metric": "revenue_per_user_p_value", "value": round(float(p_rpu), 4)},
        {"metric": "decision", "value": decision},
    ]
    return pd.DataFrame(rows)
