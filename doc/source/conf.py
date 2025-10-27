# -- General configuration -----------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['openstackdocstheme']

todo_include_todos = True

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = 'requirements'
copyright = '2017-present, OpenStack Foundation'

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
add_module_names = False

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'native'

# A list of ignored prefixes for module index sorting.
modindex_common_prefix = ['requirements-doc.']

# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'openstackdocs'

# If false, no module index is generated.
html_domain_indices = False

# If false, no index is generated.
html_use_index = False

# -- Options for LaTeX output --------------------------------------------------

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
    (
        'index',
        'RequirementsGuide.tex',
        'Global Requirements Guide',
        'OpenStack contributors',
        'manual',
    ),
]

# -- Options for openstackdocstheme extension ----------------------------------

openstackdocs_repo_name = 'openstack/requirements'
openstackdocs_auto_name = False
openstackdocs_bug_project = 'openstack-requirements'
openstackdocs_bug_tag = ''
