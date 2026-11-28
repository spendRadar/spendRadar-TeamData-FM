"""2단계: 비교 그림 → report/figures/*.png (모두 직접 방식)   (한글 글꼴: Noto Sans CJK KR 또는 나눔고딕)
실행: python scripts/2_charts.py   (1단계 결과 필요)

  1_모델별_MAE_WQL.png           8개 모델 종합 MAE 합계 · WQL (파운데이션 모델 = 색, Baseline = 회색)
  2_모델별_예상범위_적중률.png    10~90% 범위 적중률 (목표 80%)
  3_월총지출_검증_TimesFM_vs_HistQuantile.png   사용자별 '전체' 시계열: 실제 + 검증 6개월 예측·범위
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parents[1]
RES, FIG = ROOT / "results", ROOT / "report" / "figures"
FIG.mkdir(parents=True, exist_ok=True)
for name in ["Noto Sans CJK KR", "NanumGothic", "Malgun Gothic"]:
    if any(name in f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = name; break
plt.rcParams["axes.unicode_minus"] = False
COL0 = {"TimesFM 2.5": "#2a78d6", "Chronos-2": "#eb6834", "Moirai 2.0": "#1baf7a", "FinCast": "#b8399e"}
# 파운데이션 모델: 모델별 색 / Baseline: 회색
COL = COL0
GRAY, INK = "#9aa0a6", "#3c4043"

ov = pd.read_csv(RES / "comparison_overall.csv", index_col=0)
c = [COL.get(m, GRAY) for m in ov.index]

# 그림 1: MAE · WQL
fig, ax = plt.subplots(1, 2, figsize=(12, 4.6), sharey=True)
y = range(len(ov))[::-1]
for a, col, title, fmt in [(ax[0], "MAE 합계(원/월)", "MAE 합계 (만 원/월, 3명)", lambda v: f"{v/1e4:,.1f}"),
                           (ax[1], "WQL 평균", "WQL 평균", lambda v: f"{v:.3f}")]:
    v = ov[col] / (1e4 if "MAE" in col else 1)
    a.barh(list(y), v, color=c, height=0.7)
    for yy, vv, raw in zip(y, v, ov[col]):
        a.text(vv, yy, " " + fmt(raw), va="center", fontsize=8, color=INK)
    a.set_title(title, fontsize=11, color=INK); a.spines[["top", "right"]].set_visible(False)
    a.grid(axis="x", alpha=.25); a.set_xlim(0, v.max() * 1.18)
ax[0].set_yticks(list(y)); ax[0].set_yticklabels(ov.index, fontsize=9)
fig.suptitle("그림 1. 검증 6개월(2026-05 ~ 10) 종합 오차 — 낮을수록 좋음 (색 = 파운데이션 모델, 회색 = Baseline)", fontsize=11)
plt.tight_layout(); plt.savefig(FIG / "1_모델별_MAE_WQL.png", dpi=170); plt.close()

# 그림 2: 적중률
fig, a = plt.subplots(figsize=(9, 4.4))
cov = ov["10~90% 적중률"] * 100
a.bar(range(len(ov)), cov, color=c, width=0.7)
a.axhline(80, color=INK, lw=1, ls="--"); a.text(-0.4, 101, "점선 = 목표 80%", ha="left", va="top", fontsize=8.5, color=INK)
for x, v in enumerate(cov): a.text(x, v + 1, f"{v:.0f}%", ha="center", fontsize=8, color=INK, bbox=dict(facecolor="white", edgecolor="none", pad=1))   # 흰 배경: 목표선과 겹쳐도 읽히게
a.set_xticks(range(len(ov))); a.set_xticklabels(ov.index, rotation=35, ha="right", fontsize=8.5)
a.set_ylim(0, 105); a.set_ylabel("%"); a.spines[["top", "right"]].set_visible(False); a.grid(axis="y", alpha=.25)
a.set_title("그림 2. 10 ~ 90% 예상 범위 적중률 — 80%에 가까울수록 범위가 정확함", fontsize=11)
plt.tight_layout(); plt.savefig(FIG / "2_모델별_예상범위_적중률.png", dpi=170); plt.close()

# 그림 3: 사용자별 월 총지출 (전체 시계열) 검증
L = pd.read_csv(ROOT / "data" / "team_monthly_long.csv"); L = L[L.category == "전체"]
V = pd.concat([pd.read_csv(RES / "timesfm" / "ALL_validation_timesfm.csv").query("모델 == 'timesfm(직접)'").assign(이름="TimesFM 2.5"),
               pd.read_csv(RES / "baseline" / "ALL_validation_baseline.csv").query("모델 == 'baseline(직접)'").assign(이름="HistQuantile")])
V = V[V.카테고리 == "전체"]
users = sorted(L.entity_id.unique())
fig, axes = plt.subplots(1, len(users), figsize=(15, 4.4))
for a, u in zip(axes, users):
    h = L[L.entity_id == u]; x = pd.to_datetime(h.ds)
    a.plot(x, h.y / 1e4, color="black", lw=1.4, label="실제")
    for nm, colr in [("TimesFM 2.5", COL0["TimesFM 2.5"]), ("HistQuantile", GRAY)]:
        v = V[(V.사용자 == u) & (V.이름 == nm)]; xv = pd.to_datetime(v.월 + "-01")
        a.plot(xv, v.예측 / 1e4, "--o", ms=3, color=colr, lw=1.6, label=f"{nm} 예측")
        a.fill_between(xv, v["하한(10%)"] / 1e4, v["상한(90%)"] / 1e4, color=colr, alpha=.15)
    a.axvspan(pd.Timestamp("2026-05-01"), pd.Timestamp("2026-10-01"), color="#f1f3f5", zorder=0)
    a.set_title(u, fontsize=11); a.set_ylabel("만 원"); a.tick_params(axis="x", labelrotation=45, labelsize=8)
    a.spines[["top", "right"]].set_visible(False)
axes[0].legend(fontsize=8, loc="upper left")
fig.suptitle("그림 3. 월 총지출('전체' 시계열) — 실제와 검증 6개월 예측 (음영 = 10 ~ 90% 범위, 회색 배경 = 검증 구간)", fontsize=11)
plt.tight_layout(); plt.savefig(FIG / "3_월총지출_검증_TimesFM_vs_HistQuantile.png", dpi=170); plt.close()
print("저장:", FIG)
