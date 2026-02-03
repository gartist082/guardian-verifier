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
    # 파일 경로가 프로젝트 구조에 따라 다를 수 있으니 확인 필요 (예: "data/...")
    try:
        scn = pd.read_csv("guardian_scenarios.csv")
        eff = pd.read_csv("module_effects.csv")
        upg = pd.read_csv("upgrade_candidates.csv")
        price = pd.read_csv("market_prices.csv")
        presets = pd.read_csv("presets.csv")
    except FileNotFoundError:
        # 데이터 폴더 내에 있는 경우 대비
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
    return row.iloc[0]

def calc_epi(params):
    # dps_mult 합산 (곱연산 방식)
    dps_m = 1.0
    ehp_m = 1.0
    u_add = 0.0
    
    for m in ["enhance", "gems", "engrave", "ark", "elixir"]:
        row = get_effect(df_eff, m, params[m])
        dps_m *= row["dps_mult"]
        ehp_m *= row["ehp_mult"]
        u_add += row["uptime_add"]
    
    # EPI 계산 공식 (예시)
    base_epi = dps_m * 1000
    # 업타임 및 생존 가중치 적용
    final_epi = base_epi * (1 + u_add) * (ehp_m ** 0.2)
    return {
        "epi": final_epi,
        "dps_m": dps_m,
        "ehp_m": ehp_m,
        "u_add": u_add
    }

def simulate_cr(epi, boss_hp, time_limit, req_epi):
    # 단순화된 성공 확률 모델 (Sigmoid)
    # req_epi 근처에서 확률이 급변하도록 설계
    k = 0.005 # 경사도
    x = epi - req_epi
    cr10 = 1 / (1 + math.exp(-k * x))
    
    # 5분 클리어는 더 높은 EPI 요구
    x5 = epi - (req_epi * 1.4)
    cr5 = 1 / (1 + math.exp(-k * x5))
    
    return cr10, cr5

# -----------------------------
# Sidebar
# -----------------------------
st.sidebar.title("Character Settings")
sel_scenario = st.sidebar.selectbox("Target Guardian", df_scn["name"].unique())
df_target_scn = df_scn[df_scn["name"] == sel_scenario]
sel_lv = st.sidebar.selectbox("Level / Difficulty", df_target_scn["ilv_gate"].unique())

row_scn = df_target_scn[df_target_scn["ilv_gate"] == sel_lv].iloc[0]

st.sidebar.divider()
st.sidebar.subheader("Growth Modules")
p_enhance = st.sidebar.slider("Enhance Level", 0, 5, 2)
p_gems = st.sidebar.slider("Gems Level", 0, 5, 2)
p_engrave = st.sidebar.slider("Engrave Level", 0, 5, 2)
p_ark = st.sidebar.slider("Ark Passive", 0, 5, 2)
p_elixir = st.sidebar.slider("Elixir", 0, 5, 2)

params = {
    "enhance": p_enhance,
    "gems": p_gems,
    "engrave": p_engrave,
    "ark": p_ark,
    "elixir": p_elixir
}

# -----------------------------
# Logic
# -----------------------------
res = calc_epi(params)
cr10, cr5 = simulate_cr(res["epi"], row_scn["boss_hp"], row_scn["time_limit_sec"], row_scn["required_epi"])
res["cr10"] = cr10
res["cr5"] = cr5

# -----------------------------
# UI - Dashboard
# -----------------------------
st.title(f"Balance Verifier: {sel_scenario} ({sel_lv})")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Current EPI", f"{res['epi']:.0f}")
col2.metric("Required EPI", f"{row_scn['required_epi']}")
col3.metric("Clear Rate (10m)", f"{res['cr10']*100:.1f}%")
col4.metric("Clear Rate (5m)", f"{res['cr5']*100:.1f}%")

st.divider()

# Curves Section
st.subheader("Success Probability Curves")

# [수정포인트 1] X축 범위를 현재 EPI 기준으로 가변적으로 설정 (조작 시 그래프가 움직이는 효과)
current_epi = res["epi"]
# 현재 EPI를 중심으로 범위를 잡되, 최소/최대 요구치를 포함하도록 유연하게 설정
x_min = max(0, min(current_epi * 0.5, row_scn["required_epi"] * 0.5))
x_max = max(current_epi * 1.5, row_scn["required_epi"] * 1.8)
x_range = np.linspace(x_min, x_max, 100)

curve_data = []
for x in x_range:
    c10, c5 = simulate_cr(x, row_scn["boss_hp"], row_scn["time_limit_sec"], row_scn["required_epi"])
    curve_data.append({"EPI": x, "CR10": c10, "CR5": c5})
df_curve = pd.DataFrame(curve_data)

fig1 = go.Figure()
fig1.add_trace(go.Scatter(x=df_curve["EPI"], y=df_curve["CR10"]*100, name="CR10 (10분 기준)", line=dict(color='royalblue', width=2)))
fig1.add_trace(go.Scatter(x=df_curve["EPI"], y=df_curve["CR5"]*100, name="CR5 (5분 기준)", line=dict(color='firebrick', width=2, dash='dot')))

# [수정포인트 2] 현재 스펙 위치(점)를 훨씬 크게 강조 (조작 시 이동이 잘 보임)
fig1.add_trace(go.Scatter(
    x=[res["epi"]], y=[res["cr10"]*100], 
    name="내 현재 위치 (CR10)", 
    mode="markers+text",
    text=["현재 스펙"],
    textposition="top center",
    marker=dict(size=18, color='gold', symbol='diamond', line=dict(width=2, color='black'))
))

# [수정포인트 3] 가이드라인 글자 겹침 방지 (y위치를 다르게 하고 설명을 간소화)
target_cr10 = 80
target_cr5 = row_scn["base_target_cr5"] * 100

fig1.add_hline(y=target_cr10, line_dash="dash", line_color="green", 
               annotation_text="권장 클리어 확률 (80%)", annotation_position="top left")
fig1.add_hline(y=target_cr5, line_dash="dot", line_color="orange", 
               annotation_text="최소 도전 가능선", annotation_position="bottom left")

fig1.update_layout(
    xaxis_title="종합 전투력 지표 (EPI)", 
    yaxis_title="클리어 확률 (%)",
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)
st.plotly_chart(fig1, use_container_width=True)

# -----------------------------
# ROI Analysis (Bottom)
# -----------------------------
st.divider()
st.subheader("Next Upgrade Recommendation (ROI Analysis)")

# 가상의 추천 로직 (EPI 상승 대비 비용 계산)
reco_data = []
for m in ["enhance", "gems", "engrave", "ark", "elixir"]:
    curr_lv = params[m]
    if curr_lv < 5:
        # upgrade_candidates에서 비용 가져오기
        try:
            u_row = df_upg[(df_upg["module"] == m) & (df_upg["from_level"] == curr_lv)].iloc[0]
            cost = u_row["gold_cost"]
            
            # 1레벨 상승 시 dps_mult 차이 계산
            eff_curr = get_effect(df_eff, m, curr_lv)["dps_mult"]
            eff_next = get_effect(df_eff, m, curr_lv + 1)["dps_mult"]
            dmg_inc = (eff_next / eff_curr - 1) * 100
            
            reco_data.append({
                "Module": m.capitalize(),
                "Target": f"Lv.{curr_lv} → {curr_lv+1}",
                "Gold Cost": f"{cost:,}",
                "DMG Increase": f"{dmg_inc:.2f}%",
                "Cost per 1%": int(cost / dmg_inc)
            })
        except:
            continue

if reco_data:
    df_reco = pd.DataFrame(reco_data).sort_values("Cost per 1%")
    st.table(df_reco)
else:
    st.write("모든 모듈이 최대 레벨입니다.")