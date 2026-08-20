from __future__ import annotations

import os
import sys

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = PROJECT_ROOT / "src"

sys.path.insert(
    0,
    str(
        SRC_ROOT,
    ),
)


# -- Project information --------------------------------------------------

project = "TEKSI Hooks"
author = "TEKSI Association"
copyright = "2026, TEKSI Association"

version = os.environ.get(
    "DOCS_VERSION",
    "dev",
)

release = version


# -- General configuration ------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
]

templates_path = [
    "_templates",
]

exclude_patterns = [
    "_build",
    "Thumbs.db",
    ".DS_Store",
]

source_suffix = ".rst"
master_doc = "index"

pygments_style = "sphinx"

autodoc_typehints = "description"
autodoc_member_order = "bysource"


# -- HTML output -----------------------------------------------------------

html_theme = "sphinx_rtd_theme"

html_title = "TEKSI Hooks"
html_short_title = "TEKSI Hooks"

html_static_path = [
    "_static",
]

html_theme_options = {
    "collapse_navigation": False,
    "navigation_depth": 4,
    "sticky_navigation": True,
    "includehidden": True,
    "titles_only": False,
}

html_show_sourcelink = True
html_show_sphinx = True
html_show_copyright = True

htmlhelp_basename = "TEKSIHooksDoc"
