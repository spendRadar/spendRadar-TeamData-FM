"""SpendRadar 팀원 지출 데이터 평가 공통 함수 (Baseline 레포·FM 레포 공통).

  1) 데이터 로드        load_team()   data/team_monthly_long.csv → 사용자별 월간 지출 (카테고리 6개 + 전체)
  2) 예측              forecast()    직접 예측: 입력 기간 전체를 보고 6개월을 한 번에
  3) 검증 + 향후 예측   evaluate()    마지막 6개월(test)을 가리고 맞혀 MAE·MASE·WQL 계산 + 향후 6개월 예측
  4) Baseline 4종      BASELINES     HistQuantile · Naive · SeasonalNaive · 3개월 평균

예측 함수 형식 (모델 공통): pred(ctxs, h) → {분위수 q: (시계열 수, h) 배열}, q = 0.1 ~ 0.9
Colab 노트북(notebooks/)의 3 ~ 5번 셀과 같은 계산임.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

CATEGORIES = ['식비 / 카페', '주거 / 통신', '쇼핑 / 패션', '교통 / 차량', '문화 / 여가', '의료']
SERIES = CATEGORIES + ['전체']                          # 전체 = 6개 카테고리 합계, 별도 시계열로 예측
Q = tuple(round(0.1 * k, 1) for k in range(1, 10))      # 분위수 10% ~ 90% (WQL용 9개)
HORIZON = 6                                             # 검증·예측 길이 (개월)


# ---------------------------------------------------------------- 데이터
def load_team(path: str) -> dict:
    """long 형식 CSV → {사용자 ID: dict(user, monthly, series, end, test_start)}
    monthly: 월(PeriodIndex) × 시계열 7개(카테고리 6 + 전체) / end: 마지막 달 / test_start: 검증 시작 달"""
    df = pd.read_csv(path, parse_dates=["ds"])
    people = {}
    for uid, g in df.groupby("entity_id", sort=True):
        wide = g.pivot(index="ds", columns="category", values="y")
        wide.index = pd.PeriodIndex(wide.index, freq="M")
        monthly = wide.reindex(columns=SERIES).astype(float)
        test = g[g.split == "test"].ds
        people[uid] = dict(user=uid, monthly=monthly,
                           series={c: monthly[c].astype("float32") for c in SERIES},
                           end=str(monthly.index[-1]), test_start=str(test.min().to_period("M")))
        print(f"{uid}: {monthly.index[0]} ~ {monthly.index[-1]} ({len(monthly)}개월) · 검증 {people[uid]['test_start']}부터 {HORIZON}개월 · "
              f"예측 {monthly.index[-1] + 1}부터 {HORIZON}개월")
    return people


# ---------------------------------------------------------------- Baseline 4종
# HistQuantile : 최근 12개월 값의 분위수를 6개월 내내 그대로 사용 (기존 보고서 기준선)
# Naive        : 지난달 값 / SeasonalNaive: 작년 같은 달 값 / ma3: 최근 3개월 평균
# Naive·SeasonalNaive·ma3의 예상 범위 = 점예측 + 과거 예측 오차(잔차)의 분위수 (중앙값이 점예측과 같도록 맞춤)
def _rq(point, resid):
    """점예측 + 잔차 분위수 → 분위수별 예측"""
    resid = np.asarray(resid, float) if len(resid) else np.zeros(1)
    med = np.quantile(resid, 0.5)
    return {q: point + np.quantile(resid, q) - med for q in Q}


def _base_one(kind, c, h):
    c = np.asarray(c, float)
    if kind == "baseline":
        return {q: np.full(h, np.quantile(c[-12:].astype(np.float32), q)) for q in Q}
    if kind == "naive" or (kind == "snaive" and len(c) < 13):   # 1년치가 안 되면 snaive → naive
        return _rq(np.full(h, c[-1]), c[1:] - c[:-1])
    if kind == "snaive":
        return _rq(np.array([c[len(c) - 12 + (k % 12)] for k in range(h)]), c[12:] - c[:-12])
    if kind == "ma3":
        return _rq(np.full(h, c[-3:].mean()), [c[t] - c[t - 3:t].mean() for t in range(3, len(c))])


def _make_base(kind):
    def f(ctxs, h):
        outs = [_base_one(kind, c, h) for c in ctxs]
        return {q: np.vstack([o[q] for o in outs]) for q in Q}
    return f


# 내부 이름 "baseline" = HistQuantile (결과 파일의 모델 열: baseline(직접), naive(직접) …)
BASELINES = {k: _make_base(k) for k in ["baseline", "naive", "snaive", "ma3"]}


# ---------------------------------------------------------------- 예측
def forecast(pred, ctxs, h):
    """직접 예측: 입력 기간 전체를 보고 h개월을 한 번에 예측 → {분위수 q: (시계열 수, h)}
    전 기간 0원인 시계열은 모델에 넣지 않고 0원 예측, 음수는 0으로 자르고 분위수는 크기순 정렬"""
    live = [i for i, c in enumerate(ctxs) if np.any(np.asarray(c) != 0)]
    res = {q: np.zeros((len(ctxs), h)) for q in Q}
    if live:
        p = pred([np.asarray(ctxs[i], dtype=np.float32) for i in live], h)
        for q in Q: res[q][live] = np.asarray(p[q])[:, :h]
    a = np.sort(np.stack([np.maximum(res[q], 0) for q in Q]), axis=0)
    return {q: a[j] for j, q in enumerate(Q)}


# ---------------------------------------------------------------- 검증 + 향후 예측
def evaluate(pred, d):
    """사용자 한 명: 검증(test) 지표 met · 향후 6개월 예측 fc · 검증 실제 vs 예측 val (직접 예측)
    시계열 = 카테고리 6개 + 전체(합계), 각각 따로 예측
    MAE  = 월 평균 |실제 − 예측 중앙값| (원/월)
    MASE = MAE ÷ 입력 구간 '지난달 값' 예측의 평균 오차 (lag 1)
    WQL  = 2 × Σpinball ÷ Σ|실제| (분위수 9개 평균)
    '종합' 행 = 카테고리 6개 기준 (MAE 합 · MASE 평균 · WQL 합쳐서 계산 · 적중률 평균), 전체 시계열은 포함하지 않음
    지출이 한 번도 없는 시계열은 MASE·WQL·적중률에서 제외"""
    series, monthly = d["series"], d["monthly"]
    t0 = pd.Period(d["test_start"], "M"); tm = pd.period_range(t0, periods=HORIZON, freq="M")
    ctxs = [series[c][series[c].index < t0].values for c in SERIES]
    actual = np.stack([series[c][tm].values for c in SERIES]).astype(float)
    nz = [c for c in SERIES if monthly[c].sum() > 0]
    P = forecast(pred, ctxs, HORIZON)
    rows, pin_all, y_all = [], 0.0, 0.0
    for i, c in enumerate(SERIES):
        y, med = actual[i], P[0.5][i]
        mae = np.abs(y - med).mean()
        ctx = np.asarray(ctxs[i], float); sc = np.mean(np.abs(np.diff(ctx))) if len(ctx) > 1 else np.nan
        pin = sum(np.maximum(q * (y - P[q][i]), (q - 1) * (y - P[q][i])).sum() for q in Q) / len(Q)
        ys = np.abs(y).sum()
        if c in nz and c in CATEGORIES: pin_all += pin; y_all += ys
        rows.append({"카테고리": c, "MAE(원/월)": mae, "MASE": mae / sc if c in nz and sc > 0 else np.nan,
                     "WQL": 2 * pin / ys if ys > 0 else np.nan,
                     "예상범위 적중률": ((y >= P[0.1][i]) & (y <= P[0.9][i])).mean() if c in nz else np.nan})
    val = pd.DataFrame([{"카테고리": c, "월": str(m), "실제": actual[i, h], "예측": P[0.5][i, h],
                         "하한(10%)": P[0.1][i, h], "상한(90%)": P[0.9][i, h]}
                        for i, c in enumerate(SERIES) for h, m in enumerate(tm)])
    met = pd.DataFrame(rows).set_index("카테고리")
    cat = met.loc[CATEGORIES]
    met.loc["종합"] = {"MAE(원/월)": cat["MAE(원/월)"].sum(), "MASE": cat["MASE"].mean(),
                      "WQL": 2 * pin_all / y_all, "예상범위 적중률": cat["예상범위 적중률"].mean()}
    # 향후 6개월 (전체 기간을 입력으로)
    fut = pd.period_range(pd.Period(d["end"], "M") + 1, periods=HORIZON, freq="M")
    F = forecast(pred, [series[c].values for c in SERIES], HORIZON)
    fc = pd.DataFrame([{"카테고리": c, "월": str(m), "예측": round(F[0.5][i, h]),
                        "하한(10%)": round(F[0.1][i, h]), "상한(90%)": round(F[0.9][i, h])}
                       for i, c in enumerate(SERIES) for h, m in enumerate(fut)])
    return met, fc, val, P, F
