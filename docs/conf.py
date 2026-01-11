# Configuration file for Sphinx documentation builder.

project = "Papercutter"
copyright = "2025, Pranjal Rawat"
author = "Pranjal Rawat"
release = "3.0.0"

extensions = ["sphinx_design", "myst_parser"]

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
}

html_favicon = "_static/logo.svg"
