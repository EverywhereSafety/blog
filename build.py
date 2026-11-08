"""Build readable article pages from Markdown; optionally copy them to the website."""

import argparse
import html
import json
from pathlib import Path
import re
import shutil

import markdown

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
        # The title and subtitle belong to the article header, outside the prose.
        content = re.sub(r"^<h1\b[^>]*>.*?</h1>\s*", "", content, count=1)
        subtitle_match = re.match(r'<p class="article-subtitle">.*?</p>', content)
        subtitle = subtitle_match[0] if subtitle_match else ""
        if subtitle_match:
            content = content[subtitle_match.end():].lstrip()
        reading_minutes = max(1, (len(re.sub(r"<[^>]+>", " ", content).split()) + 219) // 220)

        def render_figure(match):
            image_html = match[1]
            alt = re.search(r'alt="([^"]*)"', image_html)
            caption = f"<figcaption>{alt[1]}</figcaption>" if alt and alt[1] else ""
            return f'<figure class="article-figure">{image_html}{caption}</figure>'

        content = re.sub(
            r'<p>((?:<a\b[^>]*>)?<img\b[^>]+/>(?:</a>)?)</p>',
            render_figure, content,
        )
        content = re.sub(
            r"(<table>.*?</table>)",
            r'<div class="article-table" tabindex="0" role="region" aria-label="Data table">\1</div>',
            content, flags=re.S,
        )
        rendered = (
            template.replace("{{TITLE}}", html.escape(title))
            .replace("{{DESCRIPTION}}", html.escape(description, quote=True))
            .replace("{{URL}}", html.escape(url, quote=True))
            .replace("{{IMAGE}}", html.escape(image, quote=True))
            .replace("{{SUBTITLE}}", subtitle)
            .replace("{{READING_MINUTES}}", str(reading_minutes))
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
