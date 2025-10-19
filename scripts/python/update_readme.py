"""Utility script to refresh the blog post list in the README."""

from __future__ import annotations

import argparse
import html
import json
import logging
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = REPO_ROOT / "config" / "blogs.json"
DEFAULT_README = REPO_ROOT / "README.md"
START_MARKER = "<!-- BLOG-POST-LIST:START -->"
END_MARKER = "<!-- BLOG-POST-LIST:END -->"


class FeedUpdateError(RuntimeError):
    """Raised when the feed cannot be retrieved or parsed."""


@dataclass
class BlogConfig:
    """Configuration data for a single blog feed."""

    name: str
    feed_url: str | None
    local_feed: Path | None
    max_posts: int

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "BlogConfig":
        name = str(payload.get("name", "")).strip()
        feed_url = payload.get("feed_url")
        local_feed = payload.get("local_feed")
        max_posts = int(payload.get("max_posts", 5))

        if not name:
            raise FeedUpdateError("Each blog entry must include a non-empty 'name'.")

        feed_url_str = str(feed_url).strip() if isinstance(feed_url, str) else None
        local_feed_path = (
            (REPO_ROOT / str(local_feed)) if isinstance(local_feed, str) else None
        )

        return cls(name=name, feed_url=feed_url_str, local_feed=local_feed_path, max_posts=max_posts)


def load_config(path: Path) -> List[BlogConfig]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    blogs_raw = data.get("blogs")
    if not isinstance(blogs_raw, list):
        raise FeedUpdateError("The configuration file must include a 'blogs' list.")

    blogs: List[BlogConfig] = []
    for entry in blogs_raw:
        if not isinstance(entry, dict):
            raise FeedUpdateError("Each blog entry must be a JSON object.")
        blogs.append(BlogConfig.from_dict(entry))
    return blogs


def fetch_feed(config: BlogConfig, *, offline: bool = False) -> bytes:
    if not offline and config.feed_url:
        request = urllib.request.Request(
            config.feed_url,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; READMEUpdater/1.0; +https://github.com/)"
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.read()
        except urllib.error.URLError as exc:  # pragma: no cover - network dependent
            logging.warning("Failed to download feed '%s': %s", config.feed_url, exc)

    if config.local_feed and config.local_feed.exists():
        return config.local_feed.read_bytes()

    if offline and config.feed_url:
        raise FeedUpdateError(
            f"Offline mode enabled but no local_feed found for '{config.name}'."
        )

    if config.feed_url:
        raise FeedUpdateError(
            f"Unable to retrieve feed from '{config.feed_url}' and no local fallback provided."
        )

    raise FeedUpdateError(
        f"No feed source defined for '{config.name}'. Please provide a feed_url or local_feed."
    )


def parse_feed(content: bytes) -> List[tuple[str, str]]:
    try:
        root = ET.fromstring(content)
    except ET.ParseError as exc:  # pragma: no cover - invalid input
        raise FeedUpdateError(f"Unable to parse feed content: {exc}") from exc

    tag_name = _strip_namespace(root.tag)
    if tag_name == "rss":
        return _parse_rss(root)
    if tag_name == "feed":
        return _parse_atom(root)
    raise FeedUpdateError(f"Unsupported feed type '{root.tag}'.")


def _strip_namespace(tag: str) -> str:
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def _parse_rss(root: ET.Element) -> List[tuple[str, str]]:
    channel = root.find("channel")
    if channel is None:
        raise FeedUpdateError("RSS feed did not include a channel element.")

    posts: List[tuple[str, str]] = []
    for item in channel.findall("item"):
        title = item.findtext("title", default="").strip()
        link = item.findtext("link", default="").strip()
        if title and link:
            posts.append((html.unescape(title), link))
    return posts


def _parse_atom(root: ET.Element) -> List[tuple[str, str]]:
    atom_ns = "{http://www.w3.org/2005/Atom}"
    posts: List[tuple[str, str]] = []
    for entry in root.findall(f"{atom_ns}entry"):
        title = entry.findtext(f"{atom_ns}title", default="").strip()
        link_element = entry.find(f"{atom_ns}link[@rel='alternate']")
        if link_element is None:
            link_element = entry.find(f"{atom_ns}link")
        link = (link_element.get("href") if link_element is not None else "").strip()
        if title and link:
            posts.append((html.unescape(title), link))
    return posts


def build_markdown(posts: Sequence[tuple[str, str]], *, max_posts: int) -> str:
    selected = posts[:max_posts]
    if not selected:
        return "- No posts available right now."
    return "\n".join(f"- [{title}]({link})" for title, link in selected)


def update_readme(readme_path: Path, lines: Iterable[str]) -> None:
    content = readme_path.read_text(encoding="utf-8")
    sections = list(lines)
    replacement_text = "\n".join(sections)

    marker_block = f"{START_MARKER}\n{replacement_text}\n{END_MARKER}"

    start_index = content.find(START_MARKER)
    end_index = content.find(END_MARKER)
    if start_index == -1 or end_index == -1 or end_index < start_index:
        raise FeedUpdateError(
            "Could not locate the BLOG-POST-LIST markers in the README file."
        )

    end_index += len(END_MARKER)
    updated = content[:start_index] + marker_block + content[end_index:]

    readme_path.write_text(updated, encoding="utf-8")


def process(config_path: Path, readme_path: Path, *, offline: bool, dry_run: bool) -> List[str]:
    blogs = load_config(config_path)
    markdown_sections: List[str] = []

    for blog in blogs:
        logging.info("Processing feed for '%s'", blog.name)
        feed_content = fetch_feed(blog, offline=offline)
        posts = parse_feed(feed_content)
        markdown_sections.append(build_markdown(posts, max_posts=blog.max_posts))

    if dry_run:
        return markdown_sections

    update_readme(readme_path, markdown_sections)
    return markdown_sections


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help="Path to the JSON configuration file (default: %(default)s)",
    )
    parser.add_argument(
        "--readme",
        type=Path,
        default=DEFAULT_README,
        help="Path to the README file to update (default: %(default)s)",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Skip network requests and rely solely on local feed files.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Process the feeds but do not write to the README.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging output.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    try:
        sections = process(
            args.config,
            args.readme,
            offline=args.offline,
            dry_run=args.dry_run,
        )
    except FeedUpdateError as exc:
        logging.error("%s", exc)
        return 1

    for idx, section in enumerate(sections, start=1):
        logging.info("Generated %d entries for feed %d", section.count("\n") + 1, idx)

    if args.dry_run:
        print("\n\n".join(sections))

    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    sys.exit(main())
