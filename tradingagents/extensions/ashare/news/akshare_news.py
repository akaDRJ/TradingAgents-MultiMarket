"""AKShare-backed news formatting helpers for A-share symbols."""

from datetime import datetime
from dateutil.relativedelta import relativedelta
import pandas as pd


def format_stock_news(df: pd.DataFrame, ticker: str, start_date: str, end_date: str) -> str:
    if df is None or df.empty:
        return f"No news found for {ticker}"

    out = df.copy()
    if "发布时间" in out.columns:
        pub = pd.to_datetime(out["发布时间"], errors="coerce")
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date) + relativedelta(days=1)
        out = out[(pub >= start_dt) & (pub <= end_dt)]

    if out.empty:
        return f"No news found for {ticker} between {start_date} and {end_date}"

    lines = []
    for _, row in out.iterrows():
        title = row.get("新闻标题", "No title")
        summary = row.get("新闻内容", "")
        source = row.get("文章来源", "Unknown")
        link = row.get("新闻链接", "")
        published = row.get("发布时间", "")
        lines.append(f"### {title} (source: {source})")
        if published:
            lines.append(f"Published: {published}")
        if summary:
            lines.append(str(summary))
        if link:
            lines.append(f"Link: {link}")
        lines.append("")

    return f"## {ticker} News, from {start_date} to {end_date}:\n\n" + "\n".join(lines)
