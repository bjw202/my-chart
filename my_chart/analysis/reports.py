"""Company analyst report fetcher."""

from __future__ import annotations

import datetime
import json
import time

import numpy as np
import pandas as pd
import requests

from my_chart.registry import _code


def comp_reports(comp_name: str, printing: bool = True) -> pd.DataFrame | None:
    """Fetch and export analyst reports from WiseReport.

    Parameters
    ----------
    comp_name : str
        Korean stock name.
    printing : bool
        Whether to print reports to stdout.

    Returns
    -------
    pd.DataFrame or None
        DataFrame of reports, or None if no data.
    """
    code = _code(comp_name)

    _data = []

    for i in range(1, 21):
        url = (
            f"http://comp.wisereport.co.kr/company/ajax/"
            f"c1080001_data.aspx?cmp_cd={code}&perPage=20&curPage={i}"
        )

        page = requests.get(url)
        decoded_data = page.text.encode().decode("utf-8-sig")
        data = json.loads(decoded_data)

        lists = data["lists"]

        if len(lists) == 0:
            if i == 1:
                return None
            break

        for item in lists:
            날짜 = item["ANL_DT"]
            제목 = item["RPT_TITLE"]
            제공처 = item["BRK_NM_SHORT_KOR"]
            의견 = item["RECOMM"]
            목표가 = item["TARGET_PRC"]
            com = item["COMMENT2"]
            comment = com.split("<span class='comment_text'>▶</span>")[1:]
            summary = [txt.replace("<br/>", "").replace("\r\n", "") for txt in comment]

            요약 = ""
            for j, txt in enumerate(summary):
                prefix = "▶"
                suffix = "\n" if j != len(summary) - 1 else ""
                요약 += prefix + txt + suffix

            if printing:
                print(f"({날짜}) {제공처} {의견} 목표가:{목표가}")
                print(제목)
                print(요약)
                print("")

            _data.append([날짜, 제목, 제공처, 의견, 목표가, 요약])

        time.sleep(1)

    df_reports = pd.DataFrame(
        _data, columns=["날짜", "제목", "제공처", "의견", "목표가", "요약"]
    )

    for idx in range(len(df_reports)):
        d = df_reports.loc[idx, "날짜"]
        df_reports.loc[idx, "날짜"] = datetime.datetime.strptime(d, "%y/%m/%d").date()
    df_reports = df_reports.set_index("날짜")

    df_reports = df_reports[["제공처", "제목", "의견", "목표가", "요약"]]

    for idx in range(len(df_reports)):
        j = df_reports.columns.get_loc("목표가")
        s = df_reports.iloc[idx, j]
        if s != "":
            df_reports.iloc[idx, j] = int(str(s).replace(",", ""))
        else:
            df_reports.iloc[idx, j] = np.nan

    df_reports = df_reports[["제공처", "제목", "의견", "요약"]]

    t = datetime.datetime.today()
    fname = f"{comp_name} 리포트 {t.year}_{t.month}_{t.day}.xlsx"

    with pd.ExcelWriter(fname, engine="xlsxwriter", date_format="YYYY-MM-DD") as writer:
        df_reports.to_excel(writer, sheet_name="Sheet1")

        workbook = writer.book
        worksheet = writer.sheets["Sheet1"]

        date_format = workbook.add_format(
            {"num_format": "yyyy-mm-dd", "align": "center", "valign": "top"}
        )
        txt_format = workbook.add_format({"align": "left", "valign": "top"})
        wrap_format = workbook.add_format({"text_wrap": True})

        worksheet.set_column("A:A", 11, date_format)
        worksheet.set_column("B:B", 12, txt_format)
        worksheet.set_column("C:C", 60, txt_format)
        worksheet.set_column("D:D", 7, txt_format)
        worksheet.set_column("E:E", 180, wrap_format)

    return df_reports
