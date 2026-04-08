from __future__ import annotations

from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree

import requests


class PublicNewsProvider:
    name = "public_news"

    def _fetch_feed(self, query: str):
        url = "https://news.google.com/rss/search"
        response = requests.get(
            url,
            params={"q": query, "hl": "en-US", "gl": "US", "ceid": "US:en"},
            timeout=20,
        )
        response.raise_for_status()
        return ElementTree.fromstring(response.content)

    def _parse_pub_date(self, pub_date: str):
        if not pub_date:
            return None
        try:
            parsed = parsedate_to_datetime(pub_date)
        except (TypeError, ValueError):
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)

    def _filter_items_by_date(self, root, start_date: str, end_date: str, limit: int):
        start_day = datetime.fromisoformat(start_date).date()
        end_day = datetime.fromisoformat(end_date).date()
        items = []
        for item in root.findall(".//item"):
            published = self._parse_pub_date(item.findtext("pubDate", default=""))
            if published is None:
                continue
            if start_day <= published.date() <= end_day:
                items.append(item)
            if len(items) >= limit:
                break
        return items

    def get_news(self, ticker: str, start_date: str, end_date: str, **kwargs):
        root = self._fetch_feed(f"{ticker} crypto OR cryptocurrency")
        items = self._filter_items_by_date(root, start_date, end_date, limit=8)
        lines = [f"## {ticker} News, from {start_date} to {end_date}:", ""]
        for item in items:
            title = item.findtext("title", default="Untitled")
            link = item.findtext("link", default="")
            pub_date = item.findtext("pubDate", default="")
            lines.append(f"### {title}")
            if pub_date:
                lines.append(f"Published: {pub_date}")
            if link:
                lines.append(f"Link: {link}")
            lines.append("")
        return "\n".join(lines)

    def get_global_news(
        self,
        ticker_or_curr_date: str,
        curr_date: str | None = None,
        look_back_days: int = 7,
        limit: int = 5,
        **kwargs,
    ):
        if curr_date is None:
            ticker = kwargs.get("ticker")
            curr_date = ticker_or_curr_date
        else:
            ticker = ticker_or_curr_date

        query = "bitcoin OR ethereum OR crypto market"
        if ticker:
            query = f"{ticker} OR {query}"

        root = self._fetch_feed(query)
        start_date = (datetime.fromisoformat(curr_date) - timedelta(days=look_back_days)).date().isoformat()
        items = self._filter_items_by_date(root, start_date, curr_date, limit=limit)
        lines = [f"## Global Crypto News up to {curr_date}:", ""]
        for item in items:
            lines.append(f"- {item.findtext('title', default='Untitled')}")
        return "\n".join(lines)
