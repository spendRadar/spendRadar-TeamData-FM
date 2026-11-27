"""5단계(선택): 모든 모델 결과를 엑셀 한 파일로 정리 → results/SpendRadar_TeamData_results.xlsx
실행: python scripts/5_build_results_xlsx.py"""
from pathlib import Path
import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

BASE = Path(__file__).resolve().parent
R = BASE.parent / "results"
NAME = {"timesfm(재귀)": "TimesFM 2.5 (재귀)", "chronos(재귀)": "Chronos-2 (재귀)", "moirai(재귀)": "Moirai 2.0 (재귀)",
        "fincast(재귀)": "FinCast (재귀)",
        "baseline(직접)": "HistQuantile (직접)", "baseline(재귀)": "HistQuantile (재귀)", "naive(직접)": "Naive (직접)",
        "naive(재귀)": "Naive (재귀)", "snaive(직접)": "Seasonal Naive (직접)", "snaive(재귀)": "Seasonal Naive (재귀)",
        "ma3(직접)": "3개월 평균 (직접)", "ma3(재귀)": "3개월 평균 (재귀)"}
ORDER = list(NAME.values()); U = ["U1", "U2", "U3", "U4"]
CATS = ['식비 / 카페', '주거 / 통신', '쇼핑 / 패션', '의료 및 기타', '교통 / 차량', '문화 / 여가']
DIRS = ["timesfm", "chronos", "moirai", "fincast", "baseline"]


def load(kind, dirs):
    fs = [R / d / f"ALL_{kind}_{d}.csv" for d in dirs]
    d = pd.concat([pd.read_csv(f) for f in fs if f.exists()], ignore_index=True)
    d["모델"] = d["모델"].map(NAME)
    return d


def order(df, cols):
    keys = {"모델": {m: i for i, m in enumerate(ORDER)}, "사용자": {u: i for i, u in enumerate(U)},
            "카테고리": {c: i for i, c in enumerate(CATS)}}
    return df.sort_values(cols, key=lambda s: s.map(keys[s.name]) if s.name in keys else s)


M, F, V = load("metrics", DIRS), load("forecast", DIRS), load("validation", DIRS)
tot = M[M.카테고리 == "전체"].drop(columns="카테고리")
s1 = pd.DataFrame({"MAE 4명 합계(원)": tot.groupby("모델")["MAE(원/월)"].sum(), "MASE 4명 평균": tot.groupby("모델")["MASE"].mean(),
                   "WQL 4명 평균": tot.groupby("모델")["WQL"].mean(), "예상범위 적중률 평균": tot.groupby("모델")["예상범위 적중률"].mean()}
                  ).sort_values("MAE 4명 합계(원)")
s1.insert(1, "MAE 순위", s1["MAE 4명 합계(원)"].rank(method="min").astype(int)); s1 = s1.reset_index()
f6 = F.pivot_table(index="모델", columns="사용자", values="예측", aggfunc="sum")[U]
f6 = f6.loc[[m for m in ORDER if m in f6.index]].round(0).reset_index()
info = pd.DataFrame({"항목": ["내용", "검증 방법", "예측", "지표", "파일 출처", "미포함", "주의"], "설명": [
    "SpendRadar 카테고리별 월 지출 예측 — 파운데이션 모델 4종(TimesFM 2.5·Chronos-2·Moirai 2.0·FinCast) + 기준선 4종(직접·재귀) 결과 모음",
    "2026-05~2026-10(6개월)을 가리고 이전 데이터로 예측 → 실제와 비교. 사용자 4명 × 카테고리 6개",
    "2026-11~2027-04 향후 6개월 예측(전체 데이터 사용). 값은 예측 분포의 중앙값, 하한/상한은 10%/90% 분위수",
    "MAE=월 평균 오차(원), MASE=규모 보정 오차(1 미만이면 '지난달 값'보다 나음), WQL=예상 범위 품질 — 모두 낮을수록 좋음",
    "results/<모델>/ALL_*.csv (FM: notebooks/의 Colab 노트북 출력, baseline: Baseline 레포 scripts/run_baselines.py 출력)",
    "Chronos-2의 검증 상세(ALL_validation)는 해당 실행에서 저장되지 않음",
    "팀원 4명의 실제 지출 데이터 — 사용자는 익명 ID(U1 ~ U4)로 표기"]})
sheets = [("안내", info), ("1_4명종합", s1), ("2_사용자별지표", order(tot, ["사용자", "모델"])),
          ("3_카테고리별지표", order(M[M.카테고리 != "전체"], ["사용자", "카테고리", "모델"])),
          ("4_6개월예측합계", f6), ("5_6개월예측_상세", order(F, ["모델", "사용자", "카테고리", "월"])),
          ("6_검증_실제vs예측", order(V, ["모델", "사용자", "카테고리", "월"]))]
out = R / "SpendRadar_TeamData_results.xlsx"
with pd.ExcelWriter(out, engine="openpyxl") as w:
    for n, d in sheets:
        d.to_excel(w, sheet_name=n, index=False)

wb = load_workbook(out); hf = PatternFill("solid", fgColor="F1F3F5"); tf = PatternFill("solid", fgColor="E8F1FC")
for ws in wb.worksheets:
    for c in ws[1]:
        c.font = Font(bold=True); c.fill = hf; c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.freeze_panes = "A2"
    hdr = [c.value for c in ws[1]]
    for j, h in enumerate(hdr, 1):
        vals = [len(str(ws.cell(r, j).value or "")) * 1.3 for r in range(2, min(ws.max_row, 60) + 1)]
        width = max(10, min(60, max([len(str(h)) * 2] + vals)))
        ws.column_dimensions[get_column_letter(j)].width = 110 if (ws.title == "안내" and j == 2) else width
        h = str(h)
        fmt = ("#,##0" if any(k in h for k in ["MAE", "예측", "하한", "상한", "실제"] + U)
               else "0.000" if any(k in h for k in ["MASE", "WQL"]) else "0%" if "적중률" in h else None)
        if fmt and ws.title != "안내":
            for r in range(2, ws.max_row + 1):
                ws.cell(r, j).number_format = fmt
    if "모델" in hdr:
        mj = hdr.index("모델") + 1
        for r in range(2, ws.max_row + 1):
            if str(ws.cell(r, mj).value).startswith("TimesFM"):
                for c in ws[r]:
                    c.fill = tf
wb.save(out)
print("저장:", out, [(n, len(d)) for n, d in sheets])
