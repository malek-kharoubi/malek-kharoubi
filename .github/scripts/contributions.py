"""Render the GitHub contribution calendar as a dark, full-size SVG.

Reads the calendar through the GraphQL API, so organization contributions and
(if enabled in the profile settings) private contributions are included.

Usage: GH_TOKEN=... python contributions.py <login> <output.svg>
"""
import json
import os
import sys
import urllib.request
from datetime import date

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount contributionLevel } }
      }
    }
  }
}
"""

LEVELS = {
    "NONE": "#161b22",
    "FIRST_QUARTILE": "#0e4429",
    "SECOND_QUARTILE": "#006d32",
    "THIRD_QUARTILE": "#26a641",
    "FOURTH_QUARTILE": "#39d353",
}
BG, BORDER, TEXT, MUTED = "#0d1117", "#30363d", "#c9d1d9", "#8b949e"
FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"
CELL, GAP = 11, 3
LEFT, TOP, RIGHT, BOTTOM = 44, 58, 24, 46
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()


def fetch(login, token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.load(resp)
    if body.get("errors") or not body.get("data", {}).get("user"):
        raise SystemExit(f"GraphQL error: {body.get('errors')}")
    return body["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def render(calendar):
    weeks = calendar["weeks"]
    step = CELL + GAP
    width = LEFT + len(weeks) * step - GAP + RIGHT
    height = TOP + 7 * step - GAP + BOTTOM
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" font-family="{FONT}">',
        f'<rect x=".5" y=".5" width="{width - 1}" height="{height - 1}" rx="12" fill="{BG}" stroke="{BORDER}"/>',
        f'<text x="{LEFT}" y="32" font-size="15" font-weight="600" fill="{TEXT}">'
        f'{calendar["totalContributions"]:,} contributions in the last year</text>',
    ]
    last_month = None
    for x, week in enumerate(weeks):
        for day in week["contributionDays"]:
            d = date.fromisoformat(day["date"])
            y = TOP + d.isoweekday() % 7 * step  # Sunday is the first row
            n = day["contributionCount"]
            title = f'{n} contribution{"s" if n != 1 else ""} on {d.isoformat()}'
            out.append(
                f'<rect x="{LEFT + x * step}" y="{y}" width="{CELL}" height="{CELL}" rx="2" '
                f'fill="{LEVELS.get(day["contributionLevel"], LEVELS["NONE"])}"><title>{title}</title></rect>'
            )
        first = date.fromisoformat(week["contributionDays"][0]["date"])
        if first.month != last_month and (x == 0 or first.day <= 7) and x < len(weeks) - 2:
            out.append(f'<text x="{LEFT + x * step}" y="{TOP - 10}" font-size="11" fill="{MUTED}">{MONTHS[first.month - 1]}</text>')
        last_month = first.month
    for label, row in (("Mon", 1), ("Wed", 3), ("Fri", 5)):
        out.append(f'<text x="{LEFT - 8}" y="{TOP + row * step + CELL - 1}" font-size="10" fill="{MUTED}" text-anchor="end">{label}</text>')
    legend_y = TOP + 7 * step + 14
    legend_x = width - RIGHT - 5 * step - 62
    out.append(f'<text x="{legend_x - 8}" y="{legend_y + 9}" font-size="11" fill="{MUTED}" text-anchor="end">Less</text>')
    for i, color in enumerate(LEVELS.values()):
        out.append(f'<rect x="{legend_x + i * step}" y="{legend_y}" width="{CELL}" height="{CELL}" rx="2" fill="{color}"/>')
    out.append(f'<text x="{legend_x + 5 * step + 4}" y="{legend_y + 9}" font-size="11" fill="{MUTED}">More</text>')
    out.append("</svg>")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    login, path = sys.argv[1], sys.argv[2]
    token = os.environ.get("GH_TOKEN")
    if not token:
        raise SystemExit("GH_TOKEN is not set")
    with open(path, "w", encoding="utf-8") as f:
        f.write(render(fetch(login, token)))
    print(f"wrote {path}")
