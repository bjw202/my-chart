# -*- coding: utf-8 -*-
"""RS 공식 비교 실증 — 현재 공식 vs 대안, 종목/섹터 수준."""
import sys, sqlite3, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
sys.path.insert(0, "/Users/byunjungwon/Dev/my-project-01/my_chart")
from my_chart.registry import get_sector_registry

DB = "/Users/byunjungwon/Dev/my-project-01/my_chart/Output/stock_data_weekly.db"
H = int(sys.argv[1]) if len(sys.argv) > 1 else 4

c = sqlite3.connect(DB)
px = pd.read_sql("SELECT Name, Date, Close, Volume, RS_1M, RS_3M, RS_6M, RS_9M, RS_12M FROM stock_prices", c)
px = px[~px.Name.isin(["KOSPI", "KOSDAQ"])]
reg = get_sector_registry()[["Name", "Market", "산업명(대)"]].drop_duplicates("Name").set_index("Name")
px = px.join(reg, on="Name")

_iso = pd.to_datetime(px.Date).dt.isocalendar()
px["_wk"] = _iso.year.astype(str) + "-" + _iso.week.astype(str)
_last = px.groupby("_wk").Date.transform("max")
px = px[px.Date == _last].drop(columns="_wk")
px["tv"] = px.Close * px.Volume
px = px.sort_values(["Name", "Date"])
dates = sorted(px.Date.unique())
pos = {d: i for i, d in enumerate(dates)}
g = px.groupby("Name")
px["fwd"] = g.Close.shift(-H) / px.Close - 1
px["fwd_d"] = g.Close.shift(-H-1) / g.Close.shift(-1) - 1  # 1주 지연 진입
px["tv20"] = g.tv.transform(lambda s: s.rolling(20, min_periods=8).mean())
by_date = {d: sub for d, sub in px.groupby("Date")}

def pr(s): return s.rank(pct=True) * 100
def score_current(d):
    r1, r3, r6, r9, r12 = (pr(d[k]) for k in ["RS_1M", "RS_3M", "RS_6M", "RS_9M", "RS_12M"])
    return pr(r1 + .8*r3 + .6*r6 + .4*r9 + .2*r12)
def score_ibd(d):
    q1 = d.RS_3M; q2 = (1+d.RS_6M)/(1+d.RS_3M)-1; q3 = (1+d.RS_9M)/(1+d.RS_6M)-1; q4 = (1+d.RS_12M)/(1+d.RS_9M)-1
    return pr(2*q1 + q2 + q3 + q4)
def score_3m(d): return pr(d.RS_3M)
def score_6m(d): return pr(d.RS_6M)
def score_12_1(d): return pr((1+d.RS_12M)/(1+d.RS_1M)-1)
def score_3_6_eq(d): return pr(pr(d.RS_3M)+pr(d.RS_6M))
def score_cur_no1m(d): return pr(.8*pr(d.RS_3M)+.6*pr(d.RS_6M)+.4*pr(d.RS_9M)+.2*pr(d.RS_12M))
def score_1m(d): return pr(d.RS_1M)

def score_codex(d): return pr(.2*pr(d.RS_1M)+.5*pr(d.RS_3M)+.3*pr(d.RS_6M))
def score_6_1(d): return pr((1+d.RS_6M)/(1+d.RS_1M)-1)
def score_3_1(d): return pr((1+d.RS_3M)/(1+d.RS_1M)-1)
def score_12m(d): return pr(d.RS_12M)
SCORES = {
    "12M 단독": score_12m,
    "codex안(1M20/3M50/6M30)": score_codex,
    "6-1 모멘텀": score_6_1,
    "3-1 모멘텀": score_3_1,
    "현행(1M 33%가중)": score_current,
    "현행에서 1M 제거": score_cur_no1m,
    "1M 단독": score_1m,
    "3M 단독": score_3m,
    "6M 단독": score_6m,
    "3M+6M 등가중": score_3_6_eq,
    "IBD식(최근분기 40%)": score_ibd,
    "12-1 모멘텀": score_12_1,
}

def evaluate(filter_name, mask_fn):
    rows = []
    for name, fn in SCORES.items():
        top_sets = {}
        fwd_top, fwd_bot, fwd_med, ics, persist, sec_top, sec_med = [], [], [], [], [], [], []
        fwd_mean, d_top, d_mean = [], [], []
        for d in dates[52:-H]:
            day = by_date[d].dropna(subset=["RS_1M","RS_3M","RS_6M","RS_9M","RS_12M","fwd","fwd_d"])
            day = day[mask_fn(day)]
            if len(day) < 200: continue
            day = day.assign(score=fn(day).values)
            top = day[day.score >= 90]; bot = day[day.score <= 10]
            fwd_top.append(top.fwd.mean()); fwd_mean.append(day.fwd.mean()); d_top.append(top.fwd_d.mean()); d_mean.append(day.fwd_d.mean()); fwd_bot.append(bot.fwd.mean()); fwd_med.append(day.fwd.median())
            ics.append(day[["score","fwd"]].corr(method="spearman").iloc[0,1])
            top_sets[d] = set(top.Name)
            prev = dates[pos[d]-H]
            if prev in top_sets and top_sets[prev]:
                persist.append(len(top_sets[prev] & set(top.Name))/len(top_sets[prev]))
            sec = day.groupby("산업명(대)").agg(score=("score","mean"), fwd=("fwd","mean"), n=("Name","size"))
            sec = sec[sec.n >= 5]
            if len(sec) >= 10:
                top5 = sec.sort_values("score", ascending=False).head(5)
                sec_top.append(top5.fwd.mean()); sec_med.append(sec.fwd.median())
        rows.append(dict(공식=name, 주수=len(fwd_top),
            상위10_초과pp=100*(np.mean(fwd_top)-np.mean(fwd_med)),
            상하위스프레드pp=100*(np.mean(fwd_top)-np.mean(fwd_bot)), 상위10_vs평균pp=100*(np.mean(fwd_top)-np.mean(fwd_mean)), 지연진입_vs평균pp=100*(np.mean(d_top)-np.mean(d_mean)),
            IC양수비율=100*np.mean(np.array(ics)>0),
            상위10_지속률=100*np.mean(persist),
            ))
    df = pd.DataFrame(rows).set_index("공식").round(2)
    print(f"\n=== 필터: {filter_name} | 향후 {H}주 ===")
    print(df.to_string())


evaluate("20주 평균 주간거래대금 >= 50억", lambda d: d.tv20 >= 5e9)


