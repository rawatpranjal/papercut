# Configuration file for Sphinx documentation builder.

project = "Papercutter"
copyright = "2025, Pranjal Rawat"
author = "Pranjal Rawat"
release = "3.1.0"

extensions = [
    "sphinx_design",
    "myst_parser",
    "sphinx_copybutton",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "pydata_sphinx_theme"
html_static_path = ["_static"]

html_theme_options = {
    "logo": {
        "image_light": "_static/logo.svg",
        "image_dark": "_static/logo.svg",
        "text": "Papercutter",
    },
    "github_url": "https://github.com/rawatpranjal/papercutter",
    "navbar_start": ["navbar-logo"],
    "navbar_center": ["navbar-nav"],
    "navbar_end": ["navbar-icon-links"],
    "header_links_before_dropdown": 4,
    "navigation_with_keys": True,
    "show_nav_level": 2,
    "navigation_depth": 2,
}

html_favicon = "_static/logo.svg"
