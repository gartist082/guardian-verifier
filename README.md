# 🛡️ LOST ARK Guardian Verifier

> **“단계 목표(Stage Goals) + 확률 기반 안정성(CR10/CR5)으로 밸런스를 검증합니다.”**  
> * **Project Type:** MMORPG PVE 전투 밸런스 검증 & 성장 추천 도구  
> * **Core Benchmark:** **Item Level (iLv)**  
> * **Output Focus:** Clear Time / Clear Rate / Stage Goals / Upgrade Recommendation  
> * **Tech Stack:** Python, Streamlit, Pandas, NumPy, Plotly  
> * **Live Demo:** https://guardian-verifier.streamlit.app/  
> * **Author:** Jihoon Kim (Lead Balance Designer Candidate)  
> * **Co-Work:** AI Assistant (Implementation/Refactoring Support)

---

## 1) 🎯 프로젝트 개요 (Project Objective)

이 프로젝트는 모바일 MMORPG 환경에서, “성장(강화·보석·각인·아크 패시브·엘릭서/팔찌)”이 실제 전투 체감으로 어떻게 연결되는지를 **정량화**하고, 기획 의도(난이도/리듬/단계 목표)가 실제 결과로 재현되는지 **시뮬레이션으로 검증**하기 위해 제작되었습니다.

특히 기존 “전투력(환산점수) UI 노출”이 모바일에선 피로 요인이 될 수 있다는 전제 하에,

- 유저 노출 지표: **아이템 레벨(iLv) + 클리어 타임/클리어율(성공률)**
- 내부 검증 지표: **EPI (Effective Power Index, 딜70/생존30 가중)**

로 **노출/검증 지표를 분리**하여 “현실적인 운영”과 “정확한 밸런스 검증”을 동시에 만족시키는 것을 목표로 합니다.

---

## 2) 🧠 핵심 설계 철학 (Design Philosophy)

### A. iLv를 좌표계로 하는 “단계 목표(Stage Goals)”
- **Stage 1 = 10분 제한 내 ‘안정 클리어’**
- **Stage 2 = 5분 목표 ‘최적화/경쟁’**

> 같은 콘텐츠라도 iLv 구간에 따라 유저 목적이 달라집니다.  
> 초반은 “실패 방지/학습”, 후반은 “효율/랭킹”이 핵심이므로 목표도 계단형으로 운영해야 합니다.

### B. “확률 기반 안정권”을 기준으로 밸런스를 판단
- 평균(Mean)만 보면 분산/실수/운빨이 반영되지 않아 **과대평가**가 발생합니다.
- 본 도구는 Monte Carlo 방식으로 변동성을 포함해,
  - **CR10 = Pr(T ≤ 600s)** (10분 내 클리어율)
  - **CR5 = Pr(T ≤ 300s)** (5분 내 달성율)
  - **P90Time** (느린 꼬리, 실수/운 나쁠 때 체감)
  를 핵심 지표로 사용합니다.

### C. 솔로 현실 vs 파티 경쟁 메타 분리
파티는 “딜 상승”뿐 아니라 “끊김 감소(업타임 향상)”이 동시에 일어나므로, 파티 구성에 따라 목표/기댓값이 달라져야 합니다.

- Party DPS Buff Preset
  - **Support ON:** +18%
  - **Support OFF:** +10%
- Stage2(5분) 목표는 고 iLv 경쟁 메타를 반영하여:
  - **iLv ≥ 1730 AND Party AND Support ON**일 때만 **+10%p 엄격화**

---

## 3) ✅ 검증 지표 정의 (KPIs)

### 1) Clear Time
- `T = BossHP / SustainedDPS + FailPenalty`

### 2) Clear Rates
- **CR10:** `Pr(T ≤ 600s)` → Stage1 안정권 판단
- **CR5:** `Pr(T ≤ 300s)` → Stage2 달성권 판단

### 3) 안정성
- **P90Time:** 느린 쪽 90퍼센타일 클리어 타임  
  → “운/실수 안 좋을 때 체감”을 대변하는 안정성 지표

### 4) EPI (Effective Power Index)
내부 검증/랭킹용 환산 지표 (유저 UI에는 노출하지 않아도 됨)

- `EPI = 0.7 * DealScore + 0.3 * SurvivalScore`
- DealScore는 SustainedDPS 기반, SurvivalScore는 EHP 기반으로 구성(로그 스케일 적용)

---

## 4) 🧩 Stage Goals 정책 (Rule Set)

### Stage 1 (안정 클리어)
- **목표:** `CR10 ≥ 80%`

### Stage 2 (5분 목표, 계단형)
- **기본 목표(솔로 기준):**
  - 1600: CR5 ≥ 5%
  - 1660: CR5 ≥ 10%
  - 1700: CR5 ≥ 20%
  - 1730: CR5 ≥ 30%
  - 1755: CR5 ≥ 60%

- **경쟁 메타(파티+서폿) 엄격화:**
  - `if party_mode and support_on and ilv >= 1730: target_cr5 += 10%p`
  - 예: 1730 파티+서폿ON → CR5 목표 40%, 1755 파티+서폿ON → CR5 목표 70%

---

## 5) 🧪 테스트 방법 (How to Test / Verification Checklist)

아래 체크리스트는 “시뮬레이터가 제대로 동작하고, 밸런서가 믿고 쓸 수 있는지” 검증하는 순서입니다.

### Step 1. 정책/룰 검증 (Rule Validation)
1) Stage1 목표가 항상 `CR10 ≥ 80%`로 고정되는지  
2) Stage2 목표가 iLv에 따라 계단형으로 바뀌는지  
3) **1730+에서만** (Party & Support ON)일 때 Stage2 목표가 +10%p 되는지  
4) Party DPS buff가 Support ON(+18%), OFF(+10%)로 적용되는지

> 이 단계는 “운영 정책이 정확히 구현되었는지” 검증합니다.

### Step 2. 단조성 검증 (Monotonicity Check)
모듈을 올리면 결과가 ‘상식적으로’ 좋아져야 합니다.

- 동일 조건에서 모듈을 +1 했을 때:
  - MeanTime ↓
  - CR10 ↑ 또는 유지
  - CR5 ↑ 또는 유지

단조성이 깨지면 보통:
- module_effects 계수 오류
- 추천/정규화 계산 버그
- 표본 수(n)가 너무 작아 RNG 노이즈가 큰 경우

### Step 3. 현실성 검증 (Solo vs Party Realism)
같은 iLv/세팅에서 일반적으로 성립해야 하는 관계:

- **Solo < Party(Support OFF) < Party(Support ON)**  
(시간은 짧아지고, 확률은 높아져야 정상)

또한 고 iLv(1730+)에서는:
- Support ON이 성능을 올리지만 목표도 엄격해져  
  **“성능↑ + 목표↑”**가 동시에 보이는 것이 설계 의도입니다.

### Step 4. 추천 시스템 검증 (Recommendation Policy)
추천이 단계 목표에 맞게 바뀌는지 확인합니다.

- Stage1 미달: 추천이 `ΔCR10` 중심으로 나오는가?
- Stage1 OK & Stage2 미달: 추천이 `ΔCR5` + `ΔTime` 중심으로 나오는가?
- Stage2 OK: 추천이 `효율(초/골드환산)` 중심으로 나오는가?

---

## 6) 🧰 파일 구조 (File Structure)

```bash
guardian-verifier/
├── app.py                    # Streamlit UI + 시뮬 실행 + 추천 + 그래프
├── requirements.txt          # Python dependencies
└── data/
    ├── guardian_scenarios.csv    # iLv별 보스 시나리오(HP, Stage2 base target 등)
    ├── presets.csv              # iLv 프리셋(모듈 레벨 기본값)
    ├── module_effects.csv       # 모듈 레벨 → DPS/EHP/업타임 계수
    ├── upgrade_candidates.csv   # 업그레이드 후보(단계 이동) + 비용(골드/재료)
    └── market_prices.csv        # 재료 시세(골드 환산용, 옵션)

## 7) 📄 데이터 스키마 (CSV Schema)

> 본 프로젝트는 **코드 수정 없이 CSV 교체/수정만으로** 밸런스 정책과 시뮬 결과를 튜닝할 수 있도록 설계되었습니다.  
> (운영/라이브 환경에서는 “데이터 드리븐”이 유지보수 비용을 가장 크게 줄입니다.)

---

### 7.1 `data/guardian_scenarios.csv` (가디언 시나리오 정의)

| 컬럼 | 타입 | 예시 | 설명 |
|---|---:|---|---|
| `guardian_id` | str | `G_BHM_N` | 시나리오 ID |
| `name` | str | `Behemoth` | 보스 이름 |
| `difficulty` | str | `Normal` | 난이도 |
| `ilv_gate` | int | `1730` | 아이템 레벨 구간(좌표계) |
| `boss_hp` | float/int | `165000000` | 보스 체력(클리어 타임 산출 핵심 변수) |
| `time_limit_sec` | int | `600` | 제한시간(10분) |
| `required_epi` | float | `3900` | 내부 기준점(옵션/튜닝용, 필요시) |
| `base_target_cr5` | float | `0.30` | **Stage2 기본 목표(CR5) — 솔로 기준** |

**Stage2 최종 목표 적용 규칙(코드에서 적용):**
- `target_cr5 = base_target_cr5`
- `if party_mode and support_on and ilv_gate >= 1730: target_cr5 += 0.10`

> 즉 CSV에는 “기본값(솔로 기준)”만 두고, 경쟁 메타(파티+서폿) 엄격화는 정책 로직으로 관리합니다.

---

### 7.2 `data/presets.csv` (iLv 프리셋/표준 세팅)

| 컬럼 | 타입 | 예시 | 설명 |
|---|---:|---|---|
| `ilv_gate` | int | `1600` | 구간 |
| `enhance` | int | `2` | 강화/재련 프리셋 레벨(0~5) |
| `gems` | int | `1` | 보석 프리셋 레벨(0~5) |
| `engrave` | int | `1` | 각인 프리셋 레벨(0~5) |
| `ark` | int | `2` | 아크패시브 프리셋 레벨(0~5) |
| `elixir` | int | `0` | 엘릭서/팔찌 프리셋 레벨(0~5) |
| `notes` | str | `보석7/각인유물2` | 기획 메모 |

**의도:**
- 버튼 한 번으로 “표준 세팅(현실 메타)”을 주입 → 검증/비교가 쉬워짐
- 이후 슬라이더로 미세 조정 → “왜 이 업글이 추천되는지” 확인 가능

---

### 7.3 `data/module_effects.csv` (성장 모듈 효과 테이블)

| 컬럼 | 타입 | 예시 | 설명 |
|---|---:|---|---|
| `module` | str | `gems` | 모듈 종류 (`enhance/gems/engrave/ark/elixir`) |
| `level` | int | `3` | 모듈 레벨(0~5, 확장 가능) |
| `dps_mult` | float | `1.13` | 딜 배율(딜 70% 축에 반영) |
| `ehp_mult` | float | `1.00` | 생존 배율(EHP, 생존 30% 축에 반영) |
| `uptime_add` | float | `0.02` | 업타임 보정(끊김 감소, 실전 DPS 영향) |
| `notes` | str | `~9레` | 메모 |

**설계 포인트:**
- MVP에서는 “복잡한 로아 공식”을 직접 복제하지 않고,  
  **운영 가능한 계수 테이블(dps/ehp/uptime)**로 모델을 구성합니다.
- 실제 메타 정합성은 **캘리브레이션(튜닝)**으로 끌어올립니다.

---

### 7.4 `data/upgrade_candidates.csv` (업그레이드 후보 & 비용)

| 컬럼 | 타입 | 예시 | 설명 |
|---|---:|---|---|
| `upgrade_id` | str | `U_GEM_2_3` | 업그레이드 ID |
| `module` | str | `gems` | 대상 모듈 |
| `from_level` | int | `2` | 현재 레벨 |
| `to_level` | int | `3` | 목표 레벨 |
| `gold_cost` | float/int | `360000` | 골드 비용 |
| `mat1_id` | str | `honor_token` | 재료1 ID |
| `mat1_qty` | float/int | `150` | 재료1 수량 |
| `mat2_id` | str | `destruction_shard` | 재료2 ID |
| `mat2_qty` | float/int | `220` | 재료2 수량 |

**추천 엔진에서의 사용 방식:**
- 가능한 후보를 전부 “1-step 적용”해보고  
  `ΔCR10`, `ΔCR5`, `ΔTime`, `Cost`를 계산
- Stage 상태에 따라 점수를 다르게 매겨 TOP5 추천

---

### 7.5 `data/market_prices.csv` (재료 단가/골드 환산)

| 컬럼 | 타입 | 예시 | 설명 |
|---|---:|---|---|
| `item_id` | str | `honor_token` | 재료 ID |
| `item_name` | str | `Honor Token` | 표기명 |
| `price_gold` | float | `800` | 개당 골드 |
| `last_updated` | str | `2026-02-03T00:00:00` | 갱신 시각 |

**골드 환산 비용 공식:**
- `GoldEqCost = gold_cost + mat1_qty*price(mat1) + mat2_qty*price(mat2)`

> (옵션) 추후 거래소 API 연동 시 `market_prices.csv`를 자동 갱신하도록 확장 가능합니다.

---

## 8) 📌 튜닝 가이드 (Calibration Guide)

이 툴의 목적은 “공식을 1:1로 복제”가 아니라 **운영 가능한 검증 프레임**을 만드는 것입니다.  
정확도는 다음 순서로 빠르게 끌어올릴 수 있습니다.

### 8.1 앵커(Anchor) 2~3개만 먼저 맞추기
예시(가정):
- iLv 1600 솔로 프리셋: 평균 8~9분대, CR10은 80% 근처
- iLv 1730 파티+서폿ON: Stage2 목표(기본 30% + 엄격 10%p = 40%) 근처
- iLv 1755 파티+서폿ON: Stage2 목표 70% 근처

### 8.2 조정 레버(변수)는 3개만
1) `boss_hp`(iLv별)  
2) `module_effects.csv`의 `dps_mult` 스케일(특히 보석/각인)  
3) 숙련도별 `fail_base`, `fail_time_loss_base` (실수/변동성 크기 조절)

### 8.3 조정 후 회귀 테스트(Regression)
- Rule Validation → Monotonicity → Recommendation Policy 순으로 재검증  
- 결과가 “상식적 방향(단조성)”을 깨면 계수/모델을 재점검합니다.

---

## 9) 🧾 실행 방법 (Run Locally)

```bash
pip install -r requirements.txt
streamlit run app.py

---

## 10) ⚠️ 인코딩/데이터 주의사항 (Excel Export Notes)

- 본 프로젝트는 CSV 기반으로 동작합니다.  
- Windows Excel/VBA에서 CSV를 생성할 경우 **인코딩/구분자(Delimiter)** 이슈로 리눅스(Streamlit Cloud) 환경에서 에러가 발생할 수 있습니다.

### 10.1 UTF-8 저장 권장 (Office 365)
- Office365 최신 버전에서는 CSV를 **UTF-8**로 저장하는 것이 가장 안전합니다.
- VBA 익스포트 시 `FileFormat:=xlCSVUTF8` 사용을 권장합니다.

예시(VBA):
```vb
Const xlCSVUTF8 As Long = 62
ActiveWorkbook.SaveAs Filename:=targetPath & ws.Name & ".csv", _
                     FileFormat:=xlCSVUTF8, _
                     Local:=True

### 10.2 Streamlit Cloud에서 UnicodeDecodeError가 날 때
에러 예시:

UnicodeDecodeError 발생
pd.read_csv("data/module_effects.csv") 등에서 디코딩 실패
대응 체크리스트:

- 엑셀에서 새로 추출한 CSV가 GitHub에 커밋/푸시되었는지 확인
- Streamlit Cloud에서 Reboot / Clear cache 실행
- 그래도 문제라면 아래처럼 Python 로더에 encoding fallback 적용
- 마지막으로 CSV를 VSCode에서 열고 UTF-8로 재저장(Save with Encoding → UTF-8)

---

## 11) 🤝 Credits / Collaboration
- Lead Designer: Jihoon Kim
- Balance Framework Design (Stage Goals, CR10/CR5 Policy)
- Data Schema & Verification Checklist
- Contact: gartist1006@naver.com
- Technical Partner: AI Assistant (ChatGPT)
- Python Implementation Support
- Streamlit UI/UX Construction
- Debugging & Refactoring Support

---

## 12) 📍 Roadmap (Optional)
- 직업 프리셋(광딜/단일/백어택 의존 등) 추가
- “최소 비용으로 Stage 달성” 탐색(그리디/DP) 기능 추가
- 솔로 vs 파티 곡선 오버레이 비교 모드(동일 화면 비교)
- 거래소 API 연동(캐시 적용)으로 비용 환산 자동화
- 데이터 검증 자동화: CSV 스키마/결측치/타입 검사(런타임 전 체크)




