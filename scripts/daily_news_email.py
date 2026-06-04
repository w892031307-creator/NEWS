from __future__ import annotations

import html
import os
import smtplib
import ssl
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from email.utils import formatdate
from typing import Iterable
from urllib.parse import quote_plus

import feedparser


TZ_CN = timezone(timedelta(hours=8))
MAX_ITEMS_PER_TOPIC = 5
RECENT_HOURS = 24


TOPICS = [
    {
        "name": "中国政治新闻",
        "query": "中国 政治 OR 政策 OR 外交 OR 国务院 OR 全国人大",
    },
    {
        "name": "国际政治新闻",
        "query": "国际 政治 OR 外交 OR election OR summit OR war",
    },
    {
        "name": "中国财经新闻",
        "query": "中国 经济 OR 财经 OR 央行 OR A股 OR 人民币 OR 房地产",
    },
    {
        "name": "国际财经新闻",
        "query": "全球 经济 OR 美联储 OR 美股 OR oil OR inflation OR markets",
    },
]


@dataclass(frozen=True)
class NewsItem:
    title: str
    link: str
    source: str
    published: datetime | None
    summary: str


def env(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def google_news_rss_url(query: str) -> str:
    encoded = quote_plus(f"{query} when:1d")
    return (
        "https://news.google.com/rss/search"
        f"?q={encoded}&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"
    )


def parse_datetime(entry: object) -> datetime | None:
    parsed = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
    if not parsed:
        return None
    return datetime(*parsed[:6], tzinfo=timezone.utc).astimezone(TZ_CN)


def clean_text(value: str) -> str:
    return " ".join(html.unescape(value or "").split())


def fetch_topic(query: str) -> list[NewsItem]:
    feed = feedparser.parse(google_news_rss_url(query))
    cutoff = datetime.now(TZ_CN) - timedelta(hours=RECENT_HOURS)
    items: list[NewsItem] = []
    seen_links: set[str] = set()

    for entry in feed.entries:
        link = clean_text(getattr(entry, "link", ""))
        if not link or link in seen_links:
            continue

        published = parse_datetime(entry)
        if published and published < cutoff:
            continue

        source = clean_text(getattr(getattr(entry, "source", None), "title", "")) or "Google News"
        items.append(
            NewsItem(
                title=clean_text(getattr(entry, "title", "无标题")),
                link=link,
                source=source,
                published=published,
                summary=clean_text(getattr(entry, "summary", "")),
            )
        )
        seen_links.add(link)
        if len(items) >= MAX_ITEMS_PER_TOPIC:
            break

    return items


def item_time(item: NewsItem) -> str:
    if not item.published:
        return "时间未标注"
    return item.published.strftime("%m-%d %H:%M")


def impact_hint(topic: str, title: str) -> str:
    text = title.lower()
    if "央行" in title or "美联储" in title or "inflation" in text:
        return "关注利率、汇率和市场预期变化。"
    if "股" in title or "markets" in text or "oil" in text:
        return "关注资产价格和风险偏好变化。"
    if "外交" in title or "summit" in text or "war" in text:
        return "关注地缘关系、贸易与安全议题外溢。"
    if "政策" in title or "国务院" in title:
        return "关注政策落地节奏和行业影响。"
    if "财经" in topic or "经济" in topic:
        return "关注宏观数据、企业经营和市场情绪。"
    return "关注后续政策、市场和国际关系影响。"


def render_text(sections: dict[str, list[NewsItem]]) -> str:
    today = datetime.now(TZ_CN).strftime("%Y-%m-%d")
    lines = [f"中文晨间新闻简报 | {today}", ""]

    for topic, items in sections.items():
        lines.append(f"## {topic}")
        if not items:
            lines.append("今天未抓取到最近 24 小时内的可靠 RSS 条目。")
            lines.append("")
            continue

        for index, item in enumerate(items, 1):
            lines.append(f"{index}. {item.title}")
            lines.append(f"   - 时间：{item_time(item)}")
            lines.append(f"   - 来源：{item.source}")
            lines.append(f"   - 影响：{impact_hint(topic, item.title)}")
            lines.append(f"   - 链接：{item.link}")
        lines.append("")

    lines.append("注：本邮件由云端定时任务自动生成，新闻按 RSS 可获取条目整理。")
    return "\n".join(lines)


def render_html(sections: dict[str, list[NewsItem]]) -> str:
    today = datetime.now(TZ_CN).strftime("%Y-%m-%d")
    body = [
        "<!doctype html>",
        "<html><body style=\"font-family: Arial, 'Microsoft YaHei', sans-serif; line-height: 1.6; color: #1f2937;\">",
        f"<h1 style=\"font-size: 22px;\">中文晨间新闻简报 | {today}</h1>",
    ]

    for topic, items in sections.items():
        body.append(f"<h2 style=\"font-size: 18px; border-bottom: 1px solid #e5e7eb; padding-bottom: 6px;\">{html.escape(topic)}</h2>")
        if not items:
            body.append("<p>今天未抓取到最近 24 小时内的可靠 RSS 条目。</p>")
            continue

        body.append("<ol>")
        for item in items:
            body.append("<li style=\"margin-bottom: 14px;\">")
            body.append(f"<strong>{html.escape(item.title)}</strong><br>")
            body.append(f"时间：{html.escape(item_time(item))}<br>")
            body.append(f"来源：{html.escape(item.source)}<br>")
            body.append(f"影响：{html.escape(impact_hint(topic, item.title))}<br>")
            body.append(f"<a href=\"{html.escape(item.link)}\">查看原文</a>")
            body.append("</li>")
        body.append("</ol>")

    body.append("<p style=\"color: #6b7280; font-size: 12px;\">本邮件由云端定时任务自动生成，新闻按 RSS 可获取条目整理。</p>")
    body.append("</body></html>")
    return "\n".join(body)


def collect_sections() -> dict[str, list[NewsItem]]:
    return {topic["name"]: fetch_topic(topic["query"]) for topic in TOPICS}


def send_email(subject: str, text_body: str, html_body: str) -> None:
    smtp_host = env("SMTP_HOST")
    smtp_port = int(env("SMTP_PORT", "465"))
    smtp_username = env("SMTP_USERNAME")
    smtp_password = env("SMTP_PASSWORD")
    mail_to = env("MAIL_TO")
    mail_from = env("MAIL_FROM", smtp_username)

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = mail_from
    message["To"] = mail_to
    message["Date"] = formatdate(localtime=True)
    message.set_content(text_body)
    message.add_alternative(html_body, subtype="html")

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context, timeout=30) as smtp:
        smtp.login(smtp_username, smtp_password)
        smtp.send_message(message)


def main() -> None:
    sections = collect_sections()
    today = datetime.now(TZ_CN).strftime("%Y-%m-%d")
    subject = f"中文晨间新闻简报 - {today}"
    send_email(subject, render_text(sections), render_html(sections))


if __name__ == "__main__":
    main()
