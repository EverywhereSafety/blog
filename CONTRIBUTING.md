# Writing and publishing

Start with the reader's question and a concrete example. Explain motivation,
mechanism and evidence. Attribute source projects and cite primary references.
Distinguish proposed experiments from measured results.

Store each article and its assets under `posts/<slug>/`; add it to the root index.
Keep credentials, private data and weights outside the repo. Review prose,
image attribution and relative links before publication.

Build the readable HTML pages from Markdown:

```bash
pip install -r requirements.txt
python build.py
# Also copy articles and assets into a checkout of the public website:
python build.py --output ../EverywhereSafety.github.io/blog
```

`posts/<slug>/README.md` is the prose source; `index.html` is generated.
The public URL is `https://everywheresafety.github.io/blog/<slug>/`.
Keep project, code and organization backlinks in each article.
