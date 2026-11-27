"""3단계: 보고서 그림 생성 → scripts/out/*.png, report/figures/  (한글 글꼴: Noto Sans CJK KR 또는 나눔고딕 필요)
실행: python scripts/3_charts.py"""
from pathlib import Path
BASE = Path(__file__).resolve().parent
RES = BASE.parent / "results"                    # 모델 결과 CSV 폴더 (results/<모델>/ALL_*.csv)
OUT = BASE / "out"; OUT.mkdir(exist_ok=True)     # 중간 결과·그림 저장 폴더
FILES = {k: {"m": RES / d / f"ALL_metrics_{d}.csv", "f": RES / d / f"ALL_forecast_{d}.csv", "v": RES / d / f"ALL_validation_{d}.csv"}
         for k, d in [("timesfm", "timesfm"), ("chronos", "chronos"), ("moirai", "moirai"), ("fincast", "fincast"), ("base", "baseline")]}
import pandas as pd, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager, rcParams

for f in font_manager.findSystemFonts():
    if "NotoSansCJK-Regular" in f:
        font_manager.fontManager.addfont(f)
rcParams["font.family"] = "Noto Sans CJK JP"
for f in font_manager.fontManager.ttflist:
    if "Sans CJK KR" in f.name:
        rcParams["font.family"] = f.name; break
rcParams.update({"axes.unicode_minus": False, "axes.spines.top": False, "axes.spines.right": False,
                 "axes.edgecolor": "#c3c2b7", "axes.labelcolor": "#52514e", "xtick.color": "#52514e",
                 "ytick.color": "#0b0b0b", "font.size": 10})
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e6e5e0"
COL = {"TimesFM 2.5": "#2a78d6", "Chronos-2": "#eb6834", "Moirai 2.0": "#1baf7a", "FinCast": "#b8399e"}
GRAY, GRAY_HQ = "#b9b8b2", "#6f6e69"
o = pd.read_pickle(OUT / "analysis.pkl")
U = ["U1", "U2", "U3", "U4"]


def colour(n):
    return COL.get(n, GRAY_HQ if n.startswith("HistQuantile 직접") else GRAY)


def hbar(series, title, fname, ref="HistQuantile 직접", unit=1e4, fmt="{:,.0f}만"):
    s = series.sort_values(ascending=False) / unit
    fig, ax = plt.subplots(figsize=(8.2, 4.6), dpi=200)
    y = np.arange(len(s))
    ax.barh(y, s.values, height=0.62, color=[colour(n) for n in s.index], edgecolor="white", linewidth=2)
    for i, (n, v) in enumerate(s.items()):
        ax.text(v + s.max() * .01, i, fmt.format(v), va="center", fontsize=9, color=INK,
                fontweight="bold" if n in COL else "normal")
    ax.set_yticks(y); ax.set_yticklabels(s.index)
    for lab in ax.get_yticklabels():
        if lab.get_text() in COL: lab.set_fontweight("bold")
    ax.axvline(s[ref], color=GRAY_HQ, ls=(0, (3, 3)), lw=1)
    ax.text(s[ref], len(s) - .35, " 보고서 기준선", color=INK2, fontsize=8, va="bottom")
    ax.grid(axis="x", color=GRID, lw=.8); ax.set_axisbelow(True)
    ax.set_xlim(0, s.max() * 1.15); ax.set_xlabel("만 원 (낮을수록 정확)")
    ax.set_title(title, loc="left", fontsize=11.5, color=INK, pad=10)
    plt.tight_layout(); plt.savefig(fname, bbox_inches="tight"); plt.close()


hbar(o["A"]["MAE 합계"], "참고. 4명 합계 MAE — 파운데이션 모델 4종 vs 기준선 8가지", OUT / "fig1.png")

# 보고서 그림 1 (fig3.png): 사용자별 MASE — TimesFM vs 주요 기준선
mase = o["per"]["MASE"]
models = ["TimesFM 2.5", "HistQuantile 직접", "Seasonal Naive 직접", "3개월 평균 재귀"]
mc = {"TimesFM 2.5": "#2a78d6", "HistQuantile 직접": "#6f6e69", "Seasonal Naive 직접": "#eda100", "3개월 평균 재귀": "#6250d6"}
fig, ax = plt.subplots(figsize=(8.2, 4.2), dpi=200)
x = np.arange(len(U)); w = 0.2
for j, m in enumerate(models):
    v = mase.loc[m, U].values
    b = ax.bar(x + (j - 1.5) * w, v, w * 0.9, color=mc[m], label=m, edgecolor="white", linewidth=1.5)
    for xi, vi in zip(x + (j - 1.5) * w, v):
        ax.text(xi, vi + 0.06, f"{vi:.2f}", ha="center", fontsize=7.5, color=INK)
ax.axhline(1, color="#e34948", ls=(0, (3, 3)), lw=1)
ax.text(len(U) - 0.5, 1.0, " MASE 1.0", color=INK2, fontsize=8, ha="left", va="center", bbox=dict(fc="white", ec="none", pad=1)); ax.set_xlim(-0.5, len(U) - 0.5 + 0.45)
ax.set_xticks(x); ax.set_xticklabels(U); ax.set_ylabel("MASE (낮을수록 정확)")
ax.grid(axis="y", color=GRID, lw=.8); ax.set_axisbelow(True); ax.set_ylim(0, 6.6)
ax.legend(frameon=False, ncol=4, fontsize=8.5, loc="upper left")
ax.set_title("그림 1. 사용자별 MASE — 기준선은 U3(소비 패턴 변화)에서 크게 무너짐", loc="left", fontsize=11.5, pad=10)
plt.tight_layout(); plt.savefig(OUT / "fig3.png", bbox_inches="tight"); plt.close()

# 보고서 그림 2 (fig4.png): U3 의료 및 기타 — 목돈 직후 6개월 예측
jk = o["jk_med"]; val = o["jk_val"]
fig, ax = plt.subplots(figsize=(8.2, 4.3), dpi=200)
months_v = list(val["월"]); months_f = list(jk.columns)
allm = months_v + months_f; xi = {m: i for i, m in enumerate(allm)}
ax.plot([xi[m] for m in months_v], val["실제"] / 1e4, color=INK, lw=2, marker="o", ms=4, label="실제 (검증 구간)")
lines = {"FinCast": ("#b8399e", "FinCast"), "Naive 직접": ("#e34948", "지난달 값 (Naive)"), "3개월 평균 재귀": ("#6250d6", "3개월 평균 재귀 (검증 1위)"),
         "TimesFM 2.5": ("#2a78d6", "TimesFM 2.5"), "HistQuantile 직접": ("#6f6e69", "HistQuantile (보고서 기준선)")}
for m, (c, lab) in lines.items():
    yv = np.r_[val["실제"].iloc[-1], jk.loc[m].values] / 1e4
    ax.plot([xi[months_v[-1]]] + [xi[k] for k in months_f], yv, color=c, lw=2, marker="o", ms=4,
            ls="-" if m == "TimesFM 2.5" else (0, (4, 2)), label=lab)
    dy = {"TimesFM 2.5": 9, "HistQuantile 직접": -9}.get(m, 0)
    ax.text(len(allm) - 1 + .15, jk.loc[m].values[-1] / 1e4 + dy, f"{jk.loc[m].sum()/1e4:,.0f}만", color=INK, fontsize=8, va="center")
ax.axvspan(len(months_v) - .5, len(allm) - .5, color="#f1f3f5", zorder=0)
ax.text(len(months_v) - .3, 355, "향후 6개월 예측 →  (오른쪽 숫자 = 6개월 합계)", fontsize=8, color=INK2)
ax.set_xticks(range(len(allm))); ax.set_xticklabels(allm, rotation=40, fontsize=8)
ax.set_ylabel("만 원"); ax.grid(axis="y", color=GRID, lw=.8); ax.set_axisbelow(True)
ax.set_xlim(-.3, len(allm) + .6)
ax.legend(frameon=False, fontsize=8, loc="center left")
ax.set_title("그림 2. U3 '의료 및 기타' — 10월 338만 원 일회성 지출 직후의 6개월 예측", loc="left", fontsize=11.5, pad=10)
plt.tight_layout(); plt.savefig(OUT / "fig4.png", bbox_inches="tight"); plt.close()

# 보고서 그림 4 (fig5.png): 4명 월 총지출 — 최근 6개월 실제 + 향후 6개월 예측 (FM 4종)
import json
fu = json.load(open(OUT / "future.json"))
fig, axes = plt.subplots(2, 2, figsize=(8.4, 5.6), dpi=200)
vm, fm = fu["vmonths"], fu["months"]; allm = vm + fm
for ax, u in zip(axes.flat, U):
    xa = range(len(vm)); xf = range(len(vm), len(allm))
    ax.plot(list(xa), np.array(fu["act"][u]) / 1e4, color=INK, lw=1.8, marker="o", ms=3, label="실제 (검증 구간)")
    for k, c, ls, lab in [("fincast", "#b8399e", (0, (3, 2)), "FinCast"), ("chronos", "#eb6834", (0, (3, 2)), "Chronos-2"), ("moirai", "#1baf7a", (0, (3, 2)), "Moirai 2.0"),
                          ("timesfm", "#2a78d6", "-", "TimesFM 2.5")]:
        y = np.array(fu["tot"][k][u]) / 1e4
        ax.plot([len(vm) - 1] + list(xf), np.r_[fu["act"][u][-1] / 1e4, y], color=c, ls=ls, lw=2 if k == "timesfm" else 1.3,
                marker="o", ms=3 if k == "timesfm" else 2, label=lab)
    ax.axvspan(len(vm) - .5, len(allm) - .5, color="#f1f3f5", zorder=0)
    s = sum(fu["tot"]["timesfm"][u])
    ax.set_title(f"{u}  ·  TimesFM 6개월 합계 {s/1e4:,.0f}만 원", fontsize=9.5, loc="left")
    ax.set_xticks(range(len(allm))); ax.set_xticklabels([m[2:] for m in allm], rotation=50, fontsize=6.5)
    ax.grid(axis="y", color=GRID, lw=.7); ax.set_axisbelow(True); ax.tick_params(axis="y", labelsize=7)
    ax.set_ylim(bottom=0)
axes[0, 0].set_ylabel("만 원", fontsize=8); axes[1, 0].set_ylabel("만 원", fontsize=8)
h, l = axes[0, 0].get_legend_handles_labels()
fig.legend(h, l, loc="lower center", ncol=5, frameon=False, fontsize=8, bbox_to_anchor=(0.5, -0.01))
fig.suptitle("그림 4. 월 총지출 — 최근 6개월 실제와 향후 6개월 재귀 예측 (회색 배경 = 예측, 사용자마다 세로축 다름)", fontsize=10.5, x=0.02, ha="left")
plt.tight_layout(rect=(0, 0.04, 1, 0.97)); plt.savefig(OUT / "fig5.png", bbox_inches="tight"); plt.close()

# 참고 그림 (fig6.png): 사용자별 6개월 예측 합계 — 모든 모델
fa = json.load(open(OUT / "future_all.json"))
order = fa["order"]
fig, axes = plt.subplots(2, 2, figsize=(8.4, 6.2), dpi=200)
for ax, u in zip(axes.flat, U):
    tot = [sum(fa["mon"][u][m]) / 1e4 for m in order]
    y = np.arange(len(order))[::-1]
    ax.barh(y, tot, height=.62, color=[colour(m) for m in order], edgecolor="white", linewidth=1.5)
    for yi, v, m in zip(y, tot, order):
        ax.text(v + max(tot) * .015, yi, f"{v:,.0f}", va="center", fontsize=7, color=INK, fontweight="bold" if m in COL else "normal")
    ax.set_yticks(y); ax.set_yticklabels(order, fontsize=7)
    for lab in ax.get_yticklabels():
        if lab.get_text() in COL: lab.set_fontweight("bold")
    ax.set_xlim(0, max(tot) * 1.18); ax.tick_params(axis="x", labelsize=7)
    ax.grid(axis="x", color=GRID, lw=.7); ax.set_axisbelow(True)
    ax.set_title(u, loc="left", fontsize=10)
fig.suptitle("참고. 향후 6개월 예측 합계 — 모델별 (만 원, 사용자마다 가로축 다름)", fontsize=10.5, x=0.02, ha="left")
plt.tight_layout(rect=(0, 0, 1, 0.96)); plt.savefig(OUT / "fig6.png", bbox_inches="tight"); plt.close()

# 보고서 그림 3 (f7.png): 재귀 6개월 경로 — 파운데이션 모델 4종
ff = {k: pd.read_csv(FILES[k]["f"]) for k in ["timesfm", "chronos", "moirai", "fincast"]}
lab = {"timesfm": "TimesFM 2.5", "chronos": "Chronos-2", "moirai": "Moirai 2.0", "fincast": "FinCast"}
cc = {"timesfm": "#2a78d6", "chronos": "#eb6834", "moirai": "#1baf7a", "fincast": "#b8399e"}
fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.5), dpi=200)
for ax, (u, c, unit) in zip(axes, [("U4", "의료 및 기타", 1e4), ("U3", "식비 / 카페", 1e4), ("U3", "문화 / 여가", 1e4)]):
    for k, f in ff.items():
        g = f[(f.사용자 == u) & (f.카테고리 == c)].sort_values("월")
        y = g["예측"].values / unit
        ax.plot(range(6), y, color=cc[k], lw=2.2 if k == "timesfm" else 1.5, marker="o", ms=3.5, label=lab[k],
                ls="-" if k == "timesfm" else (0, (3, 2)))
        if y[0] * unit >= 1000:
            ax.text(5.12, y[-1], f"×{y[-1]/y[0]:.1f}", fontsize=7.5, va="center", color=INK)
    ax.set_xticks(range(6)); ax.set_xticklabels([m[2:] for m in g["월"]], fontsize=7.5)
    ax.set_title(f"{u} · {c}", loc="left", fontsize=9.5); ax.set_ylabel("만 원", fontsize=8)
    ax.grid(axis="y", color=GRID, lw=.7); ax.set_axisbelow(True); ax.set_xlim(-.3, 5.8); ax.set_ylim(bottom=0)
    ax.tick_params(axis="y", labelsize=7.5)
h_, l_ = axes[0].get_legend_handles_labels()
fig.legend(h_, l_, loc="lower center", ncol=4, frameon=False, fontsize=8, bbox_to_anchor=(0.5, -0.02))
fig.suptitle("그림 3. 재귀 예측 6개월 경로 — Chronos·FinCast는 한 방향으로 계속 커지고, TimesFM은 완만함 (×= 4월/11월)", fontsize=10, x=0.02, ha="left")
plt.tight_layout(rect=(0, 0.06, 1, 0.92)); plt.savefig(OUT / "f7.png", bbox_inches="tight"); plt.close()

# 보고서에 들어간 그림을 report/figures/에 알아보기 쉬운 이름으로 복사
import shutil
FIG = BASE.parent / "report" / "figures"; FIG.mkdir(parents=True, exist_ok=True)
for src, name in [("fig3.png", "그림1_사용자별_MASE.png"), ("fig4.png", "그림2_U3_목돈직후_6개월예측.png"),
                  ("f7.png", "그림3_파운데이션모델_재귀예측경로.png"), ("fig5.png", "그림4_월총지출_실제와_6개월예측.png"),
                  ("fig1.png", "참고_4명합계MAE_전체모델.png"), ("fig6.png", "참고_6개월예측합계_전체모델.png")]:
    shutil.copy(OUT / src, FIG / name)
print("저장: scripts/out/*.png, report/figures/")
