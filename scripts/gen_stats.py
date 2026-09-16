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
    """Total contributions already include private activity, because the
    account exposes private contributions on its profile - so a repo-scoped
    Action token reads the same number the owner does. Language bytes need
    private *repo* access, which no such token has, hence the snapshot."""
    snap = load_snapshot()

    total = 0
    for y in range(2022, 2027):
        q = (
            '{ user(login:"%s"){ contributionsCollection('
            'from:"%d-01-01T00:00:00Z", to:"%d-12-31T23:59:59Z"){ '
            "contributionCalendar{totalContributions} } } }"
        ) % (USER, y, y)
        c = gh_graphql(q)["user"]["contributionsCollection"]
        total += c["contributionCalendar"]["totalContributions"]

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

    snap_langs = [tuple(x) for x in snap.get("langs", [])]
    if sum(v for _, v in snap_langs) > sum(v for _, v in langs):
        langs = snap_langs

    return {"total": total, "langs": langs}


W = 880   # one compact band: contributions on the left, languages on the right
H = 96
PAD = 24
SPLIT = 250  # x where the language block starts


def text_w(s, size, weight=400):
    """Approximate rendered width in px for the Segoe UI stack. Deliberately
    generous so layout errs toward whitespace rather than overflow."""
    return len(str(s)) * size * (0.62 if weight >= 600 else 0.55)


def card(d):
    num = f"{d['total']:,}"
    num_size = 34
    while text_w(num, num_size, 700) > SPLIT - PAD - 16:
        num_size -= 2

    inner = W - SPLIT - PAD          # width available to the language block
    langs = list(d["langs"])
    fs, dot, gap = 11, 13, 14

    def legend_w(items):
        return sum(dot + text_w(n, fs) + text_w(" 00%", fs, 600) for n, _ in items) \
               + gap * max(len(items) - 1, 0)

    while len(langs) > 2 and legend_w(langs) > inner:
        langs.pop()

    tot = sum(v for _, v in langs)
    seg, x = [], float(SPLIT)
    for n, v in langs:
        w = (v / tot) * inner
        seg.append(f'<rect x="{x:.1f}" y="34" width="{w:.1f}" height="9" '
                   f'fill="{LANG_COLORS.get(n, ACCENT)}"/>')
        x += w

    items, lx = [], float(SPLIT)
    for i, (n, v) in enumerate(langs):
        c = LANG_COLORS.get(n, ACCENT)
        items.append(
            f'<g class="fx" style="animation-delay:{0.06 * i + 0.3:.2f}s">'
            f'<circle cx="{lx + 4:.1f}" cy="66" r="4" fill="{c}"/>'
            f'<text x="{lx + dot:.1f}" y="70" class="lg">{n}</text>'
            f'<text x="{lx + dot + text_w(n, fs) + 5:.1f}" y="70" class="pc">'
            f'{v / tot * 100:.0f}%</text></g>'
        )
        lx += dot + text_w(n, fs) + text_w(" 00%", fs, 600) + gap

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Total contributions {num}; top languages across all repositories">
<style>
  text {{ font-family: 'Segoe UI', Ubuntu, Helvetica, sans-serif; }}
  .num {{ font-size: {num_size}px; font-weight: 700; fill: {ACCENT}; }}
  .cap {{ font-size: 10px; font-weight: 600; fill: {TEXT}; letter-spacing: 1.2px; }}
  .sub {{ font-size: 9px; fill: {MUTED}; }}
  .lg  {{ font-size: {fs}px; fill: {TEXT}; }}
  .pc  {{ font-size: {fs}px; font-weight: 600; fill: {MUTED}; }}
  .ttl {{ font-size: 10px; font-weight: 600; fill: {MUTED}; letter-spacing: 1.2px; }}
  .fx  {{ opacity: 0; animation: rise .55s ease-out forwards; }}
  #bar {{ animation: grow 1s cubic-bezier(.4,0,.2,1) forwards; transform-origin: {SPLIT}px 0; }}
  @keyframes rise {{ from {{ opacity:0; transform: translateY(6px); }}
                     to {{ opacity:1; transform: translateY(0); }} }}
  @keyframes grow {{ from {{ transform: scaleX(0); }} to {{ transform: scaleX(1); }} }}
</style>
<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="10" fill="{BG}" stroke="{BORDER}"/>
<g class="fx">
  <text x="{PAD}" y="48" class="num">{num}</text>
  <text x="{PAD}" y="66" class="cap">TOTAL CONTRIBUTIONS</text>
  <text x="{PAD}" y="80" class="sub">public + private &#183; since 2022</text>
</g>
<line x1="{SPLIT - 22}" y1="20" x2="{SPLIT - 22}" y2="{H - 20}" stroke="{BORDER}"/>
<text x="{SPLIT}" y="24" class="ttl">LANGUAGES</text>
<clipPath id="r"><rect x="{SPLIT}" y="34" width="{inner}" height="9" rx="4.5"/></clipPath>
<g clip-path="url(#r)" id="bar">{"".join(seg)}</g>
{"".join(items)}
</svg>"""


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    d = fetch_data()
    # Persist the owner-only view so tokenless Action runs can reuse it.
    if len(d["langs"]) >= len(load_snapshot().get("langs", [])):
        SNAPSHOT.write_text(json.dumps(
            {"langs": [list(x) for x in d["langs"]]}, indent=2) + "\n")
    (OUT / "stats.svg").write_text(card(d))
    print(f"total_contributions={d['total']:,} langs={len(d['langs'])}")


if __name__ == "__main__":
    main()
