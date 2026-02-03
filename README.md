🛡️ LOST ARK Guardian Verifier (Balance Verification System)
“단계 목표(Stage Goals) + 확률 기반 안정성(CR10/CR5)으로 밸런스를 검증합니다.”

Project Type: MMORPG PVE 전투 밸런스 검증 & 성장 추천 도구
Core Benchmark: Item Level (iLv)
Output Focus: Clear Time / Clear Rate / Stage Goals / Upgrade Recommendation
Tech Stack: Python, Streamlit, Pandas, NumPy, Plotly
Live Demo: https://guardian-verifier.streamlit.app/
Author: Jihoon Kim (Lead Balance Designer Candidate)
Co-Work: AI Assistant (Implementation/Refactoring Support)
1) 🎯 프로젝트 개요 (Project Objective)
이 프로젝트는 모바일 MMORPG 환경에서, “성장(강화·보석·각인·아크 패시브·엘릭서/팔찌)”이 실제 전투 체감으로 어떻게 연결되는지를 정량화하고, 기획 의도(난이도/리듬/단계 목표)가 실제 결과로 재현되는지 시뮬레이션으로 검증하기 위해 제작되었습니다.

특히 기존 “전투력(환산점수) UI 노출”이 모바일에선 피로 요인이 될 수 있다는 전제 하에,

유저 노출 지표: 아이템 레벨(iLv) + 클리어 타임/클리어율(성공률)
내부 검증 지표: EPI (Effective Power Index, 딜70/생존30 가중)
로 노출/검증 지표를 분리하여 “현실적인 운영”과 “정확한 밸런스 검증”을 동시에 만족시키는 것을 목표로 합니다.

2) 🧠 핵심 설계 철학 (Design Philosophy)
A. iLv를 좌표계로 하는 “단계 목표(Stage Goals)”
Stage 1 = 10분 제한 내 ‘안정 클리어’
Stage 2 = 5분 목표 ‘최적화/경쟁’
같은 콘텐츠라도 iLv 구간에 따라 유저 목적이 달라집니다.
초반은 “실패 방지/학습”, 후반은 “효율/랭킹”이 핵심이므로 목표도 계단형으로 운영해야 합니다.

B. “확률 기반 안정권”을 기준으로 밸런스를 판단
평균(Mean)만 보면 분산/실수/운빨이 반영되지 않아 과대평가가 발생합니다.
본 도구는 Monte Carlo 방식으로 변동성을 포함해,
CR10 = Pr(T ≤ 600s) (10분 내 클리어율)
CR5 = Pr(T ≤ 300s) (5분 내 달성율)
P90Time (느린 꼬리, 실수/운 나쁠 때 체감) 를 핵심 지표로 사용합니다.
C. 솔로 현실 vs 파티 경쟁 메타 분리
파티는 “딜 상승”뿐 아니라 “끊김 감소(업타임 향상)”이 동시에 일어나므로, 파티 구성에 따라 목표/기댓값이 달라져야 합니다.

Party DPS Buff Preset
Support ON: +18%
Support OFF: +10%
Stage2(5분) 목표는 고 iLv 경쟁 메타를 반영하여:
iLv ≥ 1730 AND Party AND Support ON일 때만 +10%p 엄격화
3) ✅ 검증 지표 정의 (KPIs)
1) Clear Time
T = BossHP / SustainedDPS + FailPenalty
2) Clear Rates
CR10: Pr(T ≤ 600s) → Stage1 안정권 판단
CR5: Pr(T ≤ 300s) → Stage2 달성권 판단
3) 안정성
P90Time: 느린 쪽 90퍼센타일 클리어 타임
→ “운/실수 안 좋을 때 체감”을 대변하는 안정성 지표
4) EPI (Effective Power Index)
내부 검증/랭킹용 환산 지표 (유저 UI에는 노출하지 않아도 됨)

EPI = 0.7 * DealScore + 0.3 * SurvivalScore
DealScore는 SustainedDPS 기반, SurvivalScore는 EHP 기반으로 구성(로그 스케일 적용)
4) 🧩 Stage Goals 정책 (Rule Set)
Stage 1 (안정 클리어)
목표: CR10 ≥ 80%
Stage 2 (5분 목표, 계단형)
기본 목표(솔로 기준):

1600: CR5 ≥ 5%
1660: CR5 ≥ 10%
1700: CR5 ≥ 20%
1730: CR5 ≥ 30%
1755: CR5 ≥ 60%
경쟁 메타(파티+서폿) 엄격화:

if party_mode and support_on and ilv >= 1730: target_cr5 += 10%p
5) 🧪 테스트 방법 (How to Test / Verification Checklist)
아래 체크리스트는 “시뮬레이터가 제대로 동작하고, 밸런서가 믿고 쓸 수 있는지” 검증하는 순서입니다.

Step 1. 정책/룰 검증 (Rule Validation)
Stage1 목표가 항상 CR10 ≥ 80%로 고정되는지
Stage2 목표가 iLv에 따라 계단형으로 바뀌는지
1730+에서만 (Party & Support ON)일 때 Stage2 목표가 +10%p 되는지
Party DPS buff가 Support ON(+18%), OFF(+10%)로 적용되는지
이 단계는 “운영 정책이 정확히 구현되었는지” 검증합니다.

Step 2. 단조성 검증 (Monotonicity Check)
모듈을 올리면 결과가 ‘상식적으로’ 좋아져야 합니다.

동일 조건에서 모듈을 +1 했을 때:
MeanTime ↓
CR10 ↑ 또는 유지
CR5 ↑ 또는 유지
단조성이 깨지면 보통:

module_effects 계수 오류
추천/정규화 계산 버그
표본 수(n)가 너무 작아 RNG 노이즈가 큰 경우
Step 3. 현실성 검증 (Solo vs Party Realism)
같은 iLv/세팅에서 일반적으로 성립해야 하는 관계:

Solo < Party(Support OFF) < Party(Support ON)
(시간은 짧아지고, 확률은 높아져야 정상)
또한 고 iLv(1730+)에서는:

Support ON이 성능을 올리지만 목표도 엄격해져
**“성능↑ + 목표↑”**가 동시에 보이는 것이 설계 의도입니다.
Step 4. 추천 시스템 검증 (Recommendation Policy)
추천이 단계 목표에 맞게 바뀌는지 확인합니다.

Stage1 미달: 추천이 ΔCR10 중심으로 나오는가?
Stage1 OK & Stage2 미달: 추천이 ΔCR5 + ΔTime 중심으로 나오는가?
Stage2 OK: 추천이 효율(초/골드환산) 중심으로 나오는가?
6) 🧰 파일 구조 (File Structure)
Copyguardian-verifier/
├── app.py                    # Streamlit UI + 시뮬 실행 + 추천 + 그래프
├── requirements.txt          # Python dependencies
└── data/
    ├── guardian_scenarios.csv    # iLv별 보스 시나리오(HP, Stage2 base target 등)
    ├── presets.csv              # iLv 프리셋(모듈 레벨 기본값)
    ├── module_effects.csv       # 모듈 레벨 → DPS/EHP/업타임 계수
    ├── upgrade_candidates.csv   # 업그레이드 후보(단계 이동) + 비용(골드/재료)
    └── market_prices.csv        # 재료 시세(골드 환산용, 옵션)
7) 📄 데이터 스키마 (CSV Schema)
1) guardian_scenarios.csv
컬럼	설명
guardian_id / name / difficulty	시나리오 식별자
ilv_gate	iLv 구간
boss_hp	보스 체력(시뮬 입력)
time_limit_sec	제한시간(10분=600 권장)
required_epi	내부 기준점(옵션/튜닝용)
base_target_cr5	Stage2 기본 목표(솔로 기준)
2) presets.csv
컬럼	설명
ilv_gate	iLv 구간
enhance/gems/engrave/ark/elixir	모듈 프리셋 레벨(0~5)
notes	메모
3) module_effects.csv
컬럼	설명
module	enhance/gems/engrave/ark/elixir
level	0~5 (확장 가능)
dps_mult	딜 배율
ehp_mult	생존 배율
uptime_add	업타임 보정(끊김 감소)
notes	메모
4) upgrade_candidates.csv
컬럼	설명
module/from_level/to_level	업그레이드 정의
gold_cost	골드 비용
mat1_id/mat1_qty	재료1
mat2_id/mat2_qty	재료2
5) market_prices.csv
컬럼	설명
item_id	재료 ID
price_gold	개당 골드
last_updated	갱신 시간
8) 📌 튜닝 가이드 (Calibration Guide)
이 툴의 목적은 “공식을 1:1로 복제”가 아니라 운영 가능한 검증 프레임입니다.
따라서 튜닝은 다음 순서가 가장 효율적입니다.

A. 앵커(Anchor) 2~3개만 먼저 맞추기
예시:

iLv 1600 솔로 프리셋: 평균 8~9분대
iLv 1730 파티+서폿ON: CR5 목표(40%) 근처
iLv 1755 파티+서폿ON: 경쟁 구간(목표 70%) 근처
B. 조정 레버(변수)는 3개만
boss_hp(iLv별)
module_effects의 dps_mult 스케일(특히 보석/각인)
숙련도별 fail_base / fail_time_loss_base
C. 조정 후 회귀 테스트
Rule Validation → Monotonicity → Recommendation Policy 순으로 다시 확인
9) 🧾 실행 방법 (Run Locally)
Copypip install -r requirements.txt
streamlit run app.py
10) ⚠️ 인코딩/데이터 주의사항 (Excel Export Notes)
Excel/VBA로 CSV를 익스포트할 경우, 기본 CSV는 CP949로 저장되어 리눅스(UTF-8) 환경에서 에러가 날 수 있습니다.
Office365 사용 시 xlCSVUTF8로 저장 권장
안전을 위해 Python 로더에 encoding fallback을 둘 수 있습니다.
11) 🤝 Credits / Collaboration
Lead Designer: Jihoon Kim

Balance Framework Design (Stage Goals, CR10/CR5 Policy)
Data Schema & Verification Checklist
Contact: gartist1006@naver.com
Technical Partner: AI Assistant

Python Implementation Support
Streamlit UI/UX, Debugging, Refactoring
12) 📍 Roadmap (Optional)
 직업 프리셋(광딜/단일/백어택 의존 등) 추가
 “최소 비용으로 Stage 달성” 탐색(그리디/DP) 기능 추가
 솔로 vs 파티 곡선 오버레이 비교 모드
 거래소 API 연동(캐시 적용)으로 비용 환산 자동화
