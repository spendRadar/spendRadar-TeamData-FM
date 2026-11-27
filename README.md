# SpendRadar 팀원 지출 데이터 — 시계열 파운데이션 모델 평가

SpendRadar(가천대 AI P-실무프로젝트) 지출 예측에 쓸 모델을 **팀원 4명의 실제 지출**로 검증한 **시계열 파운데이션 모델 4종 zero-shot 평가** 코드·결과·보고서.
사용자별 카테고리 6개의 월 지출로 마지막 6개월(2026-05 ~ 2026-10)을 **재귀 방식**(1개월씩 6번)으로 예측하고 MAE·MASE·WQL을 Baseline 8가지와 비교함. 같은 방식으로 향후 6개월(2026-11 ~ 2027-04)도 예측함.

- 데이터셋·Baseline: [spendRadar-TeamData-Baseline](https://github.com/terrio458/spendRadar-TeamData-Baseline)
- TabFormer 합성 데이터 평가: [spendRadar-Dataset-FM](https://github.com/spendRadar/spendRadar-Dataset-FM) — 이 레포는 그 README의 "팀원 가계부로 추가 검증"에 해당함
- 두 레포(TeamData-Baseline · TeamData-FM)는 같은 데이터(`data/team_monthly_long.csv`)와 같은 계산 코드(`src/spendradar_team.py`)를 사용함

**결론: TabFormer 평가와 같이 TimesFM 2.5를 서비스 모델로 권고.** 기존 보고서 기준선(HistQuantile)보다 유의하게 정확하고(p = 0.028), 파운데이션 모델 중 최악의 경우 오차가 가장 작으며, 재귀 6개월 예측이 한 방향으로 쏠리지 않음. 다만 실제 데이터에서는 단순한 3개월 평균 재귀가 평균 정확도 1위라, 4명·6개월 한 구간의 결과로 보고 추가 검증이 필요함.

## 1. 평가 모델
| 모델 | 체크포인트 | 가중치 라이선스 | 노트북 |
|---|---|---|---|
| TimesFM 2.5 (Google) | google/timesfm-2.5-200m-pytorch | Apache-2.0 | `notebooks/run_timesfm_colab.ipynb` |
| Chronos-2 (Amazon) | amazon/chronos-2 | Apache-2.0 | `notebooks/run_chronos_colab.ipynb` |
| Moirai 2.0 (Salesforce) | Salesforce/moirai-2.0-R-small | CC BY-NC 4.0 (비상업) | `notebooks/run_moirai_colab.ipynb` |
| FinCast (CIKM 2025) | Vincent05R/FinCast (v1.pth, 약 4GB) | Apache-2.0 | `notebooks/run_fincast_colab.ipynb` |

- 모두 추가 학습 없이(zero-shot) 사용자 × 카테고리 시계열마다 1개월 예측 → 예측 중앙값을 입력 뒤에 붙임 → 6번 반복 (재귀), 분위수 0.1 ~ 0.9 출력
- 입력 길이는 사용자마다 16 ~ 28개월(검증) / 22 ~ 34개월(향후 예측)
- 전 기간 0원인 카테고리는 모델에 넣지 않고 0원 예측, 음수는 0으로 자르고 분위수는 크기순 정렬

## 2. 데이터
- 팀원 4명(익명 ID U1 ~ U4) × 카테고리 6개(식비 / 카페, 주거 / 통신, 쇼핑 / 패션, 의료 및 기타, 교통 / 차량, 문화 / 여가) 월 지출(원), 사용자별 22 ~ 34개월
- 검증(test) 2026-05 ~ 2026-10, 평가 시계열 23개 (U1은 주거 / 통신 지출 없음)
- 원본 엑셀은 개인 금융 정보라 올리지 않음. 전처리 방법·통계는 [Baseline 레포](https://github.com/terrio458/spendRadar-TeamData-Baseline) README 참고

## 3. 결과 (Baseline 포함, 검증 6개월, 4명 종합, 낮을수록 좋음)
| 순위 (MAE) | 모델 | 구분 | MAE 합계 (원/월) | MASE 평균 | WQL 평균 | 10 ~ 90% 범위 적중률 |
|---|---|---|---|---|---|---|
| 1 | 3개월 평균 재귀 | Baseline | 3,805,543 | 1.244 | 0.608 | 73% |
| 2 | Chronos-2 | 파운데이션 모델 | 3,945,532 | 1.284 | 0.629 | 65% |
| 3 | **TimesFM 2.5** | 파운데이션 모델 | **3,980,521** | **1.370** | **0.631** | 64% |
| 4 | Moirai 2.0 | 파운데이션 모델 | 4,058,712 | 1.393 | 0.644 | 62% |
| 5 | Naive 직접 · 재귀 | Baseline | 4,202,700 | 1.274 | 0.668 · 0.673 | 69% · 66% |
| 7 | 3개월 평균 직접 | Baseline | 4,242,903 | 1.247 | 0.645 | 74% |
| 8 | HistQuantile 직접 (기존 보고서 기준선) | Baseline | 4,393,897 | 2.329 | 0.707 | 60% |
| 9 | HistQuantile 재귀 | Baseline | 4,416,161 | 2.322 | 0.718 | 56% |
| 10 | SeasonalNaive 재귀 · 직접 | Baseline | 4,959,210 | 2.521 | 0.839 · 0.851 | 53% · 56% |
| 12 | FinCast | 파운데이션 모델 | 5,128,018 | 1.500 | 0.773 | 56% |

- MAE 합계 = 사용자별 MAE(카테고리 합, 원/월)를 4명 더한 값, MASE·WQL = 사용자별 값의 평균 (`results/comparison_overall.csv`)
- TimesFM·Chronos-2는 기존 기준선 HistQuantile보다 MAE가 약 9 ~ 10% 낮음. TimesFM은 Baseline 8가지 중 7가지보다 MAE가 낮고, 3개월 평균 재귀보다는 4.6% 높음
- 상위 FM 3개의 차이는 작음 (TimesFM vs Chronos-2 MAE 차이 0.9%, 23개 조합 1:1 비교 12승 11패)
- FinCast는 금융 시장 데이터용 모델이라 목돈을 계속 이어 가 개인 지출에서 가장 나쁨 (TabFormer 평가와 같은 결론)

### 파운데이션 모델 비교 (`results/comparison_overall.csv`)
| 모델 | HistQuantile 대비 조합 승-패 | Wilcoxon p | 최악의 경우 (사용자별 1위 대비 MASE 배율) | 재귀 쏠림 | 6개월 예측 합계 U1 / U2 / U3 / U4 (만 원) |
|---|---|---|---|---|---|
| **TimesFM 2.5** | 14-9 | **0.028** | **1.29배** | **0.29** | 693 / 465 / 176 / 909 |
| Chronos-2 | 14-9 | 0.030 | 1.38배 | 0.44 | 717 / 496 / 119 / 1,120 |
| Moirai 2.0 | 13-10 | 0.250 | 1.42배 | 0.30 | 615 / 380 / 91 / 631 |
| FinCast | 12-11 | 0.214 | 1.64배 | 0.53 | 884 / 1,133 / 1,215 / 1,389 |

- 조합 = 사용자 × 카테고리 23개, Wilcoxon 부호순위 검정(단측, MASE 기준)으로 HistQuantile보다 나은지 확인
- 재귀 쏠림 = 향후 6개월 예측의 |log(마지막 달 ÷ 첫 달)| 평균. 클수록 재귀 예측이 한 방향으로 계속 커지거나 작아짐
- 6개월 예측 합계에서 TimesFM은 4명 모두 네 모델의 가운데(2 ~ 3번째)에 있음

### TimesFM 2.5를 고른 이유
- 기존 기준선 HistQuantile보다 통계적으로 유의하게 정확함 (p = 0.028) — Moirai 2.0·FinCast는 유의하지 않음
- 정확도는 Chronos-2와 사실상 같지만, 최악의 경우 오차가 가장 작고(1.29배) 재귀 쏠림이 가장 작음
- 소비 패턴이 바뀐 사용자(U3: 작년엔 쓰다 올해 0원)에서 HistQuantile·SeasonalNaive는 MASE 5.5 ~ 5.9로 무너지지만 TimesFM은 1.72
- 일회성 목돈(U3의 2026-10 338만 원) 직후 6개월을 64만 → 15만 원으로 평소 수준에 되돌림 (FinCast는 매달 163만 ~ 224만 원으로 이어 감)
- Apache-2.0이라 상업 서비스에 사용 가능 (Moirai 2.0은 비상업)
- 상세 근거: `report/SpendRadar_TimesFM_검증보고서.docx`

### 지표
| 지표 | 정의 | 단위 |
|---|---|---|
| MAE | 실제 월 지출과 예측 중앙값(q0.5)의 평균 절대 차이. 사용자 '전체'는 6개 카테고리 합 | 원/월 |
| MASE | MAE ÷ 입력 구간에서 '지난달 값' 예측(lag 1)의 평균 오차. 1 미만이면 그보다 정확. 사용자 '전체'는 카테고리 평균 | 없음 |
| WQL | 분위수 0.1 ~ 0.9 예측의 가중 분위수 손실 (2 × Σpinball ÷ Σ\|실제\|, 분위수 평균). 사용자 '전체'는 카테고리를 합쳐서 계산 | 없음 |

- TabFormer 레포는 MASE 분모로 '작년 같은 달'(m = 12)을 쓰지만, 이 데이터는 입력이 16 ~ 28개월뿐이라 '지난달'(lag 1)을 씀 → 두 레포의 MASE 값은 직접 비교하지 않음

## 4. 폴더 구조
```
data/
  team_monthly_long.csv        4명 × 6개 카테고리 월 지출 (Baseline 레포와 동일)
src/
  spendradar_team.py           데이터 로드, 직접·재귀 예측, 지표 계산 (Baseline 레포와 공통)
notebooks/
  run_<모델>_colab.ipynb       모델별 Colab 실행 (timesfm · chronos · moirai · fincast), 사람별 표 4개 · 그래프 3개
scripts/
  1_analysis.py                모든 모델 지표 통합·비교 분석 → results/comparison_*.csv
  2_report_data.py             보고서용 수치 정리 (scripts/out/*.json)
  3_charts.py                  보고서 그림 → report/figures/
  4_build_TimesFM_report.js    보고서 → report/SpendRadar_TimesFM_검증보고서.docx
  5_build_results_xlsx.py      (선택) 결과 엑셀 → results/SpendRadar_TeamData_results.xlsx
results/
  <모델>/ALL_metrics_<모델>.csv      사용자 × 카테고리 지표 (카테고리 '전체' = 사용자 종합)
  <모델>/ALL_forecast_<모델>.csv     향후 6개월 예측 (중앙값 · 10% · 90%)
  <모델>/ALL_validation_<모델>.csv   검증 구간 실제 vs 예측 (Chronos-2는 저장되지 않음)
  baseline/                         Baseline 레포 results/의 복사본 (비교용)
  comparison_overall.csv            Baseline 포함 12개 모델 4명 종합 + FM 검정·쏠림
  comparison_by_user.csv            모델 × 사용자별 MAE · MASE · WQL · 적중률
  comparison_excl_medical.csv       '의료 및 기타'(일회성 목돈) 제외 비교
  SpendRadar_TeamData_results.xlsx  위 결과를 시트 7개로 정리 (먼저 이 파일을 보면 됨)
report/
  SpendRadar_TimesFM_검증보고서.docx  검증 보고서 (16쪽, 부록: 자료·코드 안내 / 원자료 / 모델별 지표)
  figures/                          보고서 그림
```

## 5. 실행 방법
**파운데이션 모델 (Colab T4 GPU)**: `notebooks/run_<모델>_colab.ipynb`를 Colab에서 열고 런타임 유형을 T4 GPU로 바꾼 뒤 셀을 하나씩 실행. 2번 셀이 이 레포를 받아 `data/team_monthly_long.csv`를 읽음 (레포 주소가 다르면 2번 셀의 `REPO_URL` 수정). 마지막 셀이 내려받는 `ALL_*_<모델>.csv` 3개를 `results/<모델>/`에 넣으면 됨.

**비교 분석·보고서 (CPU)**
```bash
pip install -r requirements.txt
npm install docx              # 보고서(.docx) 생성용

python scripts/1_analysis.py
python scripts/2_report_data.py
python scripts/3_charts.py
node scripts/4_build_TimesFM_report.js
python scripts/5_build_results_xlsx.py   # (선택)
```
- `results/`의 CSV만 있으면 실행됨 (GPU 불필요)
- Baseline 결과를 새로 만들었다면 Baseline 레포의 `results/ALL_*_baseline.csv` 3개를 `results/baseline/`에 복사
- 그림의 한글 글꼴: Noto Sans CJK KR 또는 나눔고딕 필요
- 검증 환경: Colab T4 (모델 실행), Python 3.13 · pandas 3.0 · Node.js 22 (분석·보고서)
- 노트북의 모델 셀(4번)과 계산 셀(5번)은 `results/`를 만든 실행과 같은 코드이고, 데이터를 엑셀 업로드 대신 이 레포의 CSV에서 읽도록만 바꿈 (CSV는 같은 전처리 결과라 입력이 같음)

## 6. 한계
- 사용자 4명, 검증 구간 한 번(2026-05 ~ 2026-10)뿐이라 결론의 일반화에는 한계가 있음 — 사용자와 검증 구간을 늘려 추가 확인 필요
- 실제 데이터에서는 3개월 평균 재귀가 평균 정확도 1위로, 파운데이션 모델의 장점은 정확도보다 안정성(최악의 경우·재귀 쏠림)에 있음
- 입력이 16 ~ 28개월로 짧아 계절성을 배우기 어려움
- U2 ~ U4는 월별 집계만 있어 본인 계좌 이체가 '의료 및 기타'에 섞였을 수 있음
- Moirai 2.0은 small 모델만 사용, 모든 모델 파인튜닝 없이 평가
