#!/usr/bin/env python3
"""Fetch GitHub contribution data via the GraphQL API.

Requires a GitHub Personal Access Token with the ``read:user`` scope stored
in the ``GITHUB_TOKEN`` environment variable.  This gives access to both
public **and** private contribution counts — matching the number shown on
your own logged-in GitHub profile.

Falls back to the unauthenticated public scrape endpoint when no token is
present (public contributions only).

Usage
-----
    export GITHUB_TOKEN=ghp_...
    python3 scripts/fetch_contributions.py

Output: ``data/contributions.json``
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DEFAULT_USERNAME = "VeeratiAnudeepReddy"
DEFAULT_OUTPUT = "data/contributions.json"
GRAPHQL_URL = "https://api.github.com/graphql"
PUBLIC_URL = "https://github.com/users/{username}/contributions"
MAX_LEVEL = 4

# Map GraphQL contributionLevel strings -> int level (0-4)
_LEVEL_MAP = {
    "NONE": 0,
    "FIRST_QUARTILE": 1,
    "SECOND_QUARTILE": 2,
    "THIRD_QUARTILE": 3,
    "FOURTH_QUARTILE": 4,
}

# GraphQL query — fetches the full contribution calendar including private
GRAPHQL_QUERY = """
query($username: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $username) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
            contributionLevel
          }
        }
      }
    }
  }
}
"""


def _create_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/126.0.0.0 Safari/537.36"
        ),
    })
    retry = Retry(total=3, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


# ---------------------------------------------------------------------------
# GraphQL path (authenticated — includes private contributions)
# ---------------------------------------------------------------------------

def fetch_via_graphql(username: str, token: str) -> list[dict]:
    """Fetch contribution data using the GitHub GraphQL API."""
    now = datetime.now(timezone.utc)
    # GitHub's contributionsCollection accepts an ISO-8601 datetime range.
    # We fetch the last 12 months.
    from_dt = now.replace(year=now.year - 1).isoformat()
    to_dt = now.isoformat()

    session = _create_session()
    session.headers["Authorization"] = f"Bearer {token}"
    session.headers["Content-Type"] = "application/json"

    payload = {
        "query": GRAPHQL_QUERY,
        "variables": {"username": username, "from": from_dt, "to": to_dt},
    }

    print("Fetching contributions via GitHub GraphQL API (authenticated)...")
    resp = session.post(GRAPHQL_URL, json=payload, timeout=30)
    resp.raise_for_status()

    body = resp.json()
    if "errors" in body:
        raise RuntimeError(f"GraphQL errors: {body['errors']}")

    calendar = (
        body["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    )

    days: list[dict] = []
    for week in calendar["weeks"]:
        for day_data in week["contributionDays"]:
            date_str = day_data["date"]
            count = day_data["contributionCount"]
            level = _LEVEL_MAP.get(day_data["contributionLevel"], 0)
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            days.append({
                "date": date_str,
                "count": count,
                "level": level,
                "month": date_obj.strftime("%b"),
            })

    days.sort(key=lambda d: d["date"])
    print(f"  GraphQL returned {sum(d['count'] for d in days)} contributions "
          f"({calendar['totalContributions']} per API total).")
    return days


# ---------------------------------------------------------------------------
# Public scrape fallback (unauthenticated — public contributions only)
# ---------------------------------------------------------------------------

def _parse_count_from_tooltip(text: str | None) -> int:
    if not text:
        return 0
    m = re.search(r"^(\d+|No)\s+contribution", text.strip(), re.IGNORECASE)
    if not m:
        return 0
    v = m.group(1)
    return 0 if v.lower() == "no" else int(v)


def fetch_via_scrape(username: str) -> list[dict]:
    """Fallback: scrape the public contribution graph (no token needed)."""
    url = PUBLIC_URL.format(username=username)
    print(f"No GITHUB_TOKEN found — falling back to public scrape: {url}")
    print("WARNING: Private contributions will NOT be included.")

    session = _create_session()
    resp = session.get(url, timeout=30)
    resp.raise_for_status()
    html = resp.text

    soup = BeautifulSoup(html, "html.parser")

    tooltip_map: dict[str, str] = {}
    for t in soup.find_all("tool-tip"):
        fid = t.get("for") or t.get("data-target")
        if fid:
            tooltip_map[fid] = t.get_text(strip=True)

    days: list[dict] = []
    seen: set[str] = set()

    for cell in soup.find_all("td", {"data-date": True}):
        date_str = cell.get("data-date")
        if not date_str or date_str in seen:
            continue
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            continue

        level = int(cell.get("data-level", 0) or 0)
        level = max(0, min(level, MAX_LEVEL))
        tip = tooltip_map.get(cell.get("id", ""), "")
        count = _parse_count_from_tooltip(tip)

        days.append({
            "date": date_str,
            "count": count,
            "level": level,
            "month": date_obj.strftime("%b"),
        })
        seen.add(date_str)

    days.sort(key=lambda d: d["date"])
    print(f"  Scraper returned {sum(d['count'] for d in days)} public contributions.")
    return days


# ---------------------------------------------------------------------------
# Stats computation (unchanged)
# ---------------------------------------------------------------------------

def compute_stats(days: list[dict]) -> dict:
    total = sum(d["count"] for d in days)
    longest = current = run = 0

    for d in days:
        if d["count"] > 0:
            run += 1
            longest = max(longest, run)
        else:
            run = 0

    if days and days[-1]["count"] > 0:
        for d in reversed(days):
            if d["count"] > 0:
                current += 1
            else:
                break

    best_day = None
    if days:
        mx = max(d["count"] for d in days)
        if mx > 0:
            b = next(d for d in days if d["count"] == mx)
            best_day = {"date": b["date"], "count": b["count"]}

    monthly: dict[str, int] = {}
    for d in days:
        monthly[d["month"]] = monthly.get(d["month"], 0) + d["count"]

    return {
        "total_contributions": total,
        "current_streak": current,
        "longest_streak": longest,
        "best_day": best_day,
        "monthly_totals": monthly,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fetch GitHub contribution data (GraphQL API or public scrape)."
    )
    parser.add_argument("--username", "-u", default=DEFAULT_USERNAME)
    parser.add_argument("--output", "-o", default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    token = os.environ.get("GITHUB_TOKEN", "").strip()

    try:
        if token:
            days = fetch_via_graphql(args.username, token)
        else:
            days = fetch_via_scrape(args.username)

        stats = compute_stats(days)
        print(f"  Total: {stats['total_contributions']} | "
              f"Streak: {stats['current_streak']} days | "
              f"Longest: {stats['longest_streak']} days")

        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "username": args.username,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "source": "graphql" if token else "scrape",
            "days": days,
            "stats": stats,
        }
        output.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
        print(f"Saved {output}")

    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
