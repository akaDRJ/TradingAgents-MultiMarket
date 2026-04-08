from __future__ import annotations

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

    def get_news(self, ticker: str, start_date: str, end_date: str, **kwargs):
        root = self._fetch_feed(f"{ticker} crypto OR cryptocurrency")
        items = root.findall(".//item")[:8]
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

    def get_global_news(self, curr_date: str, look_back_days: int = 7, limit: int = 5, **kwargs):
        root = self._fetch_feed("bitcoin OR ethereum OR crypto market")
        items = root.findall(".//item")[:limit]
        lines = [f"## Global Crypto News up to {curr_date}:", ""]
        for item in items:
            lines.append(f"- {item.findtext('title', default='Untitled')}")
        return "\n".join(lines)
