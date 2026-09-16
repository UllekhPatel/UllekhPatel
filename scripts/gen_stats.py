#!/usr/bin/env python3
"""Render the all-time stats cards (public + private) as animated SVGs.

Data comes from the GitHub GraphQL API via `gh`; see fetch_data() for the
queries. Re-run with `python3 scripts/gen_stats.py` after `gh auth login`
to refresh the numbers, then commit the regenerated SVGs.
"""

import json
import subprocess
from pathlib import Path

USER = "UllekhPatel"
OUT = Path(__file__).resolve().parent.parent / "assets"
SNAPSHOT = OUT / "snapshot.json"

BG = "#0d1117"
BORDER = "#30363d"
ACCENT = "#a371f7"
TEXT = "#c9d1d9"
MUTED = "#8b949e"
CARD_H = 250  # both cards share a height so they align side by side

LANG_COLORS = {
    "TypeScript": "#3178c6", "Python": "#3572A5", "JavaScript": "#f1e05a",
    "Jupyter Notebook": "#DA5B0B", "Go": "#00ADD8", "HTML": "#e34c26",
    "C": "#555555", "Shell": "#89e051",
}


def gh_graphql(query):
    out = subprocess.run(
        ["gh", "api", "graphql", "-f", f"query={query}"],
        capture_output=True, text=True, check=True,
    ).stdout
    return json.loads(out)["data"]


def load_snapshot():
    """Values a repo-scoped Action token cannot see, captured from a run
    authenticated as the user. Refresh with `python3 scripts/gen_stats.py`
    locally after `gh auth login`."""
    if SNAPSHOT.exists():
        return json.loads(SNAPSHOT.read_text())
    return {}


def fetch_data():
    """Commit counts (public + private) are readable by any token because the
    account has 'include private contributions on my profile' enabled. Repo
    count and language bytes are NOT: a repo-scoped token sees public repos
    only, so those fall back to the committed snapshot."""
    snap = load_snapshot()
    commits_public = commits_private = prs_year = 0
    for y in range(2022, 2027):
        q = (
            '{ user(login:"%s"){ contributionsCollection('
            'from:"%d-01-01T00:00:00Z", to:"%d-12-31T23:59:59Z"){ '
            "totalCommitContributions restrictedContributionsCount "
            "totalPullRequestContributions } } }"
        ) % (USER, y, y)
        c = gh_graphql(q)["user"]["contributionsCollection"]
        commits_public += c["totalCommitContributions"]
        commits_private += c["restrictedContributionsCount"]
        prs_year += c["totalPullRequestContributions"]

    u = gh_graphql(
        '{ user(login:"%s"){ followers{totalCount} '
        "repositories(ownerAffiliations:[OWNER]){totalCount} "
        "pullRequests{totalCount} } }" % USER
    )["user"]

    langs_raw = gh_graphql(
        '{ user(login:"%s"){ repositories(first:100, '
        "ownerAffiliations:[OWNER]){ nodes{ languages(first:10){ "
        "edges{ size node{name} } } } } } }" % USER
    )["user"]["repositories"]["nodes"]

    totals = {}
    for repo in langs_raw:
        for e in repo["languages"]["edges"]:
            totals[e["node"]["name"]] = totals.get(e["node"]["name"], 0) + e["size"]
    langs = sorted(totals.items(), key=lambda kv: -kv[1])[:6]

    # Keep whichever view is richer: an owner-authenticated run sees private
    # repos and beats the snapshot; a tokenless Action run does not.
    repos = max(u["repositories"]["totalCount"], snap.get("repos", 0))
    prs = max(u["pullRequests"]["totalCount"], snap.get("prs", 0))
    snap_langs = [tuple(x) for x in snap.get("langs", [])]
    if sum(s for _, s in snap_langs) > sum(s for _, s in langs):
        langs = snap_langs

    return {
        "commits_total": commits_public + commits_private,
        "commits_private": commits_private,
        "commits_public": commits_public,
        "prs": prs,
        "repos": repos,
        "followers": u["followers"]["totalCount"],
        "langs": langs,
    }


def stats_card(d):
    rows = [
        ("Total Commits", f"{d['commits_total']:,}", True),
        ("Private Commits", f"{d['commits_private']:,}", False),
        ("Public Commits", f"{d['commits_public']:,}", False),
        ("Pull Requests", f"{d['prs']:,}", False),
    ]
    h = CARD_H
    parts = []
    for i, (label, value, hero) in enumerate(rows):
        y = 78 + i * 34
        size = 19 if hero else 15
        color = ACCENT if hero else TEXT
        weight = 700 if hero else 500
        parts.append(
            f'<g class="row" style="animation-delay:{0.12 * i + 0.2:.2f}s">'
            f'<text x="26" y="{y}" class="lbl">{label}</text>'
            f'<text x="434" y="{y}" text-anchor="end" '
            f'style="font-size:{size}px;font-weight:{weight};fill:{color}">{value}</text>'
            f'<rect x="26" y="{y + 8}" width="408" height="1" fill="{BORDER}" opacity="0.5"/>'
            "</g>"
        )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="460" height="{h}" viewBox="0 0 460 {h}" role="img" aria-label="All-time GitHub stats including private repositories">
<style>
  text {{ font-family: 'Segoe UI', Ubuntu, Helvetica, sans-serif; }}
  .title {{ font-size: 17px; font-weight: 700; fill: {ACCENT}; }}
  .sub {{ font-size: 11px; fill: {MUTED}; }}
  .lbl {{ font-size: 14px; fill: {TEXT}; }}
  .row {{ opacity: 0; animation: rise 0.6s ease-out forwards; }}
  @keyframes rise {{ from {{ opacity: 0; transform: translateY(8px); }}
                     to {{ opacity: 1; transform: translateY(0); }} }}
</style>
<rect x="0.5" y="0.5" width="459" height="{h - 1}" rx="12" fill="{BG}" stroke="{BORDER}"/>
<text x="26" y="34" class="title">All-Time Stats</text>
<text x="26" y="50" class="sub">public + private repositories</text>
{"".join(parts)}
</svg>"""


def langs_card(d):
    total = sum(s for _, s in d["langs"])
    h = CARD_H
    bars, x = [], 26.0
    seg = []
    for name, size in d["langs"]:
        w = (size / total) * 408
        seg.append(f'<rect x="{x:.1f}" y="62" width="{w:.1f}" height="10" '
                   f'fill="{LANG_COLORS.get(name, ACCENT)}"/>')
        x += w
    for i, (name, size) in enumerate(d["langs"]):
        y = 104 + i * 30
        pct = size / total * 100
        c = LANG_COLORS.get(name, ACCENT)
        bars.append(
            f'<g class="row" style="animation-delay:{0.1 * i + 0.3:.2f}s">'
            f'<circle cx="32" cy="{y - 4}" r="5" fill="{c}"/>'
            f'<text x="48" y="{y}" class="lbl">{name}</text>'
            f'<text x="434" y="{y}" text-anchor="end" class="pct">{pct:.1f}%</text>'
            "</g>"
        )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="460" height="{h}" viewBox="0 0 460 {h}" role="img" aria-label="Top languages across all repositories including private">
<style>
  text {{ font-family: 'Segoe UI', Ubuntu, Helvetica, sans-serif; }}
  .title {{ font-size: 17px; font-weight: 700; fill: {ACCENT}; }}
  .sub {{ font-size: 11px; fill: {MUTED}; }}
  .lbl {{ font-size: 14px; fill: {TEXT}; }}
  .pct {{ font-size: 13px; fill: {MUTED}; font-weight: 600; }}
  .row {{ opacity: 0; animation: rise 0.6s ease-out forwards; }}
  #bar {{ animation: grow 1.1s cubic-bezier(.4,0,.2,1) forwards; transform-origin: 26px 0; }}
  @keyframes rise {{ from {{ opacity: 0; transform: translateY(8px); }}
                     to {{ opacity: 1; transform: translateY(0); }} }}
  @keyframes grow {{ from {{ transform: scaleX(0); }} to {{ transform: scaleX(1); }} }}
</style>
<rect x="0.5" y="0.5" width="459" height="{h - 1}" rx="12" fill="{BG}" stroke="{BORDER}"/>
<text x="26" y="34" class="title">Top Languages</text>
<text x="26" y="50" class="sub">across all repositories, by bytes of code</text>
<clipPath id="r"><rect x="26" y="62" width="408" height="10" rx="5"/></clipPath>
<g clip-path="url(#r)" id="bar">{"".join(seg)}</g>
{"".join(bars)}
</svg>"""


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    d = fetch_data()
    # Persist the owner-only view so tokenless Action runs can reuse it.
    SNAPSHOT.write_text(json.dumps(
        {"repos": d["repos"], "prs": d["prs"],
         "langs": [list(x) for x in d["langs"]]}, indent=2) + "\n")
    (OUT / "stats.svg").write_text(stats_card(d))
    (OUT / "languages.svg").write_text(langs_card(d))
    print(f"commits={d['commits_total']:,} (private={d['commits_private']:,}) "
          f"prs={d['prs']} repos={d['repos']}")


if __name__ == "__main__":
    main()
