# -*- coding: utf-8 -*-
"""핫 섹터(지난 1개월 수익률 상위 5개) 안에서 종목 등급별 4주 성과 비교."""
import sys, sqlite3, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
sys.path.insert(0, "/Users/byunjungwon/Dev/my-project-01/my_chart")
from my_chart.registry import get_sector_registry
DB = "/Users/byunjungwon/Dev/my-project-01/my_chart/Output/stock_data_weekly.db"
H = int(sys.argv[1]) if len(sys.argv) > 1 else 4
c = sqlite3.connect(DB)
px = pd.read_sql("SELECT Name, Date, Close, Volume, RS_1M, RS_3M, RS_6M, RS_9M, RS_12M FROM stock_prices", c)
px = px[~px.Name.isin(["KOSPI","KOSDAQ"])]
reg = get_sector_registry()[["Name","Market","산업명(대)"]].drop_duplicates("Name").set_index("Name")
px = px.join(reg, on="Name").dropna(subset=["산업명(대)"])
iso = pd.to_datetime(px.Date).dt.isocalendar(); px["_wk"] = iso.year.astype(str)+"-"+iso.week.astype(str)
px = px[px.Date == px.groupby("_wk").Date.transform("max")]
px["tv"] = px.Close*px.Volume
px = px.sort_values(["Name","Date"]); g = px.groupby("Name")
px["fwd"] = g.Close.shift(-H)/px.Close - 1
px["tv20"] = g.tv.transform(lambda s: s.rolling(20, min_periods=8).mean())
px = px[px.tv20 >= 5e9]
dates = sorted(px.Date.unique()); by_date = {d: s for d, s in px.groupby("Date")}
def pr(s): return s.rank(pct=True)*100
SC = {
  "현행(1M 33%)": lambda d: pr(pr(d.RS_1M)+.8*pr(d.RS_3M)+.6*pr(d.RS_6M)+.4*pr(d.RS_9M)+.2*pr(d.RS_12M)),
  "1M 단독":      lambda d: pr(d.RS_1M),
  "3M 단독":      lambda d: pr(d.RS_3M),
  "6M 단독":      lambda d: pr(d.RS_6M),
  "12M 단독":     lambda d: pr(d.RS_12M),
  "IBD식":        lambda d: pr(2*d.RS_3M + ((1+d.RS_6M)/(1+d.RS_3M)-1) + ((1+d.RS_9M)/(1+d.RS_6M)-1) + ((1+d.RS_12M)/(1+d.RS_9M)-1)),
}
rows = {k: dict(top=[], mean=[], hit=[], cov=[], hot_mean=[], univ_mean=[]) for k in SC}
for d in dates[52:-H]:
    day = by_date[d].dropna(subset=["RS_1M","RS_3M","RS_6M","RS_9M","RS_12M","fwd"])
    if len(day) < 200: continue
    sec = day.groupby("산업명(대)").agg(r1m=("RS_1M","mean"), n=("Name","size"))
    sec = sec[sec.n >= 5]
    if len(sec) < 10: continue
    hot = sec.r1m.sort_values(ascending=False).head(5).index
    members = day[day["산업명(대)"].isin(hot)]
    for k, fn in SC.items():
        s = fn(day)                                   # 전체 유니버스 기준 등급 (화면과 동일)
        m = members.assign(score=s[members.index].values)
        top = m[m.score >= 80]                        # 핫 섹터 안에서 RS 80 이상인 종목
        if len(top) < 3: continue
        rows[k]["top"].append(top.fwd.mean()); rows[k]["mean"].append(m.fwd.mean())
        rows[k]["hit"].append(top.fwd.mean() > m.fwd.mean())
        rows[k]["cov"].append(len(top)/len(m))        # 핫 섹터 종목 중 RS80+ 비율 (등급이 핫 섹터를 얼마나 '잡아주나')
out = []
for k, r in rows.items():
    out.append(dict(등급=k, 주수=len(r["top"]),
        핫섹터_RS80이상_비율=100*np.mean(r["cov"]),
        RS80이상_vs_핫섹터평균pp=100*(np.mean(r["top"])-np.mean(r["mean"])),
        승률=100*np.mean(r["hit"])))
print(f"=== 핫 섹터(지난 1개월 상위 5개) 내부 | 향후 {H}주 | 거래대금 50억 이상 ===")
print(pd.DataFrame(out).set_index("등급").round(2).to_string())
