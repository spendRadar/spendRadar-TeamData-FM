"""1단계: 파운데이션 모델 4종 + Baseline 4종 결과 비교 (모두 직접 방식: 한 번에 6개월) → results/comparison_*.csv
실행: python scripts/1_compare.py   (results/<모델>/ALL_*.csv 필요)

  comparison_overall.csv    모델(× 방식)별 종합 (카테고리 6개 기준 MAE 합계 · MASE · WQL · 적중률 + 전체 시계열 + 최악 배율)
  comparison_by_user.csv    모델 × 사용자별 MAE · MASE · WQL · 적중률 (카테고리 '종합')
  comparison_by_series.csv  모델 × 시계열(사용자 × 카테고리)별 MASE
  comparison_tests.csv      FM × Baseline 1:1 비교 (시계열별 MASE 승-패, Wilcoxon 부호순위 단측 p)
  comparison_forecast_total.csv  모델 × 사용자별 향후 6개월 예측 합계 ('전체' 시계열, 원)
"""
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
DIRS = ["timesfm", "chronos", "moirai", "fincast", "baseline"]
NAME = {"timesfm(직접)": "TimesFM 2.5", "chronos(직접)": "Chronos-2", "moirai(직접)": "Moirai 2.0", "fincast(직접)": "FinCast",
        "baseline(직접)": "HistQuantile", "naive(직접)": "Naive", "snaive(직접)": "SeasonalNaive", "ma3(직접)": "3개월 평균"}   # 직접 방식만 사용
FM = ["TimesFM 2.5", "Chronos-2", "Moirai 2.0", "FinCast"]


def load(kind):
    d = pd.concat([pd.read_csv(RES / k / f"ALL_{kind}_{k}.csv") for k in DIRS if (RES / k / f"ALL_{kind}_{k}.csv").exists()],
                  ignore_index=True)
    d = d[d["모델"].isin(NAME)].copy()              # 직접 방식 결과만
    d["모델"] = d["모델"].map(NAME)
    return d


M, F = load("metrics"), load("forecast")
tot = M[M.카테고리 == "종합"]            # 사용자 종합 (카테고리 6개 기준)
ent = M[M.카테고리 == "전체"]            # 월 총지출 시계열
per = tot.pivot(index="모델", columns="사용자", values="MASE")

ov = pd.DataFrame({
    "구분": ["파운데이션 모델" if m in FM else "Baseline" for m in tot.모델.unique()]}, index=tot.모델.unique())
ov["MAE 합계(원/월)"] = tot.groupby("모델")["MAE(원/월)"].sum()
ov["MASE 평균"] = tot.groupby("모델")["MASE"].mean()
ov["WQL 평균"] = tot.groupby("모델")["WQL"].mean()
ov["10~90% 적중률"] = tot.groupby("모델")["예상범위 적중률"].mean()
ov["전체 시계열 MAE(원/월)"] = ent.groupby("모델")["MAE(원/월)"].mean()
ov["전체 시계열 WQL"] = ent.groupby("모델")["WQL"].mean()
ov["최악 배율(사용자별 1위 MASE 대비)"] = (per / per.min()).max(axis=1)
ov = ov.sort_values("MAE 합계(원/월)"); ov.insert(1, "MAE 순위", range(1, len(ov) + 1)); ov.index.name = "모델"
ov.round(6).to_csv(RES / "comparison_overall.csv", encoding="utf-8-sig")

byu = tot.set_index(["모델", "사용자"])[["MAE(원/월)", "MASE", "WQL", "예상범위 적중률"]].unstack("사용자")
byu.columns = [f"{a}_{b}" for a, b in byu.columns]
byu.loc[ov.index].round(6).to_csv(RES / "comparison_by_user.csv", encoding="utf-8-sig")

ser = M[~M.카테고리.isin(["종합", "전체"])].pivot_table(index=["사용자", "카테고리"], columns="모델", values="MASE")
ser[ov.index].round(6).to_csv(RES / "comparison_by_series.csv", encoding="utf-8-sig")

s = ser.dropna()
rows = []
for f in FM:
    for b in ["HistQuantile", "Naive", "3개월 평균", "SeasonalNaive"]:
        d = s[f] - s[b]
        rows.append({"파운데이션 모델": f, "비교 대상": b, "시계열 수": len(d), "승": int((d < 0).sum()), "패": int((d > 0).sum()),
                     "Wilcoxon p (FM이 더 좋음)": wilcoxon(d, alternative="less").pvalue})
pd.DataFrame(rows).round(6).to_csv(RES / "comparison_tests.csv", index=False, encoding="utf-8-sig")

ft = F[F.카테고리 == "전체"].groupby(["모델", "사용자"])["예측"].sum().unstack()
ft.loc[ov.index].round(0).astype(int).to_csv(RES / "comparison_forecast_total.csv", encoding="utf-8-sig")

pd.set_option("display.width", 200)
print(ov.round(3).to_string()); print(); print(pd.DataFrame(rows).round(3).to_string(index=False))
print("\n저장: results/comparison_overall · by_user · by_series · tests · forecast_total .csv")
