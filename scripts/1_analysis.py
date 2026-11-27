"""1단계: 모든 모델의 지표를 모아 비교 분석 → out/analysis.pkl
실행: python scripts/1_analysis.py"""
from pathlib import Path
BASE = Path(__file__).resolve().parent
RES = BASE.parent / "results"                    # 모델 결과 CSV 폴더 (results/<모델>/ALL_*.csv)
OUT = BASE / "out"; OUT.mkdir(exist_ok=True)     # 중간 결과·그림 저장 폴더
FILES = {k: {"m": RES / d / f"ALL_metrics_{d}.csv", "f": RES / d / f"ALL_forecast_{d}.csv", "v": RES / d / f"ALL_validation_{d}.csv"}
         for k, d in [("timesfm", "timesfm"), ("chronos", "chronos"), ("moirai", "moirai"), ("fincast", "fincast"), ("base", "baseline")]}
import pandas as pd, numpy as np, json
from scipy.stats import wilcoxon

U = ["U1", "U2", "U3", "U4"]
CATS = ['식비 / 카페', '주거 / 통신', '쇼핑 / 패션', '의료 및 기타', '교통 / 차량', '문화 / 여가']
M = pd.concat([pd.read_csv(FILES[k]["m"]) for k in ["timesfm", "chronos", "moirai", "fincast", "base"]], ignore_index=True)
F = pd.concat([pd.read_csv(FILES[k]["f"]) for k in ["timesfm", "chronos", "moirai", "fincast", "base"]], ignore_index=True)
V = pd.read_csv(FILES["timesfm"]["v"])
NAME = {"timesfm(재귀)": "TimesFM 2.5", "chronos(재귀)": "Chronos-2", "moirai(재귀)": "Moirai 2.0", "fincast(재귀)": "FinCast",
        "baseline(직접)": "HistQuantile 직접", "baseline(재귀)": "HistQuantile 재귀",
        "naive(직접)": "Naive 직접", "naive(재귀)": "Naive 재귀", "snaive(직접)": "Seasonal Naive 직접",
        "snaive(재귀)": "Seasonal Naive 재귀", "ma3(직접)": "3개월 평균 직접", "ma3(재귀)": "3개월 평균 재귀"}
M["모델"] = M["모델"].map(NAME); F["모델"] = F["모델"].map(NAME)
FM = ["TimesFM 2.5", "Chronos-2", "Moirai 2.0", "FinCast"]
BL = [n for n in NAME.values() if n not in FM]
out = {}

# 검증 구간 실제 합계 (WQL 재가중용)
ysum = V.groupby(["사용자", "카테고리"])["실제"].apply(lambda s: s.abs().sum())

tot = M[M.카테고리 == "전체"]
# A. 종합
A = pd.DataFrame({
    "MAE 합계": tot.pivot(index="모델", columns="사용자", values="MAE(원/월)")[U].sum(axis=1),
    "MASE 평균": tot.pivot(index="모델", columns="사용자", values="MASE")[U].mean(axis=1),
    "WQL 평균": tot.pivot(index="모델", columns="사용자", values="WQL")[U].mean(axis=1),
    "적중률 평균": tot.pivot(index="모델", columns="사용자", values="예상범위 적중률")[U].mean(axis=1),
}).sort_values("MAE 합계")
for k in ["MAE 합계", "MASE 평균", "WQL 평균"]:
    A[k + " 순위"] = A[k].rank().astype(int)
out["A"] = A
per = {k: tot.pivot(index="모델", columns="사용자", values=k)[U] for k in ["MAE(원/월)", "MASE", "WQL", "예상범위 적중률"]}
out["per"] = per

# B. 의료 및 기타 제외
cat = M[(M.카테고리 != "전체")].copy()
cat["ysum"] = [ysum.get((u, c), np.nan) for u, c in zip(cat.사용자, cat.카테고리)]
ex = cat[cat.카테고리 != "의료 및 기타"]
B_mae = ex.pivot_table(index="모델", columns="사용자", values="MAE(원/월)", aggfunc="sum")[U]
B_mase = ex.pivot_table(index="모델", columns="사용자", values="MASE", aggfunc="mean")[U]
w = ex[(ex.ysum > 0) & ex.WQL.notna()].copy(); w["pin2"] = w.WQL * w.ysum
B_wql = (w.groupby(["모델", "사용자"]).pin2.sum() / w.groupby(["모델", "사용자"]).ysum.sum()).unstack()[U]
B = pd.DataFrame({"MAE 합계": B_mae.sum(axis=1), "MASE 평균": B_mase.mean(axis=1), "WQL 평균": B_wql.mean(axis=1)}).sort_values("MAE 합계")
for k in ["MAE 합계", "MASE 평균", "WQL 평균"]:
    B[k + " 순위"] = B[k].rank().astype(int)
out["B"] = B; out["B_mae"] = B_mae; out["B_mase"] = B_mase
# 의료 비중
med = cat[cat.카테고리 == "의료 및 기타"].pivot(index="모델", columns="사용자", values="MAE(원/월)")[U]
out["med_share"] = (med / per["MAE(원/월)"]).loc[["TimesFM 2.5", "HistQuantile 직접", "3개월 평균 재귀"]]

# C. 조합(사용자×카테고리) 단위 1:1 비교: TimesFM vs 각 기준선 / 다른 FM
cm = cat[cat.MASE.notna()]
P = cm.pivot_table(index=["사용자", "카테고리"], columns="모델", values="MASE")
Pmae = cm.pivot_table(index=["사용자", "카테고리"], columns="모델", values="MAE(원/월)")
rows = []
for b in BL + ["Chronos-2", "Moirai 2.0", "FinCast"]:
    d = P[b] - P["TimesFM 2.5"]           # 양수 = TimesFM이 나음
    win = int((Pmae["TimesFM 2.5"] < Pmae[b]).sum()); lose = int((Pmae["TimesFM 2.5"] > Pmae[b]).sum())
    nz = d[d.abs() > 1e-12]
    p = wilcoxon(nz, alternative="greater").pvalue if len(nz) > 5 else np.nan
    rows.append({"비교 대상": b, "TimesFM 승": win, "TimesFM 패": lose, "동률": len(d) - win - lose,
                 "MASE 차이 중앙값": float(np.median(d)), "Wilcoxon p (TimesFM이 나음)": p})
C = pd.DataFrame(rows).set_index("비교 대상")
out["C"] = C; out["n_combo"] = len(P)

# D. 안정성: 사람별 최고 대비 배율 (MASE) 과 최악 MASE
mase = per["MASE"]
D = pd.DataFrame({"최악 MASE": mase.max(axis=1), "최악 사용자": mase.idxmax(axis=1),
                  "사람별 1위 대비 최대 배율": (mase / mase.min()).max(axis=1),
                  "MASE 1.8 초과 사용자 수": (mase > 1.8).sum(axis=1)}).sort_values("사람별 1위 대비 최대 배율")
out["D"] = D

# E. 6개월 예측 합리성
E = F.groupby(["모델", "사용자"])["예측"].sum().unstack()[U]
out["E"] = E
jk = F[(F.사용자 == "U3") & (F.카테고리 == "의료 및 기타")].pivot(index="모델", columns="월", values="예측")
out["jk_med"] = jk
# 최근 6개월(검증 구간) 실제 월 총지출 평균
recent = V.groupby(["사용자", "월"])["실제"].sum().groupby("사용자").agg(["mean", "median"])
out["recent"] = recent
# U3 의료 검증구간 실제
out["jk_val"] = V[(V.사용자 == "U3") & (V.카테고리 == "의료 및 기타")][["월", "실제"]]

# F. 패턴 변화 (U3 카테고리별)
Fk = cat[cat.사용자 == "U3"].pivot(index="카테고리", columns="모델", values="MAE(원/월)").reindex(CATS)[
    ["TimesFM 2.5", "HistQuantile 직접", "Seasonal Naive 직접", "3개월 평균 재귀"]]
out["jk_cat"] = Fk

# G. 파운데이션 모델 4종: HistQuantile 대비 조합 검정 + 재귀 쏠림(향후 6개월 4월/11월 비율의 |log| 평균)
G = []
for fm in FM:
    d = P["HistQuantile 직접"] - P[fm]; d = d[d.abs() > 1e-12]
    g = F[F.모델 == fm].pivot_table(index=["사용자", "카테고리"], columns="월", values="예측")
    g = g[(g > 1000).all(axis=1)]
    G.append({"모델": fm, "HQ 대비 승": int((Pmae[fm] < Pmae["HistQuantile 직접"]).sum()),
              "HQ 대비 패": int((Pmae[fm] > Pmae["HistQuantile 직접"]).sum()),
              "HQ 대비 p": wilcoxon(d, alternative="greater").pvalue,
              "재귀 쏠림": float(np.log(g.iloc[:, -1] / g.iloc[:, 0]).abs().mean())})
out["G"] = pd.DataFrame(G).set_index("모델")

pd.to_pickle(out, OUT / "analysis.pkl")

# 비교표 CSV → results/ (TabFormer FM 레포의 comparison_*.csv와 같은 역할)
cmp = A.copy(); cmp.insert(0, "구분", ["파운데이션 모델" if m in FM else "Baseline" for m in cmp.index])
cmp = cmp.join(out["G"]); cmp.index.name = "모델"
cmp.round(4).to_csv(RES / "comparison_overall.csv", encoding="utf-8-sig")
byu = pd.concat({k: v for k, v in per.items()}, axis=1)
byu.columns = [f"{k}_{u}" for k, u in byu.columns]; byu = byu.loc[A.index]; byu.index.name = "모델"
byu.round(4).to_csv(RES / "comparison_by_user.csv", encoding="utf-8-sig")
out["B"].round(4).rename_axis("모델").to_csv(RES / "comparison_excl_medical.csv", encoding="utf-8-sig")
print("저장:", RES / "comparison_overall.csv", "· comparison_by_user.csv · comparison_excl_medical.csv")
pd.set_option("display.width", 250); pd.set_option("display.float_format", lambda v: f"{v:,.3f}")
for k, v in out.items():
    print(f"\n===== {k}"); print(v.to_string() if hasattr(v, "to_string") else v)
