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
        description = next(line for line in text.splitlines()[1:] if line.strip())
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
        rendered = (
            template.replace("{{TITLE}}", html.escape(title))
            .replace("{{DESCRIPTION}}", html.escape(description, quote=True))
            .replace("{{URL}}", html.escape(url, quote=True))
            .replace("{{IMAGE}}", html.escape(image, quote=True))
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
