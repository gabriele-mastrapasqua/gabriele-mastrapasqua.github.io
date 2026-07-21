# gabrielemastrapasqua.com

My personal website — a lightweight static site built with Python.

## Stack

- **Generator**: plain Python + `markdown` + `jinja2` + `python-frontmatter`
- **CSS**: Bootstrap 5 + custom styles + WitchHazel Pygments theme
- **Templates**: Jinja2, no JS framework
- **Hosting**: GitHub Pages

## Commands

```bash
# dev — watches srcs/ and rebuilds on change
python serve.py

# production build
python build.py
```

The output lands in `docs/` (GitHub Pages root). The sitemap regenerates every build. Blog `lastmod` values use the latest of publication date, source file's last Git commit, and an optional `updated: YYYY-MM-DD` front matter field.
