import math
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# -----------------------------
# Config
# -----------------------------
st.set_page_config(page_title="Guardian Verifier", layout="wide")

# -----------------------------
# Data Load
# -----------------------------
@st.cache_data
def load_all():
    scn = pd.read_csv("data/guardian_scenarios.csv")
    eff = pd.read_csv("data/module_effects.csv")
    upg = pd.read_csv("data/upgrade_candidates.csv")
    price = pd.read_csv("data/market_prices.csv")
    presets = pd.read_csv("data/presets.csv")
    return scn, eff, upg, price, presets

df_scn, df_eff, df_upg, df_price, df_presets = load_all()
prices = {r["item_id"]: float(r["price_gold"]) for _, r in df_price.iterrows()}

# -----------------------------
# Helpers
# -----------------------------
def get_effect(df_eff_, module, level):
    row = df_eff_[(df_eff_["module"] == module) & (df_eff_["level"] == level)]
    if row.empty:
        raise ValueError(f"Missing effect: {module} level {level}")
    r = row.iloc[0]
    return float(r["dps_mult"]), float(r["ehp_mult"]), float(r["uptime_add"])

def compute_build_multipliers(df_eff_, levels):
    dps_mult = 1.0
    ehp_mult = 1.0
    uptime_add = 0.0
    for m, lv in levels.items():
        dm, em, ua = get_effect(df_eff_, m, lv)
        dps_mult *= dm
        ehp_mult *= em
        uptime_add += ua
    return dps_mult, ehp_mult, uptime_add

def gold_equiv(upg_row, prices_):
    gold = float(upg_row["gold_cost"])
    for col_id, col_qty in [("mat1_id", "mat1_qty"), ("mat2_id", "mat2_qty")]:
        item_id = str(upg_row[col_id])
        qty = float(upg_row[col_qty])
        if item_id and item_id in prices_:
            gold += qty * prices_[item_id]
    return gold

def apply_preset(ilv_gate: int):
    row = df_presets[df_presets["ilv_gate"] == ilv_gate].iloc[0]
    st.session_state.levels = {
        "enhance": int(row["enhance"]),
        "gems": int(row["gems"]),
        "engrave": int(row["engrave"]),
        "ark": int(row["ark"]),
        "elixir": int(row["elixir"]),
    }

def stage2_target(ilv: int, base_target: float, party_mode: bool, support_on: bool) -> float:
    """
    Stage2 목표(CR5) = base_target (솔로 기준)
    + 파티 경쟁 메타: iLv>=1730 AND support_on 일 때만 +10%p
    """
    t = float(base_target)
    if party_mode and support_on and ilv >= 1730:
        t += 0.10
    return float(np.clip(t, 0.0, 0.95))

def party_buffs(party_mode: bool, support_on: bool):
    """
    파티 딜/업타임 프리셋
    - support ON: +18% 딜, +0.06 업타임(끊김 감소)
    - support OFF: +10% 딜, +0.03 업타임
    """
    if not party_mode:
        return 0.0, 0.0, 1.0  # dps_buff, uptime_buff, fail_penalty_mult(=1.0 no reduction)

    if support_on:
        return 0.18, 0.06, 0.80  # 실수 페널티도 더 줄어든다고 가정
    else:
        return 0.10, 0.03, 0.90

# -----------------------------
# Simulation Core
# -----------------------------
def simulate_guardian(
    boss_hp: float,
    base_dps: float,
    base_ehp: float,
    base_uptime: float,
    levels: dict,
    df_eff_: pd.DataFrame,
    party_mode: bool,
    support_on: bool,
    skill_level: str,
    n: int = 8000,
    rng_seed: int = 42
):
    rng = np.random.default_rng(rng_seed)

    # Skill presets
    # - uptime variation reflects execution variance
    # - fail_base reflects chance of "big mistake" that costs time
    skill_uptime_std = {"low": 0.10, "mid": 0.07, "high": 0.05}[skill_level]
    fail_base = {"low": 0.18, "mid": 0.10, "high": 0.05}[skill_level]
    fail_time_loss_base = {"low": 45, "mid": 25, "high": 12}[skill_level]  # seconds

    dps_mult, ehp_mult, uptime_add = compute_build_multipliers(df_eff_, levels)

    dps_buff, uptime_buff, fail_penalty_mult = party_buffs(party_mode, support_on)

    expected_uptime = float(np.clip(base_uptime + uptime_add + uptime_buff, 0.30, 0.95))
    ehp_mean = base_ehp * ehp_mult

    # Deal/EHP -> internal scores (stable scaling)
    sustained_dps_mean = base_dps * dps_mult * (1.0 + dps_buff) * expected_uptime
    deal_score = 1000 * math.log1p(max(1.0, sustained_dps_mean))
    surv_score = 1000 * math.log1p(max(1.0, ehp_mean))
    epi = 0.7 * deal_score + 0.3 * surv_score

    clear_times = []
    for _ in range(n):
        uptime = rng.normal(expected_uptime, skill_uptime_std)
        uptime = float(np.clip(uptime, 0.30, 0.95))

        sustained_dps = base_dps * dps_mult * (1.0 + dps_buff) * uptime
        ttk = boss_hp / max(1.0, sustained_dps)

        # Fail probability decreases with survivability; party may reduce penalties
        ehp_factor = 1.0 / (1.0 + math.log1p(ehp_mean) / 10.0)  # higher ehp => smaller
        fail_prob = float(np.clip(fail_base * ehp_factor * fail_penalty_mult, 0.0, 0.35))

        fail_happens = (rng.random() < fail_prob)
        fail_loss = (fail_time_loss_base if fail_happens else 0.0)

        clear_times.append(ttk + fail_loss)

    times = np.array(clear_times)
    mean_t = float(np.mean(times))
    p90_t = float(np.percentile(times, 90))

    cr10 = float(np.mean(times <= 600.0))
    cr5 = float(np.mean(times <= 300.0))

    return {
        "epi": float(epi),
        "deal_score": float(deal_score),
        "surv_score": float(surv_score),
        "times": times,
        "mean_time": mean_t,
        "p90_time": p90_t,
        "cr10": float(cr10),
        "cr5": float(cr5),
        "expected_uptime": expected_uptime,
        "dps_buff": dps_buff,
        "uptime_buff": uptime_buff
    }

def recommend_upgrades(
    scenario_row: pd.Series,
    base_dps: float,
    base_ehp: float,
    base_uptime: float,
    levels: dict,
    party_mode: bool,
    support_on: bool,
    skill_level: str,
    target_cr5: float
):
    # baseline
    base_res = simulate_guardian(
        boss_hp=float(scenario_row["boss_hp"]),
        base_dps=base_dps,
        base_ehp=base_ehp,
        base_uptime=base_uptime,
        levels=levels,
        df_eff_=df_eff,
        party_mode=party_mode,
        support_on=support_on,
        skill_level=skill_level,
        n=3000,
        rng_seed=7
    )
    base_cr10 = base_res["cr10"]
    base_cr5 = base_res["cr5"]
    base_mean = base_res["mean_time"]

    rows = []
    for _, upg in df_upg.iterrows():
        m = upg["module"]
        if levels.get(m, None) != int(upg["from_level"]):
            continue

        new_levels = dict(levels)
        new_levels[m] = int(upg["to_level"])

        res = simulate_guardian(
            boss_hp=float(scenario_row["boss_hp"]),
            base_dps=base_dps,
            base_ehp=base_ehp,
            base_uptime=base_uptime,
            levels=new_levels,
            df_eff_=df_eff,
            party_mode=party_mode,
            support_on=support_on,
            skill_level=skill_level,
            n=3000,
            rng_seed=9
        )

        dt = base_mean - res["mean_time"]
        dcr10 = res["cr10"] - base_cr10
        dcr5 = res["cr5"] - base_cr5

        cost_ge = gold_equiv(upg, prices)
        eff = dt / max(1.0, cost_ge)

        rows.append({
            "upgrade_id": upg["upgrade_id"],
            "module": m,
            "from": int(upg["from_level"]),
            "to": int(upg["to_level"]),
            "ΔTime(s)": float(dt),
            "ΔCR10": float(dcr10),
            "ΔCR5": float(dcr5),
            "GoldEqCost": float(cost_ge),
            "Eff(s)/Gold": float(eff),
            "NewEPI": float(res["epi"])
        })

    out = pd.DataFrame(rows)
    if out.empty:
        return out

    # Stage-aware scoring
    if base_cr10 < 0.80:
        w_t, w_10, w_5, w_eff = 0.25, 0.60, 0.00, 0.15
    elif base_cr5 < target_cr5:
        w_t, w_10, w_5, w_eff = 0.30, 0.00, 0.55, 0.15
    else:
        w_t, w_10, w_5, w_eff = 0.20, 0.00, 0.15, 0.65

    def norm(s):
        return (s - s.min()) / (s.max() - s.min() + 1e-9)

    out["score"] = (
        w_t * norm(out["ΔTime(s)"]) +
        w_10 * norm(out["ΔCR10"]) +
        w_5 * norm(out["ΔCR5"]) +
        w_eff * norm(out["Eff(s)/Gold"])
    )

    return out.sort_values("score", ascending=False).head(5)

def sweep_epi_curve(
    scenario_row: pd.Series,
    base_dps: float,
    base_ehp: float,
    base_uptime: float,
    levels: dict,
    party_mode: bool,
    support_on: bool,
    skill_level: str,
    scales=np.linspace(0.8, 1.3, 21)
):
    rows = []
    for s in scales:
        r = simulate_guardian(
            boss_hp=float(scenario_row["boss_hp"]),
            base_dps=base_dps * float(s),
            base_ehp=base_ehp,
            base_uptime=base_uptime,
            levels=levels,
            df_eff_=df_eff,
            party_mode=party_mode,
            support_on=support_on,
            skill_level=skill_level,
            n=2500,
            rng_seed=int(1000*s)
        )
        rows.append({
            "EPI": r["epi"],
            "CR10": r["cr10"],
            "CR5": r["cr5"],
            "MeanTime": r["mean_time"],
            "P90Time": r["p90_time"]
        })
    return pd.DataFrame(rows).sort_values("EPI")

# -----------------------------
# UI
# -----------------------------
st.title("Guardian Clear Verifier (Portfolio Version)")
st.caption("Stage1: CR10(≤10분) ≥ 80% | Stage2: CR5(≤5분) ≥ iLv 목표 (1730+ 파티 & 서폿ON은 +10%p 엄격)")

if "levels" not in st.session_state:
    apply_preset(1600)

# Top input area
colA, colB, colC = st.columns([2, 2, 3])

with colA:
    st.subheader("iLv Presets")
    btn_cols = st.columns(5)
    for c, gate in zip(btn_cols, [1600, 1660, 1700, 1730, 1755]):
        if c.button(f"{gate} 로드"):
            apply_preset(gate)

with colB:
    st.subheader("Mode")
    ilv = st.selectbox("iLv Gate", [1600, 1660, 1700, 1730, 1755], index=0)
    party_mode = st.toggle("Party Mode (2~4)", value=False)
    support_on = st.checkbox("Support ON (서폿 포함)", value=True, disabled=not party_mode)

    skill_level = st.selectbox("Player Skill", ["low", "mid", "high"], index=1)

with colC:
    st.subheader("Modules (0~5)")
    levels = st.session_state.levels
    # sliders override session_state
    levels["enhance"] = st.slider("Enhance", 0, 5, int(levels["enhance"]))
    levels["gems"] = st.slider("Gems", 0, 5, int(levels["gems"]))
    levels["engrave"] = st.slider("Engrave", 0, 5, int(levels["engrave"]))
    levels["ark"] = st.slider("Ark Passive", 0, 5, int(levels["ark"]))
    levels["elixir"] = st.slider("Elixir/Bracelet", 0, 5, int(levels["elixir"]))
    st.session_state.levels = levels

# Scenario row
scenario_row = df_scn[df_scn["ilv_gate"] == ilv].iloc[0]
base_target_cr5 = float(scenario_row["base_target_cr5"])
target_cr5 = stage2_target(ilv, base_target_cr5, party_mode, support_on)

# Advanced base inputs (hidden) - FIXED (no else after with)

# 기본값(항상 유효)
base_dps = 1_200_000
base_ehp = 2_000_000
base_uptime = 0.70

with st.expander("Advanced (internal base stats)", expanded=False):
    base_dps = st.number_input("Base DPS (pre-mult)", value=base_dps, step=50_000, key="base_dps")
    base_ehp = st.number_input("Base EHP (pre-mult)", value=base_ehp, step=50_000, key="base_ehp")
    base_uptime = st.slider("Base Uptime", 0.50, 0.90, base_uptime, 0.01, key="base_uptime")


res = simulate_guardian(
    boss_hp=float(scenario_row["boss_hp"]),
    base_dps=base_dps,
    base_ehp=base_ehp,
    base_uptime=base_uptime,
    levels=levels,
    df_eff_=df_eff,
    party_mode=party_mode,
    support_on=support_on,
    skill_level=skill_level,
    n=9000,
    rng_seed=123
)

# Stage 판단 + 문장
stage1_ok = res["cr10"] >= 0.80
stage2_ok = res["cr5"] >= target_cr5
gap10 = (0.80 - res["cr10"]) * 100
gap5 = (target_cr5 - res["cr5"]) * 100

if not stage1_ok:
    headline = f"Stage1 안정권까지 CR10 +{max(0,gap10):.1f}%p 필요 (목표 80%)"
elif not stage2_ok:
    strict_tag = " · Party(+10%p, 서폿ON)" if (party_mode and support_on and ilv >= 1730) else ""
    headline = (f"Stage2(5분) 달성권까지 CR5 +{max(0,gap5):.1f}%p 필요 "
                f"(목표 {target_cr5*100:.0f}% · iLv {ilv}{strict_tag})")
else:
    headline = "Stage2 달성: 비용 대비 타임 최적화(경쟁) 구간"

st.markdown(f"## {headline}")

# KPI row
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("EPI", f"{res['epi']:.0f}")
k2.metric("CR10 (≤10분)", f"{res['cr10']*100:.1f}%", delta=f"{(res['cr10']-0.80)*100:+.1f}%p")
k3.metric("CR5 (≤5분)", f"{res['cr5']*100:.1f}%", delta=f"{(res['cr5']-target_cr5)*100:+.1f}%p")
k4.metric("Mean Time", f"{res['mean_time']/60:.2f} min")
k5.metric("P90 Time", f"{res['p90_time']/60:.2f} min")

dps_buff, uptime_buff, _ = party_buffs(party_mode, support_on)
st.caption(
    f"Stage2 목표(CR5): 솔로 {base_target_cr5*100:.0f}% / 현재모드 {target_cr5*100:.0f}% | "
    f"Party DPS buff: {dps_buff*100:.0f}% | Party Uptime buff: +{uptime_buff*100:.0f}%p"
)

# Distribution preview
st.subheader("Clear Time Distribution (minutes)")
sample = pd.Series(res["times"][:4000] / 60.0, name="time_min")
st.bar_chart(sample)

# Recommendations
st.subheader("Top 5 Upgrade Recommendations (Stage-aware)")
top5 = recommend_upgrades(
    scenario_row=scenario_row,
    base_dps=base_dps,
    base_ehp=base_ehp,
    base_uptime=base_uptime,
    levels=levels,
    party_mode=party_mode,
    support_on=support_on,
    skill_level=skill_level,
    target_cr5=target_cr5
)

if top5.empty:
    st.info("No applicable upgrades (check current module levels vs candidate list).")
else:
    st.dataframe(top5[["upgrade_id","module","from","to","ΔTime(s)","ΔCR10","ΔCR5","GoldEqCost","Eff(s)/Gold","NewEPI"]])

    # Explain as text
    st.subheader("Recommendation Summary")
    lines = []
    for _, r in top5.iterrows():
        lines.append(
            f"- **{r['module']} {int(r['from'])}→{int(r['to'])}** | "
            f"타임 -{r['ΔTime(s)']:.0f}s | CR10 +{r['ΔCR10']*100:.1f}%p | CR5 +{r['ΔCR5']*100:.1f}%p | "
            f"비용(골드환산) {r['GoldEqCost']:,.0f}G"
        )
    st.markdown("\n".join(lines))

# Curves
st.subheader("Curves")
df_curve = sweep_epi_curve(
    scenario_row=scenario_row,
    base_dps=base_dps,
    base_ehp=base_ehp,
    base_uptime=base_uptime,
    levels=levels,
    party_mode=party_mode,
    support_on=support_on,
    skill_level=skill_level
)

# Graph 1: EPI vs CR10/CR5
fig1 = go.Figure()
fig1.add_trace(go.Scatter(x=df_curve["EPI"], y=df_curve["CR10"]*100, name="CR10(10분)", mode="lines"))
fig1.add_trace(go.Scatter(x=df_curve["EPI"], y=df_curve["CR5"]*100, name="CR5(5분)", mode="lines"))

fig1.add_hline(y=80, line_dash="dash", annotation_text="Stage1: CR10 80%")
fig1.add_hline(y=base_target_cr5*100, line_dash="dot", annotation_text=f"Stage2 Solo Base: {base_target_cr5*100:.0f}%")

# show current mode target (may differ only for 1730+ party+support)
fig1.add_hline(y=target_cr5*100, line_dash="dash",
               annotation_text=f"Stage2 Current Target: {target_cr5*100:.0f}%")

fig1.add_trace(go.Scatter(x=[res["epi"]], y=[res["cr10"]*100], name="Current(CR10)", mode="markers", marker=dict(size=10)))
fig1.add_trace(go.Scatter(x=[res["epi"]], y=[res["cr5"]*100], name="Current(CR5)", mode="markers", marker=dict(size=10)))

fig1.update_layout(xaxis_title="EPI", yaxis_title="Rate (%)")
st.plotly_chart(fig1, use_container_width=True)

# Graph 2: EPI vs Mean/P90 time
fig2 = make_subplots(specs=[[{"secondary_y": False}]])
fig2.add_trace(go.Scatter(x=df_curve["EPI"], y=df_curve["MeanTime"]/60, name="Mean Time", mode="lines"))
fig2.add_trace(go.Scatter(x=df_curve["EPI"], y=df_curve["P90Time"]/60, name="P90 Time", mode="lines", line=dict(dash="dot")))
fig2.add_hline(y=10, line_dash="dash", annotation_text="10분 제한")
fig2.add_hline(y=5, line_dash="dash", annotation_text="5분 목표")
fig2.update_layout(xaxis_title="EPI", yaxis_title="Time (min)")
st.plotly_chart(fig2, use_container_width=True)
