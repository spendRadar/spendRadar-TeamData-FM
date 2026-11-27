// 4단계: 보고서(.docx) 생성 → report/SpendRadar_TimesFM_검증보고서.docx
// 실행: npm install docx  →  node scripts/4_build_TimesFM_report.js  (1 ~ 3단계를 먼저 실행)
const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, ImageRun, AlignmentType,
  WidthType, ShadingType, BorderStyle, LevelFormat, HeadingLevel, Footer, PageNumber, TableLayoutType,
} = require("docx");

const J = JSON.parse(fs.readFileSync(__dirname + "/out/data.json", "utf8"));
// 부록 B 원자료: data/team_monthly_long.csv → 사용자별 [월, 카테고리 6개, 합계] 행
const CATS0 = ["식비 / 카페", "주거 / 통신", "쇼핑 / 패션", "의료 및 기타", "교통 / 차량", "문화 / 여가"];
const SRC = { U1: "거래 내역 (거래 단위)", U2: "월별 집계", U3: "월별 집계 (2025·2026 가계부)", U4: "월별 집계" };
const LONG = fs.readFileSync(__dirname + "/../data/team_monthly_long.csv", "utf8").replace(/^\uFEFF/, "").trim().split(/\r?\n/).slice(1)
  .map((l) => { const c = l.split(","); return { u: c[2], cat: c[3], m: c[6].slice(0, 7), y: Number(c[7]) }; });
const RAW = ["U1", "U2", "U3", "U4"].map((u) => {
  const months = [...new Set(LONG.filter((r) => r.u === u).map((r) => r.m))].sort();
  const rows = months.map((m) => { const v = CATS0.map((c) => LONG.find((r) => r.u === u && r.m === m && r.cat === c).y); return [m, ...v, v.reduce((a, b) => a + b, 0)]; });
  return { u, src: SRC[u], rows };
});
const FU = JSON.parse(fs.readFileSync(__dirname + "/out/future.json", "utf8"));
const FA = JSON.parse(fs.readFileSync(__dirname + "/out/future_all.json", "utf8"));
const sum = (a) => a.reduce((x, y) => x + y, 0);
const FONT = "Malgun Gothic";
const W = 9026; // A4 - 1in margins
const BLUE_FILL = "E8F1FC", HEAD_FILL = "F1F3F5", INK2 = "52514E";
const T = "TimesFM 2.5";
const U = ["U1", "U2", "U3", "U4"];

const get = (d, r, c) => d.data[d.index.indexOf(r)][d.columns.indexOf(c)];
const won = (v) => Math.round(v).toLocaleString("en-US");
const man = (v) => (v / 1e4).toLocaleString("en-US", { maximumFractionDigits: 0 }) + "만";
const f3 = (v) => (v === null || v === undefined || Number.isNaN(v) ? "-" : Number(v).toFixed(3));
const f2 = (v) => (v === null || v === undefined ? "-" : Number(v).toFixed(2));
const pc = (v) => (v >= 0 ? "+" : "−") + Math.abs(v).toFixed(1) + "%";
const pct0 = (v) => Math.round(v * 100) + "%";

// ---------- text helpers ----------
const run = (t, o = {}) => new TextRun({ text: t, font: FONT, size: o.size || 21, bold: o.bold, color: o.color, italics: o.italics });
const runs = (parts) => parts.map((p) => (typeof p === "string" ? run(p) : run(p[0], p[1])));
const P = (parts, o = {}) => new Paragraph({ children: runs(Array.isArray(parts) ? parts : [parts]), spacing: { after: o.after ?? 120, line: 300 }, alignment: o.align, keepNext: o.keepNext });
const H1 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [run(t, { size: 30, bold: true })] });
const H2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [run(t, { size: 25, bold: true })] });
const B = (parts, lvl = 0) => new Paragraph({ numbering: { reference: "bul", level: lvl }, children: runs(Array.isArray(parts) ? parts : [parts]), spacing: { after: 80, line: 290 } });
const N2 = (parts) => new Paragraph({ numbering: { reference: "num2", level: 0 }, children: runs(Array.isArray(parts) ? parts : [parts]), spacing: { after: 80, line: 290 } });
const N = (parts) => new Paragraph({ numbering: { reference: "num", level: 0 }, children: runs(Array.isArray(parts) ? parts : [parts]), spacing: { after: 80, line: 290 } });
const CAP = (t) => new Paragraph({ children: [run(t, { size: 19, bold: true, color: "0B0B0B" })], spacing: { before: 160, after: 80 }, keepNext: true });
const NOTE = (t) => new Paragraph({ children: [run(t, { size: 17, color: INK2 })], spacing: { before: 40, after: 200 } });
const IMG = (file, w, h) => new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 120, after: 80 },
  children: [new ImageRun({ type: "png", data: fs.readFileSync(__dirname + "/out/" + file), transformation: { width: w, height: h },
    altText: { title: file, description: file, name: file } })] });

// ---------- table helper ----------
const border = { style: BorderStyle.SINGLE, size: 4, color: "D5D4CE" };
const borders = { top: border, bottom: border, left: border, right: border };
function table(header, rows, widths, opt = {}) {
  const sum = widths.reduce((a, b) => a + b, 0);
  const ws = widths.map((w) => Math.round((w / sum) * W));
  ws[ws.length - 1] += W - ws.reduce((a, b) => a + b, 0);
  const cell = (txt, i, isHead, fill, bold) => new TableCell({
    width: { size: ws[i], type: WidthType.DXA }, borders,
    shading: fill ? { fill, type: ShadingType.CLEAR, color: "auto" } : undefined,
    margins: { top: 50, bottom: 50, left: 90, right: 90 },
    children: [new Paragraph({ alignment: (i === 0 || (opt.left || []).includes(i)) ? AlignmentType.LEFT : AlignmentType.RIGHT,
      children: [run(String(txt), { size: 18, bold: isHead || bold })] })],
  });
  const hl = opt.highlight || [];
  const trs = [new TableRow({ tableHeader: true, children: header.map((h, i) => cell(h, i, true, HEAD_FILL)) })];
  rows.forEach((r) => {
    const isHl = hl.includes(r[0]);
    trs.push(new TableRow({ cantSplit: true, children: r.map((v, i) => cell(v, i, false, isHl ? BLUE_FILL : undefined, isHl)) }));
  });
  return new Table({ width: { size: W, type: WidthType.DXA }, columnWidths: ws, rows: trs, layout: TableLayoutType.FIXED });
}

// ---------- data ----------
const A = J.A, Bx = J.B, C = J.C, D = J.D, E = J.E;
const FM = ["TimesFM 2.5", "Chronos-2", "Moirai 2.0"];
const CATS = ["식비 / 카페", "주거 / 통신", "쇼핑 / 패션", "의료 및 기타", "교통 / 차량", "문화 / 여가"];
const PERSON = {
  "U1": "6개월 693만 원(월 110만~127만 원). 의료 및 기타가 340만 원으로 절반(49%)이고 식비 / 카페가 226만 원입니다. 주거 / 통신 거래는 없어 0원입니다. 최근 6개월 실제 월평균(171만 원)보다 낮게 예측했습니다.",
  "U2": "6개월 465만 원(월 74만~89만 원). 식비 131만, 쇼핑 107만, 의료 및 기타 104만, 주거 / 통신 63만 원으로 고르게 나뉩니다. 11월이 89만 원으로 가장 높고 이후 75만 원 안팎에서 안정적입니다.",
  "U3": "6개월 176만 원. 11월 67만 원에서 4월 18만 원으로 줄어듭니다. 의료 및 기타가 156만 원(89%)인데, 10월 338만 원 목돈의 여파가 점차 사라지는 모양입니다. 식비·쇼핑·교통은 올해처럼 거의 0원으로 예측했습니다.",
  "U4": "6개월 909만 원(월 143만~158만 원). 의료 및 기타가 399만 원(44%)으로 가장 크고, 쇼핑 187만, 식비 137만, 주거 / 통신 119만 원입니다. 과거 목돈이 잦아 의료 및 기타의 예상 범위가 0~263만 원으로 매우 넓습니다.",
};
const kind = (m) => (FM.includes(m) ? "파운데이션" : "기준선");
const aT = get(A, T, "MAE 합계");
const rel = J.rel, relB = J.relB;

// 표 1: 종합
const t1 = A.index.map((m) => [m, kind(m), won(get(A, m, "MAE 합계")),
  m === T ? "–" : pc((get(A, m, "MAE 합계") / aT - 1) * 100),
  f3(get(A, m, "MASE 평균")), f3(get(A, m, "WQL 평균")), pct0(get(A, m, "적중률 평균")), String(get(A, m, "MAE 합계 순위"))]);

// 표 2: TimesFM vs HistQuantile 사람별
const pm = J.per_mae, ps = J.per_mase, pw = J.per_wql;
const HQ = "HistQuantile 직접";
const t2 = U.map((u) => {
  const a = get(pm, T, u), b = get(pm, HQ, u);
  return [u, won(a), won(b), pc((a / b - 1) * 100), f3(get(ps, T, u)), f3(get(ps, HQ, u)), f3(get(pw, T, u)), f3(get(pw, HQ, u))];
});
t2.push(["4명 종합", won(aT), won(get(A, HQ, "MAE 합계")), pc(rel[HQ].MAE), f3(get(A, T, "MASE 평균")), f3(get(A, HQ, "MASE 평균")),
  f3(get(A, T, "WQL 평균")), f3(get(A, HQ, "WQL 평균"))]);

// 표 3: 1:1 조합 비교
const t3 = C.index.map((m) => [m, String(get(C, m, "TimesFM 승")), String(get(C, m, "TimesFM 패")),
  (get(C, m, "MASE 차이 중앙값") >= 0 ? "+" : "") + f3(get(C, m, "MASE 차이 중앙값")),
  Number(get(C, m, "Wilcoxon p (TimesFM이 나음)")).toFixed(3) + (get(C, m, "Wilcoxon p (TimesFM이 나음)") < 0.05 ? " ✓" : "")]);

// 표 4: 의료 및 기타 제외
const bT = get(Bx, T, "MAE 합계");
const t4 = Bx.index.map((m) => [m, kind(m), won(get(Bx, m, "MAE 합계")), m === T ? "–" : pc((get(Bx, m, "MAE 합계") / bT - 1) * 100),
  f3(get(Bx, m, "MASE 평균")), f3(get(Bx, m, "WQL 평균")), String(get(Bx, m, "MAE 합계 순위"))]);

// 표 5: U3 카테고리
const jc = J.jk_cat;
const t5 = jc.index.map((c) => [c, ...jc.columns.map((m) => won(get(jc, c, m)))]);

// 표 6: 6개월 예측 합계
const e6 = ["TimesFM 2.5", "Chronos-2", "Moirai 2.0", "HistQuantile 직접", "3개월 평균 재귀", "3개월 평균 직접", "Naive 직접", "Seasonal Naive 직접"];
const t6 = e6.map((m) => [m, ...U.map((u) => won(get(E, m, u)))]);

// 표 7: 안정성
const t7 = D.index.map((m) => [m, kind(m), f2(get(D, m, "최악 MASE")), get(D, m, "최악 사용자"), f2(get(D, m, "사람별 1위 대비 최대 배율")) + "배"]);

// 표 8: FM 3종
const t8 = [];
U.forEach((u) => FM.forEach((m, k) => t8.push([k === 0 ? u : "", m, won(get(pm, m, u)), f3(get(ps, m, u)), f3(get(pw, m, u)), pct0(get(J.per_cov, m, u))])));
FM.forEach((m, k) => t8.push([k === 0 ? "4명 종합" : "", m, won(get(A, m, "MAE 합계")), f3(get(A, m, "MASE 평균")), f3(get(A, m, "WQL 평균")), pct0(get(A, m, "적중률 평균"))]));

// 부록
const appx = (d, fmt) => d.index.map((m) => [m, ...U.map((u) => fmt(get(d, m, u)))]);
const sortIdx = (d) => ({ ...d, index: A.index, data: A.index.map((m) => d.data[d.index.indexOf(m)]) });

const hqMed = Math.round(get(J.jk_med, HQ, "2026-11"));

const BL8 = A.index.filter((m) => !["Chronos-2", "Moirai 2.0"].includes(m));
const tb1 = BL8.map((m) => [m, won(get(A, m, "MAE 합계")), m === T ? "–" : pc(-(1 - aT / get(A, m, "MAE 합계")) * 100),
  f3(get(A, m, "MASE 평균")), f3(get(A, m, "WQL 평균")), pct0(get(A, m, "적중률 평균"))]);
const BLc = ["HistQuantile 직접", "HistQuantile 재귀", "Seasonal Naive 직접", "Naive 직접", "3개월 평균 직접", "3개월 평균 재귀"];
const tb3 = BLc.map((m) => [m, `${get(C, m, "TimesFM 승")}승 ${get(C, m, "TimesFM 패")}패`,
  (get(C, m, "MASE 차이 중앙값") >= 0 ? "+" : "") + f3(get(C, m, "MASE 차이 중앙값")),
  Number(get(C, m, "Wilcoxon p (TimesFM이 나음)")).toFixed(3) + (get(C, m, "Wilcoxon p (TimesFM이 나음)") < 0.05 ? " ✓ 유의" : "")]);
const BLx = Bx.index.filter((m) => !["Chronos-2", "Moirai 2.0", "FinCast"].includes(m));
const tb4 = BLx.map((m) => [m, won(get(Bx, m, "MAE 합계")), m === T ? "–" : pc(-(1 - bT / get(Bx, m, "MAE 합계")) * 100), f3(get(Bx, m, "MASE 평균"))]);
const e6b = ["TimesFM 2.5", "HistQuantile 직접", "3개월 평균 재귀", "3개월 평균 직접", "Naive 직접", "Seasonal Naive 직접"];
const tb6 = e6b.map((m) => [m, ...U.map((u) => (get(E, m, u) / 1e4).toFixed(0))]);
const D8 = D.index.filter((m) => !["Chronos-2", "Moirai 2.0", "FinCast"].includes(m));
const tb7 = D8.map((m) => [m, f2(get(D, m, "최악 MASE")), get(D, m, "최악 사용자"), f2(get(D, m, "사람별 1위 대비 최대 배율")) + "배"]);
const fmRow = (m, drift, p, lic) => [m, won(get(A, m, "MAE 합계")), f3(get(A, m, "MASE 평균")), f3(get(A, m, "WQL 평균")),
  f2(get(D, m, "사람별 1위 대비 최대 배율")) + "배", drift, p, lic];
const G = J.G;
const gp = (m) => Number(get(G, m, "HQ 대비 p")).toFixed(3) + (get(G, m, "HQ 대비 p") < 0.05 ? " ✓" : "");
const gd = (m) => Number(get(G, m, "재귀 쏠림")).toFixed(2);
const tbFM = [["TimesFM 2.5", "Apache-2.0"], ["Chronos-2", "Apache-2.0"], ["Moirai 2.0", "비상업(CC BY-NC)"], ["FinCast", "Apache-2.0"]]
  .map(([m, lic]) => fmRow(m, gd(m), gp(m), lic));
const fin = (k) => get(A, "FinCast", k);

const children = [
  new Paragraph({ spacing: { before: 400, after: 100 }, children: [run("SpendRadar", { size: 24, color: INK2, bold: true })] }),
  new Paragraph({ spacing: { after: 140 }, children: [run("TimesFM 2.5 예측 엔진 검증 보고서", { size: 40, bold: true })] }),
  P([["파운데이션 모델이 통계 기준선보다 나은가, 그리고 왜 TimesFM인가", { color: INK2, size: 23 }]]),
  P([["2026-11-24 · 팀원 4명 실제 지출 데이터 · 검증 2026-05 ~ 2026-10 · 예측 2026-11 ~ 2027-04", { size: 19, color: INK2 }]], { after: 280 }),

  H1("1. 핵심 결론"),
  B([["보고서 기준선보다 정확합니다. ", { bold: true }], `TimesFM 2.5의 4명 합계 오차(MAE)는 HistQuantile보다 ${Math.abs(rel[HQ].MAE).toFixed(1)}%, 예상 범위 오차(WQL)는 ${Math.abs(rel[HQ].WQL).toFixed(1)}% 낮습니다. 사용자×카테고리 23개 조합 중 14개에서 이겼고, 통계적으로 유의합니다(p = 0.028).`]),
  B([["기준선 8가지 중 7가지보다 정확합니다. ", { bold: true }], "Naive보다 5.3%, 3개월 평균 직접보다 6.2%, HistQuantile보다 9.4~9.9%, Seasonal Naive보다 19.7% 오차가 작습니다."]),
  B([["어떤 상황에서도 무너지지 않습니다. ", { bold: true }], "소비 패턴이 바뀐 사용자에서 기준선은 MASE 5.5~5.9로 무너졌지만 TimesFM은 1.72였고, 일회성 목돈 직후에도 합리적인 6개월 예측을 냈습니다."]),
  B([["파운데이션 모델 중에서는 TimesFM이 가장 안정적입니다. ", { bold: true }], "Chronos-2·Moirai 2.0·FinCast와 비교했습니다. 정확도는 Chronos-2와 1% 이내로 같지만, 최악의 경우 오차가 가장 작고(1.29배) 재귀 6개월 예측이 한 방향으로 쏠리지 않습니다. 금융 특화 모델 FinCast는 12개 모델 중 오차가 가장 컸고, Moirai 2.0은 상업적 사용이 불가합니다."]),
  P([["권고: ", { bold: true }], "TimesFM 2.5를 SpendRadar의 기본 예측 엔진으로 채택합니다."], { after: 200 }),

  H1("2. 실험 개요"),
  table(["항목", "내용"], [
    ["데이터", "팀원 4명의 월별 지출, 카테고리 6개 (본인 이체·충전·수입 제외)"],
    ["검증 방법", "2026-05 ~ 2026-10을 가리고 이전 데이터만으로 6개월 재귀 예측 → 실제와 비교 (23개 사용자×카테고리)"],
    ["TimesFM 2.5", "Google 시계열 파운데이션 모델 · 사전학습 모델 그대로 사용(추가 학습 없음)"],
    ["비교 파운데이션 모델", "Chronos-2(Amazon) · Moirai 2.0(Salesforce) · FinCast(금융 특화, CIKM 2025)"],
    ["기준선 8가지", "HistQuantile(기존 보고서 기준선) · Naive(지난달 값) · Seasonal Naive(작년 같은 달) · 3개월 평균 — 각각 직접·재귀"],
    ["평가 지표", "MAE(월 평균 오차, 원) · MASE(규모 보정 오차) · WQL(예상 범위 품질) — 모두 낮을수록 좋음"],
  ], [1.6, 7.4], { left: [1] }),

  H1("3. TimesFM이 기준선보다 나은 이유"),
  H2("3.1 소비 패턴이 바뀌어도 따라갑니다"),
  P("U3는 올해 식비·쇼핑·교통 지출이 거의 0원이 됐습니다. 과거 1년을 보는 기준선은 예전 수준을 계속 예측했지만, TimesFM은 바뀐 패턴을 따라갔습니다."),
  CAP("표 1. U3 카테고리별 MAE (원/월)"),
  table(["카테고리", ...jc.columns], t5, [1.8, 1.5, 1.7, 1.9, 1.6]),
  IMG("fig3.png", 590, 302),
  B("식비 / 카페 오차: TimesFM 390원 vs HistQuantile 221,500원 vs Seasonal Naive 239,750원."),
  H2("3.2 일회성 목돈을 미래로 복사하지 않습니다"),
  P("서비스에서 쓰는 것은 ‘지금부터 6개월’ 예측입니다. U3는 2026-10에 338만 원의 일회성 지출이 있었습니다."),
  IMG("fig4.png", 590, 310),
  CAP("표 2. 향후 6개월 예측 합계 (만 원)"),
  table(["모델", ...U], tb6, [2.6, 1.5, 1.5, 1.5, 1.5], { highlight: [T] }),
  B("지난달 값은 338만 원을 매달 반복해 U3 6개월을 2,046만 원으로, 검증 1위인 3개월 평균 재귀도 995만 원으로 예측합니다."),
  B("작년 같은 달 값은 U4의 작년 2월 목돈(621만 원)을 복사해 1,571만 원으로 예측합니다."),
  B("금융 특화 파운데이션 모델 FinCast도 목돈을 이어 가 의료 및 기타를 매달 163만~224만 원으로, U3 6개월을 1,215만 원으로 예측합니다."),
  B("TimesFM은 목돈을 일시적인 일로 보고 64만 → 15만 원으로 평소 수준에 되돌려, U3 6개월을 176만 원으로 예측합니다."),
  H2("3.3 어떤 사용자에서도 무너지지 않습니다"),
  CAP("표 3. 최악의 경우 (사용자별 MASE 기준)"),
  table(["모델", "최악 MASE", "최악 사용자", "사용자별 1위 대비 최대 배율"], tb7, [2.8, 1.3, 1.3, 2.4], { highlight: [T] }),
  B("기준선은 각자 약점이 있습니다. 과거를 길게 보면 패턴 변화에, 최근 값을 쓰면 목돈에 무너집니다. 사용자마다 맞는 기준선도 다릅니다."),
  B("TimesFM은 4명 모두에서 1위 대비 1.29배 이내로, 하나의 모델로 모든 사용자에게 안정적인 성능을 냅니다."),
  H2("3.4 예상 범위까지 제공합니다"),
  B("TimesFM의 WQL은 0.631로 HistQuantile(0.707)보다 10.8%, Seasonal Naive(0.851)보다 25.9% 좋습니다."),
  B("‘다음 달 OO만~OO만 원’처럼 범위로 안내하는 서비스에 필요한 확률 예측을 추가 작업 없이 제공합니다."),

  H1("4. 파운데이션 모델 중 TimesFM을 선택한 이유"),
  P("같은 조건에서 Chronos-2(Amazon), Moirai 2.0(Salesforce), 그리고 금융 시계열 특화 모델 FinCast(CIKM 2025)와 비교했습니다."),
  CAP("표 4. 파운데이션 모델 4종 비교"),
  table(["모델", "MAE 합계(원)", "MASE 평균", "WQL 평균", "최악 배율", "재귀 쏠림", "HistQ 대비 p", "라이선스"], tbFM,
    [1.6, 1.4, 1, 1, 1, 1, 1.1, 1.6], { highlight: [T], left: [7] }),
  NOTE("재귀 쏠림 = 향후 6개월 예측에서 카테고리별 4월/11월 비율의 로그 절댓값 평균(작을수록 예측 경로가 안정적). HistQ 대비 p = 23개 조합에서 HistQuantile보다 낫다는 Wilcoxon 검정."),
  N([["정확도는 최상위 수준입니다. ", { bold: true }], `TimesFM과 Chronos의 오차 차이는 1% 이내(MAE 3,980,521 vs 3,945,532원, WQL 0.631 vs 0.629)로 사실상 같습니다. 23개 조합 1:1 비교에서도 TimesFM이 Chronos에 12승 11패, FinCast에 14승 9패입니다. FinCast는 MAE ${won(fin("MAE 합계"))}원으로 TimesFM보다 ${((fin("MAE 합계") / aT - 1) * 100).toFixed(1)}% 크고, 기준선을 포함한 12개 모델 중 가장 큽니다.`]),
  N([["최악의 경우가 가장 덜 나쁩니다. ", { bold: true }], "사용자별 1위 대비 최대 배율이 TimesFM 1.29배, Chronos 1.38배, Moirai 1.42배, FinCast 1.64배입니다. 개인 금융 서비스에서는 평균보다 ‘누구에게도 크게 틀리지 않는 것’이 중요합니다."]),
  N([["재귀 6개월 예측이 한 방향으로 쏠리지 않습니다. ", { bold: true }], "재귀 쏠림 지표가 TimesFM 0.29로 가장 작습니다(Moirai 0.30, Chronos 0.44, FinCast 0.53). Chronos는 U4의 의료 및 기타를 60만 → 102만 원으로, U3의 문화 / 여가를 4.9배로 키웁니다. FinCast는 올해 식비가 0원인 U3의 식비 / 카페를 1만 → 9.7만 원으로, U1의 쇼핑 / 패션을 40만 → 65만 원으로 계속 키웁니다."]),
  IMG("f7.png", 600, 210),
  N([["극단으로 치우치지 않습니다. ", { bold: true }], "6개월 예측 합계가 4명 모두에서 네 모델의 가운데(2~3번째)에 있습니다(예: U2 Moirai 380만 · TimesFM 465만 · Chronos 496만 · FinCast 1,133만 원)."]),
  N([["FinCast는 후보에서 제외합니다. ", { bold: true }], "주가·환율 같은 금융 시장 데이터에 맞춰 추세를 이어 가도록 설계된 모델이라, 목돈과 중단이 잦은 개인 소비 데이터에서는 예측이 크게 부풀었습니다(6개월 예측 합계 U3 1,215만 · U2 1,133만 원, TimesFM은 176만 · 465만 원). HistQuantile 대비 개선도 유의하지 않고(p = 0.21), 모델 파일이 약 4GB로 가장 무겁습니다."]),
  N([["Moirai는 후보에서 제외합니다. ", { bold: true }], "정확도가 TimesFM·Chronos보다 낮고, HistQuantile 대비 개선이 유의하지 않으며(p = 0.25), 비상업 라이선스라 서비스에 쓸 수 없습니다."]),
  N([["서비스 적용이 쉽습니다. ", { bold: true }], "Apache-2.0 라이선스로 상업 서비스에 바로 쓸 수 있고, 사용자별 학습 없이 사전학습 모델로 바로 예측합니다."]),

  H1("5. TimesFM 향후 6개월 재귀 예측 (2026-11 ~ 2027-04)"),
  P("TimesFM 2.5로 4명의 전체 데이터(2026-10까지)를 사용해 1개월씩 6번 재귀 예측했습니다. 금액은 예측 분포의 중앙값이며, 마지막 열은 11월 예측의 예상 범위(10~90%)입니다."),
  CAP("표 5. 사용자별 월 총지출 예측 (단위: 만 원)"),
  table(["사용자", ...FU.months.map((m) => m.slice(2)), "6개월 합계"],
    U.map((u) => [u, ...FU.tot.timesfm[u].map((x) => (x / 1e4).toFixed(1)), (sum(FU.tot.timesfm[u]) / 1e4).toFixed(1)]),
    [1.3, 1, 1, 1, 1, 1, 1, 1.3]),
  IMG("fig5.png", 590, 404),
  ...U.flatMap((u, ui) => {
    const rows = CATS.map((c) => {
      const v = FU.cat[u][c];
      return [c, ...v.map((r) => (r[0] / 1e4).toFixed(1)), (sum(v.map((r) => r[0])) / 1e4).toFixed(1),
        `${(v[0][1] / 1e4).toFixed(0)} ~ ${(v[0][2] / 1e4).toFixed(0)}`];
    });
    const totRow = ["합계", ...FU.tot.timesfm[u].map((x) => (x / 1e4).toFixed(1)), (sum(FU.tot.timesfm[u]) / 1e4).toFixed(1), ""];
    return [H2(`5.${ui + 1} ${u}`),
      CAP(`표 ${6 + ui}. ${u} — 카테고리별 6개월 재귀 예측 (단위: 만 원)`),
      table(["카테고리", ...FU.months.map((m) => m.slice(2)), "6개월 합계", "11월 범위"], [...rows, totRow],
        [1.7, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 1.1, 1.3], { highlight: ["합계"] }),
      B(PERSON[u])];
  }),
  H2("5.5 예측 활용 시 참고"),
  B("예측값은 분포의 중앙값이므로 일회성 목돈은 거의 반영되지 않습니다. 서비스에서는 ‘평소 OO만~OO만 원’처럼 범위로 안내하고, 예산 경고에는 상한(90%)을 쓰는 것을 권합니다."),
  H1("6. 결론"),
  P("TimesFM 2.5는 기존 보고서 기준선보다 통계적으로 유의하게 정확했고(MAE −9.4%, p = 0.028), 비교한 기준선 8가지 중 7가지보다 오차가 작았습니다. 더 큰 강점은 안정성입니다. 단순 기준선은 소비 패턴이 바뀌거나 일회성 목돈이 생기면 크게 틀렸지만, TimesFM은 4명 모두에서 무너지지 않았고 목돈 직후에도 합리적인 예측을 냈습니다."),
  P("파운데이션 모델 4종 중에서는 Chronos-2와 정확도가 같으면서 최악의 경우 오차가 가장 작고 재귀 예측이 가장 안정적인 TimesFM 2.5를 기본 엔진으로 권고합니다. 금융 특화 모델인 FinCast는 개인 소비 데이터에서 오히려 가장 부정확해, ‘금융 데이터용 모델’보다 ‘범용 시계열 모델’이 이 서비스에 맞다는 점도 확인했습니다."),
  P([["발표용 한 문장: ", { bold: true }], "“TimesFM은 기존 기준선보다 오차를 9% 줄였고, 소비 패턴 변화나 일회성 목돈에도 무너지지 않는 가장 안정적인 예측 엔진입니다.”"]),
  P([["검증 범위: ", { bold: true }, ], ["4명 × 6개월 한 구간의 결과입니다. 사용자와 검증 구간을 늘려 같은 결론이 유지되는지 추가 확인을 권합니다.", { color: INK2 }]], { after: 60 }),

  // ---------- 부록 A. 자료·코드 안내 ----------
  new Paragraph({ pageBreakBefore: true, heading: HeadingLevel.HEADING_1, children: [run("부록 A. 자료·코드 안내", { size: 30, bold: true })] }),
  P("이 보고서의 데이터, 모델 결과, 실행 코드는 GitHub 저장소 두 곳에 있습니다. 사용자는 익명 ID(U1 ~ U4)로 표기했고, 원본 엑셀은 개인 금융 정보라 올리지 않았습니다."),
  H2("A.1 저장소 구성"),
  table(["저장소 / 폴더", "내용"], [
    ["spendRadar-TeamData-Baseline", "데이터셋 + Baseline 4종 (직접·재귀)"],
    ["   data/team_monthly_long.csv", "4명 × 카테고리 6개 월별 지출 (long 형식, 부록 B와 같음) — 두 저장소에 같은 파일"],
    ["   src/", "prep_team_monthly.py (원본 엑셀 → 월간 데이터) · spendradar_team.py (예측·지표 공통 코드)"],
    ["   scripts/run_baselines.py", "Baseline 예측 + 지표 → results/ (CPU 몇 초)"],
    ["spendRadar-TeamData-FM", "파운데이션 모델 4종 + 비교 분석 + 이 보고서"],
    ["   notebooks/", "run_<모델>_colab.ipynb — TimesFM · Chronos-2 · Moirai 2.0 · FinCast (Colab T4)"],
    ["   results/<모델>/", "ALL_metrics · ALL_forecast · ALL_validation CSV (baseline은 Baseline 저장소 결과 복사본)"],
    ["   results/…results.xlsx", "SpendRadar_TeamData_results.xlsx — 모든 모델 결과를 시트 7개로 정리 (먼저 이 파일을 보면 됨)"],
    ["   scripts/", "1 ~ 5단계 비교 분석 · 그림 · 보고서 · 엑셀 생성"],
    ["   report/", "이 보고서와 그림"],
  ], [3.6, 5.4], { left: [0, 1] }),
  H2("A.2 원자료와 전처리 규칙"),
  B("원자료: 팀원 4명의 은행·카드 거래 내역 또는 가계부를 카테고리로 분류한 엑셀(거래 내역 시트 또는 월별 집계 시트). src/prep_team_monthly.py가 두 형식을 자동으로 구분합니다."),
  B("출금만 사용하고 급여 / 부수입(수입)은 뺐습니다. 거래 내역이 있는 U1은 본인 계좌 이체와 하나머니 충전도 소비가 아니므로 뺐습니다."),
  B("의료와 기타는 ‘의료 및 기타’로 합쳐 카테고리 6개로 정리했습니다. 일부만 기록된 2026-11과, 앞쪽에 지출이 거의 0원인 기간은 제외했습니다."),
  B("월별 집계만 있는 U2 ~ U4는 본인 이체를 뺄 수 없어 ‘의료 및 기타’가 부풀 수 있습니다."),
  H2("A.3 결과 파일 형식 (results/<모델>/)"),
  table(["파일", "내용", "주요 열"], [
    ["ALL_metrics_<모델>.csv", "사용자·카테고리별 검증 지표 (카테고리 = 전체 → 사용자 종합)", "MAE(원/월) · MASE · WQL · 예상범위 적중률"],
    ["ALL_forecast_<모델>.csv", "향후 6개월(2026-11 ~ 2027-04) 예측", "예측(중앙값) · 하한(10%) · 상한(90%)"],
    ["ALL_validation_<모델>.csv", "검증 구간(2026-05 ~ 2026-10) 월별 실제 vs 예측", "실제 · 예측 · 하한 · 상한"],
  ], [2.7, 3.6, 2.7], { left: [1, 2] }),
  NOTE("baseline 폴더에는 기준선 4종 × 직접·재귀 8가지가 ‘모델’ 열로 구분되어 함께 들어 있습니다. Chronos-2는 ALL_validation이 저장되지 않았습니다."),
  H2("A.4 실행 방법"),
  P([["파운데이션 모델 (Google Colab, T4 GPU)", { bold: true }]], { after: 60 }),
  N2("notebooks/run_<모델>_colab.ipynb를 Colab에서 열고 런타임 → 런타임 유형 변경 → T4 GPU 선택"),
  N2("셀을 하나씩 순서대로 실행: 1 설치(✅ 확인) → 2 저장소 데이터 불러오기 → 3 데이터 정리 → 4 모델 → 5 4명 일괄 실행 → 6 사람별 표·그래프 → 7 요약·CSV 저장"),
  N2("내려받은 ALL_metrics · ALL_forecast · ALL_validation CSV를 results/<모델>/에 넣기"),
  P([["비교 분석·보고서 재생성 (FM 저장소 루트에서)", { bold: true }]], { before: 120, after: 60 }),
  table(["순서", "명령", "결과"], [
    ["1", "python scripts/1_analysis.py", "모든 모델 지표 통합·비교 분석"],
    ["2", "python scripts/2_report_data.py", "보고서용 수치 정리 (JSON)"],
    ["3", "python scripts/3_charts.py", "보고서 그림 → report/figures/"],
    ["4", "node scripts/4_build_TimesFM_report.js", "이 보고서 → report/"],
    ["5", "python scripts/5_build_results_xlsx.py", "(선택) 결과 엑셀 → results/"],
  ], [0.8, 4.4, 3.8], { left: [1, 2] }),
  NOTE("필요 패키지: pandas · numpy · scipy · matplotlib · openpyxl (Python), docx (Node.js). results/의 CSV만 있으면 실행됩니다."),

  // ---------- 부록 B. 원자료 ----------
  new Paragraph({ pageBreakBefore: true, heading: HeadingLevel.HEADING_1, children: [run("부록 B. 원자료 — 사용자별 월별 카테고리 지출 (전체 기간)", { size: 30, bold: true })] }),
  P("모델에 실제로 들어간 데이터입니다(단위: 만 원). 원본 엑셀을 A.2의 규칙으로 정리한 것으로, data/team_monthly_long.csv와 같습니다. 음영 행은 검증 구간(2026-05 ~ 2026-10)입니다."),
  table(["사용자", "원본 형식", "기간"], RAW.map((r) => [r.u, r.src, `${r.rows[0][0]} ~ ${r.rows[r.rows.length - 1][0]} (${r.rows.length}개월)`]), [1.4, 4.8, 2.8], { left: [1] }),
  NOTE("U1: 원본은 2024-01부터지만 2024-02 ~ 09는 다른 카드를 써서 이 계좌 소비가 거의 0원이라(본인 확인), 꾸준히 쓰기 시작한 2024-10부터 사용했습니다. U3: 2025년은 가계부 기록, 2026년은 본인 카드를 거의 쓰지 않아 식비 등이 0원인 달이 많습니다(본인 확인). U2·U3·U4는 월별 집계만 있어 본인 계좌 이체를 걸러내지 못했습니다."),
  ...RAW.flatMap((r, ui) => {
    const VM = FU.vmonths;
    const body = r.rows.map((row) => [VM.includes(row[0]) ? row[0] + " ●" : row[0], ...row.slice(1).map((x) => (x / 1e4).toFixed(1))]);
    return [CAP(`표 B${ui + 1}. ${r.u}`), table(["월", ...CATS.map((c) => c.replace(" / ", "/")), "합계"], body,
      [1.3, 1.1, 1.1, 1.1, 1.2, 1.1, 1.1, 1], { highlight: VM.map((m) => m + " ●") })];
  }),

  // ---------- 부록 C. 사용자별 지표 ----------
  new Paragraph({ pageBreakBefore: true, heading: HeadingLevel.HEADING_1, children: [run("부록 C. 모델별·사용자별 3대 지표", { size: 30, bold: true })] }),
  P("파운데이션 모델 4종과 기준선 8가지의 사용자별 검증 결과입니다(검증 2026-05 ~ 2026-10, 낮을수록 좋음). 4명 합계 MAE 순으로 정렬했습니다."),
  CAP("표 C1. MAE (원/월, 카테고리 합)"),
  table(["모델", ...U], A.index.map((m) => [m, ...U.map((u) => won(get(pm, m, u)))]), [2.6, 1.6, 1.6, 1.6, 1.6], { highlight: [T] }),
  CAP("표 C2. MASE (카테고리 평균)"),
  table(["모델", ...U], A.index.map((m) => [m, ...U.map((u) => f3(get(ps, m, u)))]), [2.6, 1.6, 1.6, 1.6, 1.6], { highlight: [T] }),
  CAP("표 C3. WQL"),
  table(["모델", ...U], A.index.map((m) => [m, ...U.map((u) => f3(get(pw, m, u)))]), [2.6, 1.6, 1.6, 1.6, 1.6], { highlight: [T] }),
];
const doc = new Document({
  styles: {
    default: { document: { run: { font: FONT, size: 21 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 30, bold: true, color: "0B0B0B" }, paragraph: { spacing: { before: 360, after: 140 }, keepNext: true, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 25, bold: true, color: "1F4E8C" }, paragraph: { spacing: { before: 240, after: 100 }, keepNext: true, outlineLevel: 1 } },
    ],
  },
  numbering: { config: [
    { reference: "bul", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 400, hanging: 260 } } } }] },
    { reference: "num2", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 400, hanging: 300 } } } }] },
    { reference: "num", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 400, hanging: 300 } } } }] },
  ] },
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
      children: [new TextRun({ children: ["SpendRadar TimesFM 검증 보고서 · ", PageNumber.CURRENT], font: FONT, size: 16, color: INK2 })] })] }) },
    children,
  }],
});
Packer.toBuffer(doc).then((b) => { fs.mkdirSync(__dirname + "/../report", { recursive: true }); fs.writeFileSync(__dirname + "/../report/SpendRadar_TimesFM_검증보고서.docx", b); console.log("written"); });
