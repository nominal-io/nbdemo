"""The ``notebook-gallery`` directive: a card grid for the demos beside the page.

Adapted from nominal-client's ``example-gallery``. A card links to each:

- subfolder with an ``index.md``, titled from its first ``#`` heading, unless ``:exclude:`` names it, and
- notebook: a MyST Markdown file with ``kernelspec`` in its front matter.

A card shows a thumbnail over the page's first ``#`` heading as its title. The thumbnail is, in
order of preference:

1. the page's ``thumbnail`` front-matter key, a path relative to the page (read from the file);
2. the first image in a notebook cell tagged ``thumbnail``;
3. the page's last image, so a notebook's last plot.

A page without one gets an empty tile. Adapted from shibuya-page's ``gallery``.
The sidebar lists the pages through each index's toctree, not here.
"""

from pathlib import Path
from typing import Any, NamedTuple

import yaml
from docutils import nodes
from docutils.parsers.rst import directives
from sphinx.application import Sphinx
from sphinx.environment import BuildEnvironment
from sphinx.util import logging
from sphinx.util.docutils import SphinxDirective

logger = logging.getLogger(__name__)
STATIC_PATH = Path(__file__).parent / "static"
THUMBNAIL_TAG = "tag_thumbnail"


class notebook_gallery(nodes.General, nodes.Element):
    """Where the cards go; replaced once every page's thumbnail is known."""


class Card(NamedTuple):
    title: str
    thumbnail: str = ""


def _heading(markdown: str, fallback: str) -> str:
    """The first ``#`` heading."""
    for line in markdown.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def _myst_card(path: Path, *, notebook_only: bool) -> Card | None:
    text = path.read_text(encoding="utf-8")
    meta: dict[str, Any] = {}
    if text.startswith("---\n"):
        front, _, text = text[4:].partition("\n---\n")
        meta = yaml.safe_load(front) or {}
    if notebook_only and "kernelspec" not in meta:
        return None
    return Card(_heading(text, path.stem), str(meta.get("thumbnail", "")))


def _cards(folder: Path, exclude: set[str]) -> list[tuple[str, Path, Card]]:
    """(docname relative to the folder, source path, card) for each subfolder and notebook."""
    found = []
    for sub in sorted(p for p in folder.iterdir() if (p / "index.md").is_file() and p.name not in exclude):
        card = _myst_card(sub / "index.md", notebook_only=False)
        assert card is not None
        found.append((f"{sub.name}/index", sub / "index.md", card))
    for path in sorted(p for p in folder.glob("*.md") if p.stem != "index"):
        card = _myst_card(path, notebook_only=True)
        if card is not None:
            found.append((path.stem, path, card))
    return found


class NotebookGallery(SphinxDirective):
    def _front_matter_thumbnail(self, card: Card, ref: str) -> str:
        """The page's ``thumbnail`` front matter, as a path from the source directory, registered so
        the builder copies it. Read here, from the file, as the titles are: the page's metadata isn't
        reliably set on CI."""
        if not card.thumbnail:
            return ""
        relpath, abspath = self.env.relfn2path(card.thumbnail, ref)
        if not Path(abspath).is_file():
            logger.warning("thumbnail %r of %s not found", card.thumbnail, ref, location=self.env.docname)
            return ""
        self.env.images.add_file(self.env.docname, relpath)
        self.env.note_dependency(abspath)
        return relpath

    option_spec = {"exclude": directives.unchanged}

    def run(self) -> list[nodes.Node]:
        folder = Path(self.env.doc2path(self.env.docname)).parent
        prefix = self.env.docname.rpartition("/")[0]
        entries = []
        exclude = set(self.options.get("exclude", "").split())
        for link, path, card in _cards(folder, exclude):
            self.env.note_dependency(path)
            ref = f"{prefix}/{link}" if prefix else link
            entries.append((card.title, ref, self._front_matter_thumbnail(card, ref)))
        self.env.notebook_galleries[self.env.docname] = {ref for _, ref, _ in entries}
        return [notebook_gallery(entries=entries)]


def _image_key(env: BuildEnvironment, node: nodes.image) -> str | None:
    candidate = node.get("candidates", {}).get("*")
    return candidate if candidate in env.images else None


def _find_thumbnail(app: Sphinx, doctree: nodes.document) -> None:
    env = app.env
    docname = env.docname
    images = [key for node in doctree.findall(nodes.image) if (key := _image_key(env, node))]
    tagged = [
        key
        for cell in doctree.findall(nodes.container)
        if THUMBNAIL_TAG in cell.get("classes", ())
        for node in cell.findall(nodes.image)
        if (key := _image_key(env, node))
    ]
    if tagged or images:
        env.notebook_thumbs[docname] = (tagged or images[::-1])[0]


def _draw(app: Sphinx, doctree: nodes.document, docname: str) -> None:
    env = app.env
    for node in list(doctree.findall(notebook_gallery)):
        if app.builder.format != "html":
            node.parent.remove(node)
            continue
        grid = nodes.container(classes=["sp-gallery"])
        for title, ref, front_matter in node["entries"]:
            link = nodes.reference("", "", internal=True, refuri=app.builder.get_relative_uri(docname, ref))
            thumb = front_matter or env.notebook_thumbs.get(ref)
            if thumb:
                frame = nodes.inline("", "", classes=["sp-gallery-image"])
                frame += nodes.image(uri=thumb, candidates={"*": thumb}, alt="")
            else:
                frame = nodes.inline("", "", classes=["sp-gallery-image", "sp-gallery-empty"])
            link += frame
            link += nodes.inline(title, title, classes=["sp-gallery-title"])
            grid += nodes.paragraph("", "", link, classes=["sp-gallery-card"])
        node.replace_self(grid)


def _init_env(app: Sphinx) -> None:
    for attr in ("notebook_galleries", "notebook_thumbs"):
        if not hasattr(app.env, attr):
            setattr(app.env, attr, {})


def _purge(app: Sphinx, env: BuildEnvironment, docname: str) -> None:
    env.notebook_galleries.pop(docname, None)
    env.notebook_thumbs.pop(docname, None)


def _merge(app: Sphinx, env: BuildEnvironment, docnames: set[str], other: BuildEnvironment) -> None:
    for docname in docnames:
        if docname in other.notebook_galleries:
            env.notebook_galleries[docname] = other.notebook_galleries[docname]
        if docname in other.notebook_thumbs:
            env.notebook_thumbs[docname] = other.notebook_thumbs[docname]


def _outdated(app: Sphinx, env: BuildEnvironment, added: set[str], changed: set[str], removed: set[str]) -> list[str]:
    """Rebuild a gallery when a page it links to changes (its thumbnail may), or one is added or removed."""
    touched = added | changed | removed
    folders = {docname.rpartition("/")[0] for docname in added | removed}
    return [
        doc
        for doc, refs in env.notebook_galleries.items()
        if refs & touched or any(f == doc.rpartition("/")[0] for f in folders)
    ]


def _add_static(app: Sphinx, config: Any) -> None:
    config.html_static_path.append(str(STATIC_PATH))


def setup(app: Sphinx) -> dict[str, Any]:
    app.add_node(notebook_gallery)
    app.add_directive("notebook-gallery", NotebookGallery)
    app.connect("builder-inited", _init_env)
    app.connect("config-inited", _add_static)
    # after Sphinx's image collector (500) has registered the page's images
    app.connect("doctree-read", _find_thumbnail, priority=600)
    app.connect("doctree-resolved", _draw)
    app.connect("env-purge-doc", _purge)
    app.connect("env-merge-info", _merge)
    app.connect("env-get-outdated", _outdated)
    app.add_css_file("notebook-gallery.css")
    return {"parallel_read_safe": True, "parallel_write_safe": True, "env_version": 2}
