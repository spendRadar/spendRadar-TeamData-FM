# SpendRadar 팀원 지출 데이터 — 시계열 파운데이션 모델 평가

SpendRadar(가천대 AI P-실무프로젝트) 지출 예측에 쓸 모델을 **팀원의 실제 지출**로 검증한 **시계열 파운데이션 모델 4종 zero-shot 평가** 코드·결과.
사용자별 카테고리 6개 + 전체(월 총지출)의 마지막 6개월(2026-05 ~ 2026-10)을 **재귀 방식**(1개월씩 6번, 샘플 경로 200개)으로 예측하고 MAE·MASE·WQL을 Baseline 8가지와 비교함. 같은 방식으로 향후 6개월(2026-11 ~ 2027-04)도 예측함.

- 데이터셋·Baseline: [spendRadar-TeamData-Baseline](https://github.com/spendRadar/spendRadar-TeamData-Baseline) (전처리·포함 조건·Baseline 상세)
- TabFormer 합성 데이터 평가: [spendRadar-Dataset-FM](https://github.com/spendRadar/spendRadar-Dataset-FM) — 이 레포는 그 README의 "팀원 가계부로 추가 검증"에 해당함
- 두 레포(TeamData-Baseline · TeamData-FM)는 같은 데이터(`data/team_monthly_long.csv`)와 같은 계산 코드(`src/spendradar_team.py`)를 사용함

**결론: TimesFM 2.5가 MAE·WQL 1위이고 예상 범위가 가장 정확해(10 ~ 90% 적중률 80%) TabFormer 평가와 같이 서비스 후보 1순위.** 다만 가장 강한 Baseline(HistQuantile 재귀)과의 차이가 MAE 2.1%·WQL 2.6%로 작고 통계적으로 유의하지 않음(시계열 17개 중 9승 8패, p = 0.54). 사용자 3명 · 검증 1구간의 결과라 사용자를 늘린 추가 검증이 필요함.

## 1. 평가 모델
| 모델 | 체크포인트 | 가중치 라이선스 | 노트북 |
|---|---|---|---|
| TimesFM 2.5 (Google) | google/timesfm-2.5-200m-pytorch | Apache-2.0 | `notebooks/run_timesfm_colab.ipynb` |
| Chronos-2 (Amazon) | amazon/chronos-2 | Apache-2.0 | `notebooks/run_chronos_colab.ipynb` |
| Moirai 2.0 (Salesforce) | Salesforce/moirai-2.0-R-small | CC BY-NC 4.0 (비상업) | `notebooks/run_moirai_colab.ipynb` |
| FinCast (CIKM 2025) | Vincent05R/FinCast (v1.pth, 약 4GB) | Apache-2.0 | `notebooks/run_fincast_colab.ipynb` |

- 모두 추가 학습 없이(zero-shot) 시계열마다 예측
- **재귀 예측**: 1개월 예측 분포(분위수 0.1 ~ 0.9)에서 경로마다 값을 하나씩 뽑아(층화 샘플링) 입력 뒤에 붙임 → 6번 반복 → 경로 200개의 월별 분포에서 분위수 계산. 앞 달의 불확실성이 다음 달 입력에 들어가 누적됨
- 전 기간 0원인 시계열은 0원 예측, 음수는 0으로 자르고 분위수는 크기순 정렬
- 입력 길이: 검증 18 ~ 28개월 / 향후 예측 24 ~ 34개월

## 2. 데이터
- 팀원 3명(익명 ID U1 · U2 · U4) × 시계열 7개(식비 / 카페, 주거 / 통신, 쇼핑 / 패션, 교통 / 차량, 문화 / 여가, 의료 + 전체), 월 지출(원)
- 카드 결제(소비)만 사용, 송금 · 이체 · '기타' 제외. U3는 기록 누락으로 포함 조건(기록 기간 18개월 이상) 미달 → 제외
- 검증(test) 2026-05 ~ 2026-10, 평가 시계열 17개 (카테고리 6개 × 3명 중 전 기간 0원인 U1 주거 / 통신 제외)
- 원본 엑셀은 개인 금융 정보라 올리지 않음. 전처리 규칙 · 사용자 포함 여부는 [Baseline 레포](https://github.com/spendRadar/spendRadar-TeamData-Baseline) README

## 3. 결과 (Baseline 포함, 검증 6개월, 3명 종합, 낮을수록 좋음)
| 순위 (MAE) | 모델 | 구분 | MAE 합계 (원/월) | MASE 평균 | WQL 평균 | 10 ~ 90% 적중률 | 전체 시계열 MAE |
|---|---|---|---|---|---|---|---|
| 1 | **TimesFM 2.5** | 파운데이션 모델 | **1,037,471** | 0.865 | **0.390** | **80%** | 166,501 |
| 2 | HistQuantile 재귀 | Baseline | 1,059,699 | 0.875 | 0.401 | 61% | 159,441 |
| 3 | Chronos-2 | 파운데이션 모델 | 1,089,796 | 0.883 | 0.424 | 71% | **147,538** |
| 4 | HistQuantile 직접 (기존 보고서 기준선) | Baseline | 1,099,234 | 0.894 | 0.409 | 63% | 160,427 |
| 5 | Moirai 2.0 | 파운데이션 모델 | 1,129,502 | 0.934 | 0.414 | 65% | 196,513 |
| 6 | 3개월 평균 직접 | Baseline | 1,180,189 | 0.912 | 0.440 | 78% | 152,710 |
| 7 | Naive 직접 | Baseline | 1,196,130 | **0.797** | 0.432 | 81% | 260,111 |
| 8 | 3개월 평균 재귀 | Baseline | 1,243,228 | 0.881 | 0.442 | 81% | 176,680 |
| 9 | SeasonalNaive 직접 · 재귀 | Baseline | 1,314,950 · 1,314,981 | 1.210 | 0.495 · 0.484 | 74% | 220,569 · 220,739 |
| 11 | Naive 재귀 | Baseline | 1,339,240 | 0.837 | 0.477 | 92% | 299,769 |
| 12 | FinCast | 파운데이션 모델 | 1,544,017 | 1.023 | 0.568 | 76% | 194,635 |

- 종합 = 카테고리 6개 기준 사용자 종합(MAE는 카테고리 합, MASE · 적중률은 카테고리 평균, WQL은 카테고리를 합쳐서 계산)의 3명 MAE 합계 · MASE · WQL 평균 (`results/comparison_overall.csv`)
- 전체 시계열 MAE = 월 총지출 시계열 하나의 MAE 3명 평균 (원/월)
- 그림: `report/figures/1_모델별_MAE_WQL.png` · `2_모델별_예상범위_적중률.png` · `3_월총지출_검증_TimesFM_vs_HistQuantile.png`

### 파운데이션 모델 vs Baseline 1:1 비교 (`results/comparison_tests.csv`)
| 모델 | vs HistQuantile 재귀 (승-패, p) | vs HistQuantile 직접 (승-패, p) | vs Naive 직접 (승-패, p) | 최악 배율 |
|---|---|---|---|---|
| **TimesFM 2.5** | 9-8, 0.537 | **11-6, 0.040** | 7-10, 0.500 | 1.31배 |
| Chronos-2 | 7-10, 0.573 | 8-9, 0.306 | 7-10, 0.726 | 1.38배 |
| Moirai 2.0 | 8-9, 0.897 | 8-9, 0.678 | 7-10, 0.573 | 1.43배 |
| FinCast | 5-12, 0.920 | 5-12, 0.897 | 5-12, 0.978 | 2.42배 |

- 승-패 = 시계열 17개에서 MASE가 더 낮은 쪽, p = Wilcoxon 부호순위 검정(단측, 파운데이션 모델이 더 좋다는 가설)
- 비교를 16번(모델 4 × Baseline 4, `comparison_tests.csv`) 했으므로 다중 비교를 보정하면(Bonferroni 기준 0.05 ÷ 16 ≈ 0.003) TimesFM vs HistQuantile 직접의 p = 0.040도 유의하지 않음 — 표본이 작아 '유의한 차이 없음'으로 보는 것이 안전함
- 최악 배율 = 사용자별 1위 MASE 대비 가장 나쁜 배율 (작을수록 어느 사용자에서도 크게 무너지지 않음)

### 해석
- **TimesFM 2.5**: MAE · WQL 1위, 10 ~ 90% 범위 적중률이 목표(80%)와 일치. 기존 보고서 기준선(HistQuantile 직접)보다는 유의하게 정확함(p = 0.04). 가장 강한 Baseline인 HistQuantile 재귀와는 9승 8패로 사실상 비슷하고, 장점은 정확도보다 **예상 범위의 정확성**(HistQuantile 재귀 61%)에 있음
- **Chronos-2**: 종합 3위지만 월 총지출('전체') 시계열 하나는 가장 정확함(MAE 14.8만 원)
- **Moirai 2.0**: 기존 보고서 기준선보다도 MAE가 높고, 비상업 라이선스라 서비스에 쓸 수 없음
- **FinCast**: 12개 중 최하위. 금융 시장 데이터용 모델이라 추세를 이어 가 개인 지출을 부풀림 — U2 쇼핑 / 패션을 매달 71만 ~ 93만 원으로 예측(실제 중앙값 약 9만 원), 6개월 예측 합계 U2 926만 원(최근 6개월 실제 457만 원)
- **MASE**는 Naive 직접이 가장 낮음: 금액이 작은 카테고리(의료 · 교통)의 상대 오차에서 강하기 때문. 금액 기준(MAE)으로는 7위
- 사용자별 MASE: U1(0.28 ~ 0.39)은 모든 상위 모델이 잘 맞히고, U2(1.1 ~ 1.6)는 모두 어려움 — U2는 '지난달 값'(Naive)이 가장 좋음
- TabFormer 평가와 비교: 같은 점은 HistQuantile이 가장 강한 Baseline이고, TimesFM이 선정 모델이며, FinCast가 HistQuantile보다 떨어진다는 것. 다른 점은 TabFormer에서는 상위 3개 모델(Moirai 2.0 · TimesFM 2.5 · Chronos-2)이 모두 HistQuantile보다 정확했지만, 실제 데이터에서는 TimesFM만 HistQuantile 재귀보다 근소하게 앞서고 Moirai 2.0은 5위라는 것
- HistQuantile은 TabFormer 레포(입력 전체 96개월의 분위수)와 달리 최근 12개월의 분위수 (상세: Baseline 레포 2장)

### 향후 6개월 예측 합계 ('전체' 시계열, 2026-11 ~ 2027-04, 만 원, `results/comparison_forecast_total.csv`)
| 모델 | U1 | U2 | U4 |
|---|---|---|---|
| (참고) 최근 6개월 실제 2026-05 ~ 10 | 278 | 457 | 544 |
| **TimesFM 2.5** | 268 | 463 | 543 |
| Chronos-2 | 268 | 439 | 548 |
| Moirai 2.0 | 252 | 445 | 582 |
| FinCast | 239 | 926 | 688 |
| HistQuantile 재귀 | 233 | 392 | 582 |

### 지표
| 지표 | 정의 | 단위 |
|---|---|---|
| MAE | 실제 월 지출과 예측 중앙값(q0.5)의 평균 절대 차이 | 원/월 |
| MASE | MAE ÷ 입력 구간에서 '지난달 값' 예측(lag 1)의 평균 오차. 1 미만이면 그보다 정확 | 없음 |
| WQL | 분위수 0.1 ~ 0.9 예측의 가중 분위수 손실 (2 × Σpinball ÷ Σ\|실제\|, 분위수 평균) | 없음 |

- TabFormer 레포는 MASE 분모로 '작년 같은 달'(m = 12)을 쓰지만, 이 데이터는 입력이 18 ~ 28개월뿐이라 '지난달'(lag 1)을 씀 → 두 레포의 MASE 값은 직접 비교하지 않음

## 4. 폴더 구조
```
data/
  team_monthly_long.csv        3명 × 시계열 7개 월 지출 (Baseline 레포와 동일)
src/
  spendradar_team.py           데이터 로드, 직접·재귀(샘플 경로) 예측, 지표 계산 (Baseline 레포와 공통, 노트북 3 ~ 5번 셀과 같은 계산)
notebooks/
  run_<모델>_colab.ipynb       모델별 Colab 실행 (timesfm · chronos · moirai · fincast), 사람별 표 4개 · 그래프 3개
scripts/
  1_compare.py                 12개 모델 비교 → results/comparison_*.csv
  2_charts.py                  비교 그림 → report/figures/
  3_build_results_xlsx.py      결과 엑셀 → results/SpendRadar_TeamData_results.xlsx
results/
  <모델>/ALL_metrics_<모델>.csv      사용자 × 시계열 지표 (카테고리 '종합' = 카테고리 6개 기준 사용자 종합)
  <모델>/ALL_forecast_<모델>.csv     향후 6개월 예측 (중앙값 · 10% · 90%)
  <모델>/ALL_validation_<모델>.csv   검증 구간 실제 vs 예측
  baseline/                         Baseline 레포 results/의 복사본 (비교용)
  comparison_overall.csv            12개 모델 종합 (MAE · MASE · WQL · 적중률 · 전체 시계열 · 최악 배율)
  comparison_by_user.csv            모델 × 사용자별 지표
  comparison_by_series.csv          모델 × 시계열별 MASE
  comparison_tests.csv              파운데이션 모델 vs Baseline 1:1 비교 (승-패, Wilcoxon p)
  comparison_forecast_total.csv     모델 × 사용자별 향후 6개월 예측 합계
  SpendRadar_TeamData_results.xlsx  위 결과를 시트 8개로 정리 (먼저 이 파일을 보면 됨)
report/figures/                     비교 그림 3개
```

## 5. 실행 방법
**파운데이션 모델 (Colab T4 GPU)**: `notebooks/run_<모델>_colab.ipynb`를 Colab에서 열고 셀을 하나씩 실행 (GitHub에서 바로 열기: `https://colab.research.google.com/github/spendRadar/spendRadar-TeamData-FM/blob/main/notebooks/run_timesfm_colab.ipynb`). 2번 셀이 이 레포의 `data/team_monthly_long.csv`를 받음. 마지막 셀이 내려받는 `ALL_*_<모델>.csv` 3개를 `results/<모델>/`에 넣음. 샘플 경로 200개라 모델당 수 분 ~ 십여 분.

**비교 분석 (CPU)**
```bash
pip install -r requirements.txt
python scripts/1_compare.py
python scripts/2_charts.py
python scripts/3_build_results_xlsx.py
```
- `results/`의 CSV만 있으면 실행됨. Baseline 결과를 새로 만들었다면 Baseline 레포의 `results/ALL_*_baseline.csv` 3개를 `results/baseline/`에 복사
- 그림의 한글 글꼴: Noto Sans CJK KR 또는 나눔고딕
- 검증: 4개 모델 결과의 검증 실제값(126개씩)이 `data/team_monthly_long.csv`와 모두 일치하고, MAE를 검증 상세에서 다시 계산한 값이 지표 파일과 일치함을 확인함

## 6. 한계
- 사용자 3명, 검증 구간 한 번(2026-05 ~ 2026-10)뿐이라 1:1 비교의 표본이 작음(시계열 17개) — TimesFM과 HistQuantile 재귀의 차이는 유의하지 않음
- 입력이 18 ~ 28개월로 짧아 계절성을 배우기 어려움
- 카드 결제만 쓰고 '기타'를 뺐으므로 실제 총지출보다 작음. U2 · U4는 월별 집계라 카테고리 안의 비소비 거래를 확인할 수 없음
- Moirai 2.0은 small 모델만 사용, 모든 모델 파인튜닝 없이 평가
- 샘플 경로 재귀는 시드에 따라 결과가 약간 달라질 수 있음 (경로 200개 기준 MAE 차이 0.2% 이내, 시드 고정). GPU 연산 특성상 같은 시드로 다시 돌려도 파운데이션 모델 결과는 아주 조금 다를 수 있음
- 라이브러리는 최소 버전만 지정함(`timesfm[torch]>=2.0.2`, `chronos-forecasting>=2.1.0`), uni2ts(Moirai)와 FinCast는 GitHub 최신 코드를 설치 → 나중에 다시 돌리면 버전 차이로 결과가 달라질 수 있음 (실행일 2026-11-28, Colab T4)
- MAE 합계는 지출이 큰 사용자(U4 · U2)의 영향이 크고, MASE 평균은 대부분 0원인 '의료' 시계열의 영향을 받음 → 금액 기준 판단은 MAE · WQL, 상대 비교는 사용자별 MASE를 함께 볼 것

## 변경 이력
- **2026-11-28** — 팀 피드백 반영 후 전체 재실행
  - 재귀 예측: 중앙값만 붙이던 방식 → 샘플 경로 200개 (6개월 불확실성 누적)
  - 데이터: 포함 조건 명시(기록 기간 18개월 이상) → 3명, 송금 · '기타' 제외 → 카테고리 '의료 및 기타'를 '의료'로, '전체' 시계열 추가 (상세: Baseline 레포 변경 이력)
  - 분석 코드를 단순화(`scripts/1 ~ 3`), 이전 기준으로 만든 Word 보고서는 삭제
  - 요약 CSV는 소수 6자리로 저장(반올림 두 번에 따른 표기 차이 방지), 노트북 설명의 샘플 경로 수(200개) 정정 — 계산 코드는 변경 없음
- 2026-11-27 — 첫 업로드 (4명, 중앙값 재귀) — 이전 결과는 커밋 기록에 남아 있음
