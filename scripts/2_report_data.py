"""2단계: 보고서용 수치를 JSON으로 정리 → out/*.json
실행: python scripts/2_report_data.py"""
from pathlib import Path
BASE = Path(__file__).resolve().parent
RES = BASE.parent / "results"                    # 모델 결과 CSV 폴더 (results/<모델>/ALL_*.csv)
OUT = BASE / "out"; OUT.mkdir(exist_ok=True)     # 중간 결과·그림 저장 폴더
FILES = {k: {"m": RES / d / f"ALL_metrics_{d}.csv", "f": RES / d / f"ALL_forecast_{d}.csv", "v": RES / d / f"ALL_validation_{d}.csv"}
         for k, d in [("timesfm", "timesfm"), ("chronos", "chronos"), ("moirai", "moirai"), ("fincast", "fincast"), ("base", "baseline")]}

import pandas as pd, numpy as np, json
U = ["U1", "U2", "U3", "U4"]
CATS = ['식비 / 카페', '주거 / 통신', '쇼핑 / 패션', '의료 및 기타', '교통 / 차량', '문화 / 여가']
o = pd.read_pickle(OUT / "analysis.pkl")
A, B, per = o["A"], o["B"], o["per"]
T = "TimesFM 2.5"
pct = lambda a, b: (a / b - 1) * 100
rel = {m: {"MAE": pct(A.loc[T, "MAE 합계"], A.loc[m, "MAE 합계"]), "WQL": pct(A.loc[T, "WQL 평균"], A.loc[m, "WQL 평균"]),
           "MASE": pct(A.loc[T, "MASE 평균"], A.loc[m, "MASE 평균"])} for m in A.index}
relB = {m: pct(B.loc[T, "MAE 합계"], B.loc[m, "MAE 합계"]) for m in B.index}
def df2(d): return {"index": list(map(str, d.index)), "columns": list(map(str, d.columns)),
                    "data": d.astype(object).where(d.notna(), None).values.tolist()}
J = {"A": df2(A), "B": df2(B), "C": df2(o["C"]), "D": df2(o["D"]), "E": df2(o["E"]), "jk_cat": df2(o["jk_cat"]),
     "jk_med": df2(o["jk_med"]), "per_mae": df2(per["MAE(원/월)"]), "per_mase": df2(per["MASE"]), "per_wql": df2(per["WQL"]),
     "per_cov": df2(per["예상범위 적중률"]), "B_mae": df2(o["B_mae"]), "med_share": df2(o["med_share"]), "G": df2(o["G"]), "rel": rel, "relB": relB}
json.dump(J, open(OUT / "data.json", "w"), ensure_ascii=False, indent=1, default=float)

# 향후 6개월 예측 (TimesFM 카테고리 상세 + 파운데이션 모델 4종 월 합계)
f = {k: pd.read_csv(FILES[k]["f"]) for k in ["timesfm", "chronos", "moirai", "fincast"]}
V = pd.read_csv(FILES["timesfm"]["v"])
tot = {k: d.groupby(["사용자", "월"])["예측"].sum().unstack() for k, d in f.items()}
act = V.groupby(["사용자", "월"])["실제"].sum().unstack()
t = f["timesfm"]
fu = {"months": list(tot["timesfm"].columns), "vmonths": list(act.columns),
      "tot": {k: {u: v.loc[u].round().tolist() for u in U} for k, v in tot.items()},
      "act": {u: act.loc[u].round().tolist() for u in U},
      "cat": {u: {c: t[(t.사용자 == u) & (t.카테고리 == c)].sort_values("월")[["예측", "하한(10%)", "상한(90%)"]].values.tolist() for c in CATS} for u in U},
      "catact": {u: {c: V[(V.사용자 == u) & (V.카테고리 == c)].sort_values("월")["실제"].tolist() for c in CATS} for u in U}}
fu["valact"] = {u: {c: V[(V.사용자 == u) & (V.카테고리 == c)].sort_values("월")["실제"].tolist() for c in CATS} for u in U}
json.dump(fu, open(OUT / "future.json", "w"), ensure_ascii=False)

# 모든 모델(파운데이션 4종 + 기준선 6가지) 6개월 예측 — Naive·Seasonal Naive는 직접·재귀가 같아 직접만
NAME = {"timesfm(재귀)": "TimesFM 2.5", "chronos(재귀)": "Chronos-2", "moirai(재귀)": "Moirai 2.0", "fincast(재귀)": "FinCast", "baseline(직접)": "HistQuantile 직접",
        "baseline(재귀)": "HistQuantile 재귀", "naive(직접)": "Naive", "snaive(직접)": "Seasonal Naive", "ma3(직접)": "3개월 평균 직접", "ma3(재귀)": "3개월 평균 재귀"}
F = pd.concat([pd.read_csv(FILES[k]["f"]) for k in ["timesfm", "chronos", "moirai", "fincast", "base"]])
F = F[F.모델.isin(NAME)]; F["모델"] = F.모델.map(NAME)
ORDER = list(NAME.values()); months = sorted(F.월.unique())
mon = F.groupby(["사용자", "모델", "월"])["예측"].sum(); catsum = F.groupby(["사용자", "모델", "카테고리"])["예측"].sum()
fa = {"order": ORDER, "months": months, "mon": {u: {m: [float(mon[(u, m, mm)]) for mm in months] for m in ORDER} for u in U},
      "cat": {u: {c: [float(catsum[(u, m, c)]) for m in ORDER] for c in CATS} for u in U}}
json.dump(fa, open(OUT / "future_all.json", "w"), ensure_ascii=False)
print("저장:", OUT / "data.json", OUT / "future.json", OUT / "future_all.json")
