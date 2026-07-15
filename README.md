# simple static blog generator in py3

## how to watch for changes

```python
python serve.py
```

## how to build

```python
python build.py
```

The sitemap is regenerated during every build. Blog `lastmod` values use the
latest of the publication date, the source file's last Git commit, and an
optional `updated: YYYY-MM-DD` front matter field. CI checks out the full Git
history so edits to existing posts receive an accurate modification date.


## TODO

- [ ] tags in posts + index for each tags
- [ ] write 1 article about journaling and gratitute diary, as I use them
