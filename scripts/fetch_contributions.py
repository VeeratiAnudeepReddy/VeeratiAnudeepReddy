#!/usr/bin/env python3
"""Fetch public GitHub contribution data without authentication.

This script scrapes the public contribution calendar from GitHub's
``/users/{username}/contributions`` endpoint, parses each day's activity,
and writes the data plus summary statistics to ``data/contributions.json``.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
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
CONTRIBUTIONS_URL = "https://github.com/users/{username}/contributions"

# GitHub uses a 0-4 level scale for contribution intensity.
MAX_LEVEL = 4


def _create_session() -> requests.Session:
    """Create a requests session with retries and a browser-like User-Agent."""
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
    )

    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    return session


def fetch_contributions(username: str) -> str:
    """Download the public contribution graph HTML for a GitHub user.

    Args:
        username: The GitHub username to fetch.

    Returns:
        Raw HTML of the contribution calendar page.

    Raises:
        requests.RequestException: If the request fails after retries.
        ValueError: If GitHub returns a non-success status code.
    """
    url = CONTRIBUTIONS_URL.format(username=username)
    session = _create_session()

    try:
        response = session.get(url, timeout=30)
    except requests.RequestException as exc:
        raise requests.RequestException(
            f"Failed to download contribution graph for {username}: {exc}"
        ) from exc

    if response.status_code != 200:
        raise ValueError(
            f"GitHub returned status {response.status_code} for {url}. "
            "The user may not exist or the request may have been blocked."
        )

    return response.text


def _parse_count_from_tooltip(tooltip_text: str | None) -> int:
    """Extract the contribution count from a GitHub tool-tip string.

    Examples:
        - "No contributions on July 20, 2025." -> 0
        - "1 contribution on July 19, 2025." -> 1
        - "5 contributions on July 18, 2025." -> 5

    Args:
        tooltip_text: The raw tool-tip text.

    Returns:
        The integer contribution count.
    """
    if not tooltip_text:
        return 0

    match = re.search(r"^(\d+|No)\s+contribution", tooltip_text.strip(), re.IGNORECASE)
    if not match:
        return 0

    value = match.group(1)
    return 0 if value.lower() == "no" else int(value)


def parse_contributions(html: str) -> list[dict]:
    """Parse contribution days from the GitHub contribution HTML.

    Args:
        html: Raw HTML from GitHub's contributions endpoint.

    Returns:
        A list of contribution-day dictionaries, sorted by date.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Build a map from day element id -> tool-tip text.
    tooltip_map: dict[str, str] = {}
    for tooltip in soup.find_all("tool-tip"):
        target_id = tooltip.get("for") or tooltip.get("data-target")
        if target_id:
            tooltip_map[target_id] = tooltip.get_text(strip=True)

    days: list[dict] = []
    seen_dates: set[str] = set()

    for cell in soup.find_all("td", {"data-date": True}):
        date_str = cell.get("data-date")
        if not date_str or date_str in seen_dates:
            continue

        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            continue

        level = int(cell.get("data-level", 0) or 0)
        level = max(0, min(level, MAX_LEVEL))

        tooltip_text = tooltip_map.get(cell.get("id", ""), "")
        count = _parse_count_from_tooltip(tooltip_text)

        days.append(
            {
                "date": date_str,
                "count": count,
                "level": level,
                "month": date_obj.strftime("%b"),
            }
        )
        seen_dates.add(date_str)

    days.sort(key=lambda d: d["date"])
    return days


def compute_stats(days: list[dict]) -> dict:
    """Compute aggregate statistics from a list of contribution days.

    Args:
        days: Contribution-day dictionaries sorted by date.

    Returns:
        A dictionary of summary statistics.
    """
    total_contributions = sum(day["count"] for day in days)

    # Longest streak and current streak.
    longest_streak = 0
    current_streak = 0
    active_run = 0

    for day in days:
        if day["count"] > 0:
            active_run += 1
            longest_streak = max(longest_streak, active_run)
        else:
            active_run = 0

    # Current streak ends at the last recorded day.
    if days and days[-1]["count"] > 0:
        current_streak = 0
        for day in reversed(days):
            if day["count"] > 0:
                current_streak += 1
            else:
                break

    # Best day (earliest date in case of ties).
    best_day: dict | None = None
    if days:
        max_count = max(day["count"] for day in days)
        if max_count > 0:
            best = next(day for day in days if day["count"] == max_count)
            best_day = {"date": best["date"], "count": best["count"]}

    # Monthly totals using abbreviated month labels.
    monthly_totals: dict[str, int] = {}
    for day in days:
        month = day["month"]
        monthly_totals[month] = monthly_totals.get(month, 0) + day["count"]

    return {
        "total_contributions": total_contributions,
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "best_day": best_day,
        "monthly_totals": monthly_totals,
    }


def build_contribution_data(username: str, days: list[dict]) -> dict:
    """Assemble the final JSON payload.

    Args:
        username: GitHub username.
        days: Parsed contribution days.

    Returns:
        Dictionary ready to be serialized to JSON.
    """
    stats = compute_stats(days)
    return {
        "username": username,
        "generated_at": datetime.now().isoformat(),
        "days": days,
        "stats": stats,
    }


def save_contributions(data: dict, path: str | Path) -> None:
    """Write contribution data to disk as formatted JSON.

    Args:
        data: The data payload to save.
        path: Destination filesystem path.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    """Run the contribution fetching pipeline.

    Args:
        argv: Optional command-line arguments. If ``None``, ``sys.argv`` is used.

    Returns:
        ``0`` on success, ``1`` on failure.
    """
    parser = argparse.ArgumentParser(
        description="Fetch public GitHub contribution data and save it as JSON.",
    )
    parser.add_argument(
        "--username",
        "-u",
        default=DEFAULT_USERNAME,
        help="GitHub username to fetch contributions for.",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=DEFAULT_OUTPUT,
        help="Path to the output JSON file.",
    )
    args = parser.parse_args(argv)

    try:
        print("Downloading contribution graph...")
        html = fetch_contributions(args.username)

        print("Parsing HTML...")
        days = parse_contributions(html)

        if not days:
            print(
                f"Warning: no contribution days found for {args.username}.",
                file=sys.stderr,
            )

        print("Calculating statistics...")
        data = build_contribution_data(args.username, days)

        save_contributions(data, args.output)
        print(f"Saved {args.output}")
    except requests.RequestException as exc:
        print(f"Network error: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # pragma: no cover - last-resort safety net
        print(f"Unexpected error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
