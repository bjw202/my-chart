# -*- coding: utf-8 -*-
import sys, sqlite3, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
sys.path.insert(0, "/Users/byunjungwon/Dev/my-project-01/my_chart")
from my_chart.registry import get_sector_registry
DB = "/Users/byunjungwon/Dev/my-project-01/my_chart/Output/stock_data_weekly.db"
c = sqlite3.connect(DB)
px = pd.read_sql("SELECT Name, Date, Close, Volume FROM stock_prices", c)
px = px[~px.Name.isin(["KOSPI","KOSDAQ"])]
reg = get_sector_registry()[["Name","산업명(대)"]].drop_duplicates("Name").set_index("Name")
px = px.join(reg, on="Name").dropna(subset=["산업명(대)"])

_iso = pd.to_datetime(px.Date).dt.isocalendar()
px["_wk"] = _iso.year.astype(str) + "-" + _iso.week.astype(str)
_last = px.groupby("_wk").Date.transform("max")
px = px[px.Date == _last].drop(columns="_wk")
px["tv"] = px.Close*px.Volume
px = px.sort_values(["Name","Date"])
px["tv20"] = px.groupby("Name").tv.transform(lambda s: s.rolling(20,min_periods=8).mean())
px = px[px.tv20 >= 5e9]
px["r1w"] = px.groupby("Name").Close.pct_change(1)
# sector equal-weight weekly return → chain index
sec = px.groupby(["Date","산업명(대)"]).agg(r=("r1w","mean"), n=("Name","size")).reset_index()
sec = sec[sec.n>=5]
idx = sec.pivot(index="Date", columns="산업명(대)", values="r").sort_index()
level = (1+idx.fillna(0)).cumprod()
look = {"1주":1,"2주":2,"1개월":4,"2개월":8,"3개월":12,"6개월":26,"12개월":52}
def pr(df): return df.rank(axis=1, pct=True)*100
feats = {k: level.pct_change(v) for k,v in look.items()}
feats["현행 섹터종합(1w30/1m40/3m30)"] = .3*pr(feats["1주"]) + .4*pr(feats["1개월"]) + .3*pr(feats["3개월"])
feats["1개월+3개월 등가중"] = pr(feats["1개월"]) + pr(feats["3개월"])
feats["3개월+6개월 등가중"] = pr(feats["3개월"]) + pr(feats["6개월"])
feats["12-1 모멘텀"] = (1+feats["12개월"])/(1+feats["1개월"])-1
for H in (2,4,8):
    fwd = level.shift(-H)/level - 1
    rows=[]
    for name,f in feats.items():
        ex, win, persist, ic = [],[],[],[]
        tops={}
        for d in level.index[52:-H]:
            s = f.loc[d].dropna(); fr = fwd.loc[d].dropna()
            common = s.index.intersection(fr.index)
            if len(common)<10: continue
            s=s[common]; fr=fr[common]
            top = s.sort_values(ascending=False).head(5).index
            ex.append(fr[top].mean()-fr.median()); win.append(fr[top].mean()>fr.median())
            ic.append(s.rank().corr(fr.rank()))
            tops[d]=set(top)
            pd_=level.index[list(level.index).index(d)-H]
            if pd_ in tops: persist.append(len(tops[pd_]&set(top))/5)
        rows.append(dict(과거창=name, top5_초과pp=100*np.mean(ex), top5_승률=100*np.mean(win), IC=np.mean(ic), IC양수=100*np.mean(np.array(ic)>0), top5_지속률=100*np.mean(persist)))
    print(f"\n=== 섹터 수준 | 향후 {H}주 | 거래대금 50억 이상, 멤버 5개 이상 섹터 ===")
    print(pd.DataFrame(rows).set_index("과거창").round(2).to_string())
