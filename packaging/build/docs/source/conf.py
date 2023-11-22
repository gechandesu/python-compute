# Add /mnt/build/compute-0.1.0.dev1 to path for autodoc Sphinx extension
import os
import sys
sys.path.insert(0, os.path.abspath('/mnt/build/compute-0.1.0.dev1'))

# Project information
project = 'Compute'
copyright = '2023, Compute Authors'
author = 'Compute Authors'
release = '0.1.0'

# Sphinx general settings
extensions = [
    'sphinx.ext.autodoc',
    'sphinx_multiversion',
]
templates_path = ['_templates']
exclude_patterns = []
language = 'en'

# HTML output settings
html_theme = 'alabaster'
html_static_path = ['_static']
html_sidebars = {
    '**': [
        'about.html',
        'navigation.html',
        'relations.html',
        'searchbox.html',
        'donate.html',
        'versioning.html',
    ]
}
