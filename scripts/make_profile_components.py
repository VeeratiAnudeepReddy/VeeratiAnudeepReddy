#!/usr/bin/env python3
"""Generate the rounded SVG components used by the profile README.

GitHub strips CSS from READMEs, so border-radius is only possible inside
SVG images. Every coloured rectangle here is drawn with ``rx`` so the whole
profile shares one corner radius. Output goes to ``assets/``.
"""

from __future__ import annotations

import argparse
from html import escape
from pathlib import Path

W = 840
RADIUS = 10
CHIP_RADIUS = 6
FONT = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'DejaVu Sans Mono', monospace"
CHAR_W = 7.25  # advance width of the 12px monospace stack

BG = "#0d1117"
CARD = "#161b22"
CHIP = "#21262d"
BORDER = "#30363d"
TEXT = "#e6edf3"
BODY = "#c9d1d9"
DIM = "#8b949e"
GREEN = "#3fb950"
GREEN_SOFT = "#7ee787"
GREEN_BG = "#12261a"
BLUE = "#79c0ff"
BLUE_BG = "#10243a"


def tw(text: str, size: float = 12) -> float:
    return len(text) * CHAR_W * size / 12


def wrap(text: str, width_px: float, size: float = 12) -> list[str]:
    limit = max(10, int(width_px / (CHAR_W * size / 12)))
    lines: list[str] = []
    line = ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if len(trial) <= limit:
            line = trial
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


class Svg:
    def __init__(self, height: float, title: str, width: float = W):
        self.w, self.h = width, height
        self.parts: list[str] = []
        self.title = title

    def rect(self, x, y, w, h, fill, r=RADIUS, stroke=None, sw=1):
        s = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" ry="{r}" fill="{fill}"{s}/>'
        )

    def card(self, x, y, w, h, fill=CARD, r=RADIUS):
        self.rect(x + 0.5, y + 0.5, w - 1, h - 1, fill, r, BORDER)

    def text(self, x, y, s, fill=BODY, size=12, weight="normal", anchor="start"):
        self.parts.append(
            f'<text x="{x}" y="{y}" fill="{fill}" font-family="{FONT}" font-size="{size}" '
            f'font-weight="{weight}" text-anchor="{anchor}">{escape(s)}</text>'
        )

    def chip(self, x, y, label, fill=CHIP, color=BODY, h=24, size=11, r=CHIP_RADIUS) -> float:
        w = tw(label, size) + 18
        self.rect(x, y, w, h, fill, r)
        self.text(x + 9, y + h / 2 + size * 0.35, label, color, size)
        return w

    def chips(self, x, y, labels, max_x, gap=8, h=24, **kw) -> float:
        """Flow chips; returns y after the last row."""
        cx = x
        for label in labels:
            w = tw(label, kw.get("size", 11)) + 18
            if cx + w > max_x:
                cx = x
                y += h + gap
            self.chip(cx, y, label, h=h, **kw)
            cx += w + gap
        return y + h

    def save(self, path: Path):
        body = "\n".join(self.parts)
        path.write_text(
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
            f'viewBox="0 0 {self.w} {self.h}" role="img" aria-label="{escape(self.title)}">\n'
            f"<title>{escape(self.title)}</title>\n{body}\n</svg>\n",
            encoding="utf-8",
        )


# ---------------------------------------------------------------------------
# Components
# ---------------------------------------------------------------------------

def section_header(name: str, cmd: str, path: Path):
    s = Svg(48, name)
    s.text(0, 30, "~", DIM, 14)
    s.text(16, 30, "$", GREEN, 14, "bold")
    s.text(32, 30, cmd, TEXT, 14, "bold")
    s.rect(W - 120, 22, 120, 3, BORDER, 1.5)
    s.rect(W - 120, 22, 40, 3, GREEN, 1.5)
    s.save(path)


def stats(items: list[tuple[str, str]], path: Path):
    gap = 12
    cw = (W - gap * (len(items) - 1)) / len(items)
    s = Svg(92, "Highlights")
    for i, (num, label) in enumerate(items):
        x = i * (cw + gap)
        s.card(x, 0, cw, 92)
        s.rect(x + 18, 20, 20, 3, GREEN, 1.5)
        s.text(x + 18, 56, num, TEXT, 26, "bold")
        s.text(x + 18, 76, label, DIM, 11)
    s.save(path)


def about(rows: list[tuple[str, str]], path: Path):
    pad = 24
    label_w = 120
    lines = [(k, wrap(v, W - pad * 2 - label_w - 8)) for k, v in rows]
    h = 56 + sum(len(v) * 20 + 10 for _, v in lines) + 10
    s = Svg(h, "About")
    s.card(0, 0, W, h)
    for i, c in enumerate(("#ff5f56", "#ffbd2e", "#27c93f")):
        s.parts.append(f'<circle cx="{pad + i * 18}" cy="26" r="5" fill="{c}"/>')
    s.text(pad + 70, 30, "anudeep@profile: ~", DIM, 11)
    y = 66
    for k, vs in lines:
        s.text(pad, y, k, GREEN_SOFT, 12, "bold")
        for j, line in enumerate(vs):
            s.text(pad + label_w, y + j * 20, line, BODY, 12)
        y += len(vs) * 20 + 10
    s.save(path)


def experience(items: list[dict], path: Path):
    pad = 24
    s = Svg(10, "Experience")
    y = 0
    for it in items:
        bullet_lines = [wrap(b, W - pad * 2 - 18) for b in it["bullets"]]
        h = 78 + sum(len(b) * 18 + 6 for b in bullet_lines) + 8
        s.card(0, y, W, h)
        s.text(pad, y + 34, it["title"], TEXT, 14, "bold")
        s.text(pad, y + 54, it["org"], GREEN_SOFT, 12)
        dw = tw(it["date"], 11) + 18
        s.chip(W - pad - dw, y + 18, it["date"], GREEN_BG, GREEN_SOFT)
        by = y + 82
        for lines in bullet_lines:
            s.rect(pad, by - 8, 5, 5, GREEN, 2.5)
            for j, line in enumerate(lines):
                s.text(pad + 18, by + j * 18, line, BODY, 12)
            by += len(lines) * 18 + 6
        y += h + 12
    s.h = y - 12
    s.parts.insert(0, "")
    s.save(path)


def project(p: dict, path: Path):
    pad = 24
    inner = W - pad * 2
    desc = wrap(p["desc"], inner)
    bullets = [wrap(b, inner - 18) for b in p["bullets"]]
    s = Svg(0, p["title"])
    s.text(pad, 36, p["title"], TEXT, 15, "bold")
    s.text(pad, 56, p["sub"], DIM, 11)
    label = p.get("link_label", "GitHub")
    lw = tw(label, 11) + 18
    s.chip(W - pad - lw, 20, label, GREEN_BG, GREEN_SOFT)
    y = 92
    for line in desc:
        s.text(pad, y, line, BODY, 12)
        y += 18
    y += 10
    if p.get("award"):
        s.chip(pad, y, p["award"], BLUE_BG, BLUE)
        y += 24 + 22
    for lines in bullets:
        s.rect(pad, y - 8, 5, 5, GREEN, 2.5)
        for j, line in enumerate(lines):
            s.text(pad + 18, y + j * 18, line, DIM, 12)
        y += len(lines) * 18 + 6
    y += 6
    end = s.chips(pad, y, p["tags"], W - pad)
    s.h = end + 24
    s.parts.insert(0, "")
    s.rect(0.5, 0.5, W - 1, s.h - 1, CARD, RADIUS, BORDER)
    s.parts.insert(0, s.parts.pop())  # card behind content
    s.save(path)


def skills(groups: list[tuple[str, list[str]]], path: Path):
    pad = 24
    label_w = 112
    # first pass for height
    rows = []
    for label, items in groups:
        tmp = Svg(0, "")
        end = tmp.chips(0, 0, items, W - pad * 2 - label_w)
        rows.append(end)
    h = 32 + sum(r + 16 for r in rows)
    s = Svg(h, "Technical skills")
    s.card(0, 0, W, h)
    y = 24
    for (label, items), rh in zip(groups, rows):
        s.text(pad, y + 16, label, GREEN_SOFT, 12, "bold")
        s.chips(pad + label_w, y, items, W - pad)
        y += rh + 16
        if (label, items) != groups[-1]:
            s.rect(pad, y - 9, W - pad * 2, 1, BORDER, 0.5)
    s.save(path)


def achievements(rows: list[tuple[str, str, str, str]], path: Path):
    pad = 20
    rh = 52
    h = len(rows) * (rh + 8) - 8
    s = Svg(h, "Achievements")
    styles = {
        "1st": (GREEN_BG, GREEN_SOFT),
        "2nd": (BLUE_BG, BLUE),
        "FIN": (CHIP, BODY),
        "2★": (CHIP, BODY),
    }
    for i, (rank, award, event, note) in enumerate(rows):
        y = i * (rh + 8)
        s.card(0, y, W, rh)
        bg, fg = styles[rank]
        s.rect(pad, y + 12, 44, 28, bg, 8)
        s.text(pad + 22, y + 31, rank, fg, 12, "bold", "middle")
        s.text(pad + 62, y + 22, award, TEXT, 13, "bold")
        s.text(pad + 62, y + 40, event, DIM, 11)
        s.text(W - pad, y + 31, note, BODY, 11, anchor="end")
    s.save(path)


def twin_lists(left: tuple[str, list[str]], right: tuple[str, list[str]], path: Path):
    gap = 12
    cw = (W - gap) / 2
    pad = 22
    cols = []
    for title, items in (left, right):
        wrapped = [wrap(i, cw - pad * 2 - 16) for i in items]
        cols.append((title, wrapped))
    h = 60 + max(sum(len(w) * 18 + 8 for w in c[1]) for c in cols) + 8
    s = Svg(h, "Certifications and leadership")
    for k, (title, wrapped) in enumerate(cols):
        x = k * (cw + gap)
        s.card(x, 0, cw, h)
        s.text(x + pad, 34, title, TEXT, 13, "bold")
        s.rect(x + pad, 44, 24, 3, GREEN, 1.5)
        y = 72
        for lines in wrapped:
            s.rect(x + pad, y - 8, 5, 5, GREEN, 2.5)
            for j, line in enumerate(lines):
                s.text(x + pad + 16, y + j * 18, line, BODY, 12)
            y += len(lines) * 18 + 8
    s.save(path)


def link_pill(label: str, value: str, path: Path):
    w = tw(label, 11) + tw(value, 12) + 54
    s = Svg(36, f"{label}: {value}", width=round(w))
    s.card(0, 0, w, 36, CARD, 18)
    s.text(18, 23, label, DIM, 11)
    s.text(18 + tw(label, 11) + 14, 23, value, GREEN_SOFT, 12, "bold")
    s.save(path)


# ---------------------------------------------------------------------------
# Content
# ---------------------------------------------------------------------------

U = "VeeratiAnudeepReddy"


def build(out: Path):
    out.mkdir(parents=True, exist_ok=True)

    for slug, cmd in [
        ("about", "cat about.md"),
        ("experience", "git log --experience"),
        ("projects", "ls projects/"),
        ("skills", "cat skills.json"),
        ("achievements", "cat achievements.md"),
        ("activity", "git log --contributions"),
        ("connect", "echo $CONTACT"),
    ]:
        section_header(slug.title(), cmd, out / f"h-{slug}.svg")

    stats(
        [("9.37", "CGPA / 10.0"), ("3x", "1st place wins"), ("10,000+", "hackathon field"), ("29.89%", "traffic wait cut")],
        out / "stats.svg",
    )

    about(
        [
            ("education", "B.Tech Computer Science and Engineering, VNR Vignana Jyothi Institute of Engineering and Technology, Hyderabad (2024-2028). CGPA 9.37 / 10.0"),
            ("role", "Software Development Engineer, Full-Stack + AI/ML"),
            ("workflow", "AI-assisted development with Cursor, Claude Code and GitHub Copilot"),
            ("focus", "Scalable full-stack systems with AI/ML integration"),
            ("location", "Hyderabad, India"),
        ],
        out / "about.svg",
    )

    experience(
        [
            {
                "title": "Full Stack Developer Intern",
                "org": "PSNM Innovations  /  Remote",
                "date": "Feb 2026 - Apr 2026",
                "bullets": [
                    "Architected StudyAI, an AI learning platform that turns study material into 4 formats: explanations, quizzes, flashcards and study plans.",
                    "Engineered REST APIs and LLM-based content generation, delivering the platform within a 3-month internship.",
                    "Created 2 admin tools (analytics dashboard and content-moderation console) to track user activity and platform content.",
                ],
            },
            {
                "title": "Product Team Member, Pothole Mapper",
                "org": "VNR VJIET  /  Hyderabad",
                "date": "2025",
                "bullets": ["Co-developed a community pothole-reporting tool and ran user-feedback cycles to improve usability."],
            },
        ],
        out / "experience.svg",
    )

    projects = [
        {
            "slug": "pondfix",
            "title": "PondFix - Smart Aquaculture Monitoring",
            "sub": "IoT  /  real-time  /  machine learning",
            "desc": "IoT platform that monitors water quality across ponds and streams live readings to web and mobile apps.",
            "bullets": [
                "Tracks 3 water-quality parameters across 17 ponds, streamed live via Socket.io.",
                "Express.js ingestion API validates telemetry into MongoDB, with a simulator for live and anomaly data.",
                "scikit-learn model trained on 72,750+ readings forecasts water quality 3 hours ahead and escalates alerts to automated voice calls.",
                "Multilingual RAG chatbot (Groq, ChromaDB, Sarvam) and a YOLOv8 service that flags inactive fish.",
            ],
            "tags": ["Next.js", "React Native", "Node.js", "Socket.io", "MongoDB", "scikit-learn"],
        },
        {
            "slug": "vision-agent",
            "title": "Privacy-Preserving Vision Agent",
            "sub": "browser agent  /  privacy  /  LLM",
            "desc": "Browser agent that redacts PII locally before any external AI call.",
            "bullets": [
                "Redacts PII locally (OCR, DOM extraction, Presidio/NER) before any external AI call.",
                "Chrome Extension plus FastAPI backend give agents sanitized screen and DOM context.",
                "5-stage pipeline: task parsing, planning, browser actions, verification and failure recovery.",
            ],
            "tags": ["Python", "FastAPI", "Chrome Extension", "OCR", "Presidio"],
        },
        {
            "slug": "traffic",
            "title": "AI-Based Urban Traffic Flow Optimization",
            "sub": "computer vision  /  simulation",
            "desc": "Adaptive signal control that cuts waiting time using real-time vehicle detection.",
            "bullets": [
                "Reduced vehicle waiting time by 29.89% vs. fixed-timing signals in SUMO simulation.",
                "YOLOv8 / OpenCV detection pipeline blending 70% predicted and 30% live traffic data.",
                "Timing engine adjusts green phases by +10s / -11s per direction.",
            ],
            "tags": ["YOLOv8", "OpenCV", "SUMO", "Python"],
            "award": "First Runner-Up, VNR Designathon 2026  /  1st Place, Convergence 2K26",
        },
        {
            "slug": "civix",
            "title": "Civix - Civic Issue Reporting Platform",
            "sub": "full stack  /  geolocation  /  AI validation",
            "desc": "GPS-tagged civic issue reporting with AI report validation and real-time tracking.",
            "bullets": ["Launched the platform with AI report validation, reaching 50+ users in testing."],
            "tags": ["React", "Node.js", "MongoDB"],
            "award": "1st Place, Webathon 4.0  /  1,000+ participants",
        },
        {
            "slug": "railway",
            "title": "AI Railway Optimization Platform",
            "sub": "graph algorithms  /  optimization",
            "desc": "Accessibility-first route finder across the railway network.",
            "bullets": [
                "Mapped 8,737 stations into an accessible route finder covering 64% of the railway network.",
                "Models schedules as time-expanded graphs solved with CP-SAT.",
            ],
            "tags": ["Python", "Graph Algorithms", "CP-SAT"],
        },
    ]
    for p in projects:
        project(p, out / f"project-{p['slug']}.svg")

    skills(
        [
            ("Languages", ["C++", "Java", "Python", "JavaScript", "Kotlin", "C", "SQL", "HTML", "CSS"]),
            ("Frontend", ["React.js", "Next.js", "Tailwind CSS", "Three.js", "React Native", "Flutter", "Android"]),
            ("Backend", ["Node.js", "Express.js", "FastAPI", "REST APIs", "Socket.io"]),
            ("Databases", ["MongoDB", "PostgreSQL", "Firebase", "Supabase", "ChromaDB"]),
            ("AI / ML", ["scikit-learn", "YOLOv8", "OpenCV", "NumPy", "Pandas", "LLM APIs", "RAG"]),
            ("Tools", ["Git", "GitHub", "Cursor", "Claude Code", "GitHub Copilot", "Power BI"]),
            ("Core CS", ["Data Structures and Algorithms", "OOP", "DBMS", "Operating Systems"]),
        ],
        out / "skills.svg",
    )

    achievements(
        [
            ("1st", "1st Place, Convergence 2K26 Software Hackathon", "Intelligent Shipment Piggybacking", "NetworkX"),
            ("1st", "1st Place, Convergence 2K26 Project Contest", "Traffic Optimization", "India Education Diary"),
            ("1st", "1st Place, Webathon 4.0", "Civix", "1,000+ participants"),
            ("2nd", "Runner-Up, VJ Hackathon", "Hackathon", "10,000+ participants"),
            ("2nd", "First Runner-Up, VNR Designathon 2026", "Open Innovation Track", "Top 30 of 2,800+"),
            ("FIN", "Finalist, Solution Sprint Ideathon", "Ideathon", ""),
            ("2★", "CodeChef 2-Star", "Competitive programming", "Rating 1420"),
        ],
        out / "achievements.svg",
    )

    twin_lists(
        ("Certifications", [
            "Microsoft Certified: Power BI Data Analyst Associate",
            "ServiceNow Virtual Internship, SmartBridge",
            "Generative AI, Udemy",
        ]),
        ("Leadership", [
            "Chairperson, Gamma Club (Research Club of VNR VJIET): heads student research initiatives",
            "Action Committee Member, Turing Hut Coding Club: selected from 900+ students",
            "Member, Computer Society of India (CSI)",
        ]),
        out / "certs-leadership.svg",
    )

    link_pill("github", f"/{U}", out / "link-github.svg")
    link_pill("linkedin", "/in/anudeep-reddy-veerati", out / "link-linkedin.svg")
    link_pill("portfolio", "anudeepreddyveerati.dev", out / "link-portfolio.svg")
    link_pill("email", "anudeepreddy016@gmail.com", out / "link-email.svg")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate rounded README SVG components.")
    parser.add_argument("--output", "-o", default="assets")
    args = parser.parse_args(argv)
    build(Path(args.output))
    print(f"Wrote components to {args.output}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
