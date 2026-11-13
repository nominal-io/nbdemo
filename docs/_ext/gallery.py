"""The ``notebook-gallery`` directive: a card grid for the demos beside the page.

Adapted from nominal-client's ``example-gallery``. A card links to each:

- subfolder with an ``index.md``, titled from its first ``#`` heading, unless ``:exclude:`` names it, and
- notebook: a MyST Markdown file with ``kernelspec`` in its front matter.

A card shows the page's first ``#`` heading as its title. The optional front-matter ``icon`` key
names an octicon.
The sidebar lists the pages through each index's toctree, not here.
"""

from pathlib import Path
from typing import Any, NamedTuple

import yaml
from docutils import nodes
from docutils.parsers.rst import directives
from docutils.statemachine import StringList
from sphinx.application import Sphinx
from sphinx.environment import BuildEnvironment
from sphinx.util.docutils import SphinxDirective

GALLERY = """\
::::{{grid}} 1 1 2 2
:gutter: 4

{cards}
::::
"""

CARD = """\
:::{{grid-item-card}} {label}
:link: {link}
:link-type: doc
:::
"""


class Card(NamedTuple):
    title: str
    icon: str


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
    return Card(_heading(text, path.stem), meta.get("icon", ""))


def _cards(folder: Path, exclude: set[str]) -> list[tuple[str, Path, Card]]:
    """(docname relative to the folder, source path, card) for each subfolder and notebook."""
    found = []
    for sub in sorted(p for p in folder.iterdir() if (p / "index.md").is_file() and p.name not in exclude):
        card = _myst_card(sub / "index.md", notebook_only=False)
        assert card is not None
        found.append((f"{sub.name}/index", sub / "index.md", card))
    for path in sorted(folder.glob("*.md")):
        card = _myst_card(path, notebook_only=True)
        if card is not None:
            found.append((path.stem, path, card))
    return found


class NotebookGallery(SphinxDirective):
    option_spec = {"exclude": directives.unchanged}

    def run(self) -> list[nodes.Node]:
        folder = Path(self.env.doc2path(self.env.docname)).parent
        cards = []
        exclude = set(self.options.get("exclude", "").split())
        for link, path, card in _cards(folder, exclude):
            self.env.note_dependency(path)
            label = f"{{octicon}}`{card.icon}` {card.title}" if card.icon else card.title
            cards.append(CARD.format(label=label, link=link))
        self.env.notebook_galleries = getattr(self.env, "notebook_galleries", set()) | {self.env.docname}

        markup = GALLERY.format(cards="\n".join(cards))
        container = nodes.Element()
        source = self.get_source_info()[0]
        self.state.nested_parse(StringList(markup.splitlines(), source), self.content_offset, container)
        return container.children


def _purge(app: Sphinx, env: BuildEnvironment, docname: str) -> None:
    getattr(env, "notebook_galleries", set()).discard(docname)


def _merge(app: Sphinx, env: BuildEnvironment, docnames: set[str], other: BuildEnvironment) -> None:
    env.notebook_galleries = getattr(env, "notebook_galleries", set()) | getattr(other, "notebook_galleries", set())


def _outdated(app: Sphinx, env: BuildEnvironment, added: set[str], changed: set[str], removed: set[str]) -> list[str]:
    """Rebuild a gallery when a page is added to or removed from its folder or a subfolder."""
    folders = {docname.rpartition("/")[0] for docname in added | removed}
    return [
        doc
        for doc in getattr(env, "notebook_galleries", set())
        if any(folder == doc.rpartition("/")[0] or folder.startswith(doc.rpartition("/")[0]) for folder in folders)
    ]


def setup(app: Sphinx) -> dict[str, Any]:
    app.add_directive("notebook-gallery", NotebookGallery)
    app.connect("env-purge-doc", _purge)
    app.connect("env-merge-info", _merge)
    app.connect("env-get-outdated", _outdated)
    return {"parallel_read_safe": True, "parallel_write_safe": True}
