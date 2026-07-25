# GitHub Profile Art Generator

Automated, GitHub-renderable profile art built with pure SVG and Python.

- Animated ASCII portrait
- Neofetch-style info card
- GitHub contribution heatmap

Everything is generated locally as static SVG using SMIL animations—no JavaScript.

---

## Generated Art

### ASCII Portrait

![ASCII Portrait](./anudeep-ascii.svg)

### Info Card

![Info Card](./info-card.svg)

### Contribution Heatmap

![Contribution Heatmap](./contrib-heatmap.svg)

---

## How It Works

| Script | Purpose | Output |
| --- | --- | --- |
| [`scripts/prep_photo.py`](./scripts/prep_photo.py) | Removes the background, grayscales, runs CLAHE/denoise, and resizes the source photo. | `assets/source-prepped.png` |
| [`scripts/make_ascii_svg.py`](./scripts/make_ascii_svg.py) | Maps the prepped photo to a monospace density ramp and renders a typing-style ASCII SVG. | `anudeep-ascii.svg` |
| [`scripts/make_info_card.py`](./scripts/make_info_card.py) | Builds a neofetch-style terminal card with profile details and a row-by-row typing animation. | `info-card.svg` |
| [`scripts/fetch_contributions.py`](./scripts/fetch_contributions.py) | Scrapes the public GitHub contributions page (no token, no GraphQL) and computes stats/streaks. | `data/contributions.json` |
| [`scripts/render_heatmap_svg.py`](./scripts/render_heatmap_svg.py) | Renders a 53-week × 7-day animated contribution heatmap. | `contrib-heatmap.svg` |

---

## Local Setup

```bash
# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r scripts/requirements.txt

# Run the full pipeline
python3 scripts/prep_photo.py
python3 scripts/make_ascii_svg.py
python3 scripts/make_info_card.py
python3 scripts/fetch_contributions.py
python3 scripts/render_heatmap_svg.py
```

---

## Project Structure

```text
.
├── .github/workflows/update-profile-art.yml   # Placeholder automation workflow
├── assets/
│   ├── source-photo.jpg                       # Source portrait
│   └── source-prepped.png                     # Processed portrait
├── data/
│   └── contributions.json                     # Parsed contribution data
├── scripts/
│   ├── fetch_contributions.py
│   ├── make_ascii_svg.py
│   ├── make_info_card.py
│   ├── prep_photo.py
│   ├── render_heatmap_svg.py
│   └── requirements.txt
├── anudeep-ascii.svg
├── contrib-heatmap.svg
├── info-card.svg
├── LICENSE
└── README.md
```

---

## License

MIT. See [`LICENSE`](./LICENSE).
