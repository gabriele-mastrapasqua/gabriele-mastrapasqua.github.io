import pathlib
import re
import subprocess
from typing import Sequence
import shutil
import hashlib
import datetime

import markdown
import markdown.extensions.fenced_code
import markdown_link_attr_modifier
import pymdownx.magiclink
import frontmatter
import jinja2

import highlighting
import witchhazel

jinja_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader("templates"),
)

markdown_ = markdown.Markdown(
    extensions=[
        "toc",
        "admonition",
        "tables",
        "abbr",
        "attr_list",
        "footnotes",
        "pymdownx.smartsymbols",
        "pymdownx.tilde",
        "pymdownx.caret",
        markdown.extensions.fenced_code.FencedCodeExtension(lang_prefix="language-"),
        pymdownx.magiclink.MagiclinkExtension(
            hide_protocol=False,
        ),
        markdown_link_attr_modifier.LinkAttrModifierExtension(
            new_tab="external_only", custom_attrs=dict(referrerpolicy="origin")
        ),
    ]
)


def copy_static():
    print("copy static...")
    pathlib.Path("./docs").mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        pathlib.Path("./static"), pathlib.Path("./docs/static"), dirs_exist_ok=True
    )


def get_static_version() -> str:
    stylesheet = pathlib.Path("./static/style.css").read_bytes()
    return hashlib.sha256(stylesheet).hexdigest()[:12]


def get_sources():
    yield from pathlib.Path(".").glob("srcs/*.md")
    yield from pathlib.Path(".").glob("srcs/*/index.md")


def parse_source(source: pathlib.Path) -> frontmatter.Post:
    post = frontmatter.load(str(source))
    return post


def git_last_modified(path: pathlib.Path) -> datetime.date | None:
    """Return the last committed change date without using build time."""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%cs", "--", str(path)],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None

    value = result.stdout.strip()
    return datetime.date.fromisoformat(value) if value else None


def as_date(value) -> datetime.date | None:
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    if isinstance(value, str):
        return datetime.date.fromisoformat(value)
    return None


def post_last_modified(post: frontmatter.Post) -> datetime.date:
    """Use explicit metadata or Git history, never the CI build timestamp."""
    candidates = [as_date(post.get("date")), as_date(post.get("updated"))]
    candidates.append(git_last_modified(post["source"]))
    return max(candidate for candidate in candidates if candidate is not None)


def post_social_image(post: frontmatter.Post) -> tuple[str, str]:
    """Use explicit metadata, then the first Markdown image, then a safe fallback."""
    image = post.get("social_image")
    alt = post.get("social_image_alt") or post.get("preview_image_alt")

    if not image and post.get("preview_image"):
        image = post["preview_image"]
        if not image.startswith(("/", "http://", "https://")):
            image = f"/{post['stem']}/{image}"

    if not image:
        match = re.search(r"!\[(?P<alt>[^\]]*)\]\((?P<url>[^\s)]+)", post.content)
        if match:
            image = match.group("url")
            alt = alt or match.group("alt")

    if not image:
        image = "/static/me.png"
        alt = alt or "Gabriele Mastrapasqua"

    if not image.startswith(("http://", "https://")):
        image = f"https://gabrielemastrapasqua.com/{image.lstrip('/')}"

    return image, alt or f"Cover image for {post['title']}"


def fixup_styles(content: str) -> str:
    content = content.replace("<table>", '<table class="table">')
    return content


def render_markdown(content: str) -> str:
    markdown_.reset()
    content = markdown_.convert(content)
    content = highlighting.highlight(content)
    content = fixup_styles(content)
    return content


def write_post(post: frontmatter.Post, content: str):
    dst = pathlib.Path(f"./docs/blog/{post['stem']}")
    dst.mkdir(parents=True, exist_ok=True)

    index = dst / "index.html"

    template = jinja_env.get_template("blog/post.html")
    rendered = template.render(post=post, content=content)

    index.write_text(rendered)


def copy_post_resources(post: frontmatter.Post):
    src = post["source"].parent
    dst = pathlib.Path(f"./docs/{post['stem']}")
    dst.mkdir(parents=True, exist_ok=True)

    shutil.copytree(src, dst, dirs_exist_ok=True)


def write_posts() -> Sequence[frontmatter.Post]:
    posts = []
    sources = get_sources()

    for source in sources:
        post = parse_source(source)
        content = render_markdown(post.content)

        post["source"] = source
        if source.match("*/index.md"):
            post["stem"] = source.parent.name
            copy_post_resources(post)
        else:
            post["stem"] = source.stem

        post["lastmod"] = post_last_modified(post)
        post["social_image"], post["social_image_alt"] = post_social_image(post)

        write_post(post, content)

        posts.append(post)

    return posts


def write_pygments_style_sheet():
    css = highlighting.get_style_css(witchhazel.WitchHazelStyle)
    pathlib.Path("./docs/static/pygments.css").write_text(css)


def write_home():
    path = pathlib.Path("./docs/index.html")
    template = jinja_env.get_template("index.html")
    rendered = template.render()
    path.write_text(rendered)

def write_about():
    path = pathlib.Path("./docs/about.html")
    template = jinja_env.get_template("about.html")
    rendered = template.render()
    path.write_text(rendered)

def write_projects():
    dst = pathlib.Path("./docs/projects")
    dst.mkdir(parents=True, exist_ok=True)
    template = jinja_env.get_template("projects.html")
    rendered = template.render()
    (dst / "index.html").write_text(rendered)

def write_book():
    dst = pathlib.Path("./docs/book")
    dst.mkdir(parents=True, exist_ok=True)
    template = jinja_env.get_template("book.html")
    rendered = template.render()
    (dst / "index.html").write_text(rendered)

def write_consultancy():
    dst = pathlib.Path("./docs/consultancy")
    dst.mkdir(parents=True, exist_ok=True)
    template = jinja_env.get_template("consultancy.html")
    rendered = template.render()
    (dst / "index.html").write_text(rendered)

def write_about_page():
    dst = pathlib.Path("./docs/about")
    dst.mkdir(parents=True, exist_ok=True)
    template = jinja_env.get_template("about.html")
    rendered = template.render()
    (dst / "index.html").write_text(rendered)

def write_blog_index(posts: Sequence[frontmatter.Post]):
    print("write blog index...")
    '''
    posts = sorted(posts, key=lambda post: post["date"], reverse=True)
    path = pathlib.Path("./docs/blog/index.html")
    template = jinja_env.get_template("blog/index.html")
    rendered = template.render(posts=posts)
    path.write_text(rendered)
    '''
    dst = pathlib.Path(f"./docs/blog/")
    dst.mkdir(parents=True, exist_ok=True)
    index = dst / "index.html"

    posts = sorted(posts, key=lambda post: post["date"], reverse=True)
    template = jinja_env.get_template("blog/index.html")
    rendered = template.render(posts=posts)
    index.write_text(rendered)



def write_rss(posts: Sequence[frontmatter.Post]):
    posts = sorted(posts, key=lambda post: post["date"], reverse=True)
    path = pathlib.Path("./docs/feed.xml")
    template = jinja_env.get_template("rss.xml")
    build_date = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%a, %d %b %Y %H:%M:%S +0000"
    )
    rendered = template.render(
        posts=posts,
        root="https://gabrielemastrapasqua.com",
        build_date=build_date,
    )
    path.write_text(rendered)


def write_sitemap(posts: Sequence[frontmatter.Post]):
    path = pathlib.Path("./docs/sitemap.xml")
    template = jinja_env.get_template("sitemap.xml")
    visible_posts = [post for post in posts if not post.get("hidden")]
    blog_lastmod = max(
        (post["lastmod"] for post in visible_posts),
        default=git_last_modified(pathlib.Path("templates/blog/index.html")),
    )
    pages = [
        ("/", git_last_modified(pathlib.Path("templates/index.html"))),
        ("/blog/", blog_lastmod),
        ("/about/", git_last_modified(pathlib.Path("templates/about.html"))),
        ("/projects/", git_last_modified(pathlib.Path("templates/projects.html"))),
        (
            "/consultancy/",
            git_last_modified(pathlib.Path("templates/consultancy.html")),
        ),
        ("/book/", git_last_modified(pathlib.Path("templates/book.html"))),
    ]
    rendered = template.render(
        posts=posts,
        pages=pages,
        root="https://gabrielemastrapasqua.com",
    )
    path.write_text(rendered)


def write_robots():
    path = pathlib.Path("./docs/robots.txt")
    template = jinja_env.get_template("robots.txt")
    path.write_text(template.render(root="https://gabrielemastrapasqua.com"))


def write_cname():
    pathlib.Path("./docs/CNAME").write_text("gabrielemastrapasqua.com")


def main():
    jinja_env.globals["static_version"] = get_static_version()
    copy_static()
    write_pygments_style_sheet()
    write_home()
    write_projects()
    write_book()
    write_consultancy()
    write_about_page()
    #write_about()
    posts = write_posts()
    write_blog_index(posts)
    write_rss(posts)
    write_sitemap(posts)
    write_robots()
    write_cname()


if __name__ == "__main__":
    main()
