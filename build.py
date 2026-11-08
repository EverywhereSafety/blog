"""Build readable article pages from Markdown; optionally copy them to the website."""

import argparse
import html
import json
from pathlib import Path
import re
import shutil

import markdown
from native_figures import native_content

ROOT = Path(__file__).resolve().parent
SITE = "https://everywheresafety.github.io"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Website blog directory")
    args = parser.parse_args()
    template = (ROOT / "template.html").read_text()
    for source in sorted((ROOT / "posts").glob("*/README.md")):
        text = source.read_text()
        title = text.splitlines()[0].removeprefix("# ")
        description = next(
            line
            for line in text.splitlines()[1:]
            if line.strip() and not line.lstrip().startswith(("<", "#", "!["))
        )
        url = f"{SITE}/blog/{source.parent.name}/"
        cover = re.search(r"!\[[^\]]*\]\(([^)]+)\)", text)
        image = (
            url + cover[1]
            if cover
            else f"{SITE}/assets/everywhere-safety-mark-white.png"
        )
        organization = {
            "@type": "Organization",
            "name": "Everywhere Safety",
            "url": SITE + "/",
        }
        structured = {
            "@context": "https://schema.org",
            "@type": "BlogPosting",
            "headline": title,
            "description": description,
            "url": url,
            "mainEntityOfPage": {"@type": "WebPage", "@id": url},
            "image": [image],
            "author": organization,
            "publisher": organization,
            "inLanguage": "en",
        }
        content = markdown.markdown(text, extensions=["extra", "toc"])
        toc_entries = []
        section_number = 0
        subsection_number = 0
        for heading in re.finditer(r'<h([23]) id="([^"]+)">(.*?)</h\1>', content):
            level, section_id, label = heading.groups()
            if level == "2":
                section_number += 1
                subsection_number = 0
                number = str(section_number)
            else:
                subsection_number += 1
                number = f"{section_number}.{subsection_number}"
            label = html.escape(html.unescape(re.sub(r"<[^>]+>", "", label)))
            toc_entries.append(
                f'<li class="toc-level-{level}"><a href="#{html.escape(section_id, quote=True)}">'
                f'<span class="toc-number" aria-hidden="true">{number}</span><span>{label}</span></a></li>'
            )
        toc = '<ol class="toc-list">' + "".join(toc_entries) + "</ol>"
        # Number only the article's actual headings; chart panel labels are separate.
        heading_number = [0, 0]
        def number_heading(match):
            level, section_id, label = match.groups()
            if level == "2":
                heading_number[0] += 1
                heading_number[1] = 0
                number = str(heading_number[0])
            else:
                heading_number[1] += 1
                number = f"{heading_number[0]}.{heading_number[1]}"
            return f'<h{level} id="{section_id}"><span class="section-number" aria-hidden="true">{number}</span>{label}</h{level}>'
        content = re.sub(r'<h([23]) id="([^"]+)">(.*?)</h\1>', number_heading, content)
        # The title and subtitle belong to the article header, outside the prose.
        content = re.sub(r"^<h1\b[^>]*>.*?</h1>\s*", "", content, count=1)
        subtitle_match = re.match(r'<p class="article-subtitle">.*?</p>', content)
        subtitle = subtitle_match[0] if subtitle_match else ""
        if subtitle_match:
            content = content[subtitle_match.end():].lstrip()
        reading_minutes = max(1, (len(re.sub(r"<[^>]+>", " ", content).split()) + 219) // 220)

        figure_number = 0
        def render_figure(match):
            nonlocal figure_number
            figure_number += 1
            image_html = match[1]
            alt = re.search(r'alt="([^"]*)"', image_html)
            image_src = re.search(r'src="([^"]*)"', image_html)
            native = native_content(image_src[1], source.parent / "assets") if image_src else None
            captions = {
                "puzzle-rhythm.png": "96 cases, 12 per board-size/difficulty group. Dots and curves show medians; whiskers and shaded bands show the middle 50%. Placement-chain points show medians only. Progress is normalized within each solver trace.",
                "contest-rhythm.png": "Aggregate candidate counts and exact placements from the recorded deduction trace. Both axes are linear; this is a solver procedure, not elapsed time. Hover or focus to inspect events. <a href='assets/contest-rhythm.json'>Aggregate trace data</a>.",
            }
            label = captions.get(Path(image_src[1]).name, alt[1] if alt else "")
            caption = f'<figcaption><span class="caption-label">Figure {figure_number}.</span> {label}</figcaption>'
            native_class = " native-figure" if native else ""
            return f'<figure id="figure-{figure_number}" class="article-figure{native_class}">{native or image_html}{caption}</figure>'

        content = re.sub(
            r'<p>((?:<a\b[^>]*>)?<img\b[^>]+/>(?:</a>)?)</p>',
            render_figure, content,
        )
        table_number = 0
        def render_table(match):
            nonlocal table_number
            table_number += 1
            caption = f'<caption><span class="caption-label">Table {table_number}.</span> Canonical solver medians for 96 generated cases, with 12 cases per board-size/difficulty group.</caption>'
            table = match[1].replace("<table>", "<table>" + caption, 1)
            return f'<div class="article-table" tabindex="0" role="region" aria-label="Table {table_number}">{table}</div>'
        content = re.sub(r"(<table>.*?</table>)", render_table, content, flags=re.S)
        rendered = (
            template.replace("{{TITLE}}", html.escape(title))
            .replace("{{DESCRIPTION}}", html.escape(description, quote=True))
            .replace("{{URL}}", html.escape(url, quote=True))
            .replace("{{IMAGE}}", html.escape(image, quote=True))
            .replace("{{SUBTITLE}}", subtitle)
            .replace("{{READING_MINUTES}}", str(reading_minutes))
            .replace("{{CONTENTS}}", toc)
            .replace(
                "{{STRUCTURED_DATA}}", json.dumps(structured).replace("<", "\\u003c")
            )
            .replace("{{CONTENT}}", content)
        )
        (source.parent / "index.html").write_text(rendered)
        if args.output:
            target = args.output / source.parent.name
            target.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source.parent / "index.html", target / "index.html")
            source_assets = source.parent / "assets"
            target_assets = target / "assets"
            # Remove stale generated assets when an article illustration is replaced.
            if target_assets.exists():
                for old in target_assets.iterdir():
                    if old.is_file() and not (source_assets / old.name).exists():
                        old.unlink()
            shutil.copytree(source_assets, target_assets, dirs_exist_ok=True)
        print(source.parent.name)


if __name__ == "__main__":
    main()
