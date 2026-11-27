"""3단계: 모든 결과를 엑셀 한 파일로 → results/SpendRadar_TeamData_results.xlsx
실행: python scripts/3_build_results_xlsx.py   (1단계 결과 필요)"""
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
DIRS = ["timesfm", "chronos", "moirai", "fincast", "baseline"]
NAME = {"timesfm(재귀)": "TimesFM 2.5", "chronos(재귀)": "Chronos-2", "moirai(재귀)": "Moirai 2.0", "fincast(재귀)": "FinCast",
        "baseline(재귀)": "HistQuantile 재귀", "baseline(직접)": "HistQuantile 직접", "naive(재귀)": "Naive 재귀",
        "naive(직접)": "Naive 직접", "snaive(재귀)": "SeasonalNaive 재귀", "snaive(직접)": "SeasonalNaive 직접",
        "ma3(재귀)": "3개월 평균 재귀", "ma3(직접)": "3개월 평균 직접"}
SERIES = ['식비 / 카페', '주거 / 통신', '쇼핑 / 패션', '교통 / 차량', '문화 / 여가', '의료', '전체', '종합']
ov = pd.read_csv(RES / "comparison_overall.csv")
ORDER = list(ov["모델"])


def load(kind):
    d = pd.concat([pd.read_csv(RES / k / f"ALL_{kind}_{k}.csv") for k in DIRS], ignore_index=True)
    d["모델"] = d["모델"].map(NAME)
    key = {"모델": {m: i for i, m in enumerate(ORDER)}, "카테고리": {c: i for i, c in enumerate(SERIES)}}
    cols = [c for c in ["모델", "사용자", "카테고리", "월"] if c in d]
    return d.sort_values(cols, key=lambda s: s.map(key[s.name]) if s.name in key else s)


M, F, V = load("metrics"), load("forecast"), load("validation")
info = pd.DataFrame({"항목": ["내용", "데이터", "검증", "향후 예측", "지표", "종합 행", "출처"], "설명": [
    "SpendRadar 팀원 지출 데이터 — 파운데이션 모델 4종(TimesFM 2.5 · Chronos-2 · Moirai 2.0 · FinCast) + Baseline 4종(직접 · 재귀) 결과",
    "팀원 3명(U1 · U2 · U4) × 카테고리 6개 + 전체(합계). 포함 조건 · 전처리는 spendRadar-TeamData-Baseline README",
    "2026-05 ~ 2026-10(6개월)을 가리고 이전 데이터로 예측. 재귀 = 1개월 예측 분포에서 샘플 경로 200개로 6개월 불확실성 누적",
    "2026-11 ~ 2027-04, 예측 = 중앙값, 하한 · 상한 = 10% · 90% 분위수",
    "MAE = 월 평균 오차(원), MASE = 지난달 값 예측 대비 오차(1 미만이면 더 정확), WQL = 분위수 예측 품질 — 모두 낮을수록 좋음",
    "카테고리 '종합' = 카테고리 6개 기준 사용자 종합 (MAE 합, MASE · 적중률 평균, WQL 합쳐서 계산), '전체' = 월 총지출 시계열",
    "results/<모델>/ALL_*.csv (FM: notebooks/ Colab 노트북, Baseline: Baseline 레포 scripts/run_baselines.py)"]})
sheets = [("안내", info), ("1_종합비교", ov), ("2_사용자별", pd.read_csv(RES / "comparison_by_user.csv")),
          ("3_FM_vs_Baseline_검정", pd.read_csv(RES / "comparison_tests.csv")),
          ("4_지표_상세", M), ("5_6개월예측합계", pd.read_csv(RES / "comparison_forecast_total.csv")),
          ("6_6개월예측_상세", F), ("7_검증_실제vs예측", V)]
out = RES / "SpendRadar_TeamData_results.xlsx"
with pd.ExcelWriter(out, engine="openpyxl") as w:
    for n, d in sheets:
        d.to_excel(w, sheet_name=n, index=False)

wb = load_workbook(out)
hf, tf = PatternFill("solid", fgColor="F1F3F5"), PatternFill("solid", fgColor="E8F1FC")
for ws in wb.worksheets:
    for c in ws[1]:
        c.font = Font(bold=True); c.fill = hf; c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.freeze_panes = "A2"
    hdr = [str(c.value) for c in ws[1]]
    for j, h in enumerate(hdr, 1):
        vals = [len(str(ws.cell(r, j).value or "")) * 1.2 for r in range(2, min(ws.max_row, 60) + 1)]
        ws.column_dimensions[get_column_letter(j)].width = 120 if (ws.title == "안내" and j == 2) else max(10, min(50, max([len(h) * 1.8] + vals)))
        fmt = ("0%" if "적중" in h else "0.000" if any(k in h for k in ["MASE", "WQL", "p ", "배율"])
               else "#,##0" if any(k in h for k in ["MAE", "예측", "하한", "상한", "실제", "U1", "U2", "U4"]) else None)
        if fmt and ws.title != "안내":
            for r in range(2, ws.max_row + 1): ws.cell(r, j).number_format = fmt
    if "모델" in hdr or "파운데이션 모델" in hdr:
        mj = (hdr.index("모델") if "모델" in hdr else hdr.index("파운데이션 모델")) + 1
        for r in range(2, ws.max_row + 1):
            if str(ws.cell(r, mj).value).startswith("TimesFM"):
                for c in ws[r]: c.fill = tf
wb.save(out)
print("저장:", out)
