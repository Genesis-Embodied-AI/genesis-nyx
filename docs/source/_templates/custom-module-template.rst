{{ fullname.split('.') | last | escape | underline }}

{# Sphinx's recursive autosummary discovers package contents via a filesystem
   walk of __path__. The gs_nyx package ships native runtime libs as siblings
   of the real Python C extensions (libslang.so, libSPIRV-Tools-shared.so,
   libOpenImageDenoise.so.*, libtbb.so.12, libvulkan.so.1, ...). Depending on
   how Sphinx classifies each one it can land in any of the discovered-member
   lists below — and trying to import them fails since they have no PyInit_*
   entry point. Filter every list defensively. #}
{% set py_attributes = [] %}
{% for item in attributes %}
{%- if not (item.split('.') | last).startswith('lib') %}
{%- set _ = py_attributes.append(item) %}
{%- endif %}
{%- endfor %}
{% set py_functions = [] %}
{% for item in functions %}
{%- if not (item.split('.') | last).startswith('lib') %}
{%- set _ = py_functions.append(item) %}
{%- endif %}
{%- endfor %}
{% set py_classes = [] %}
{% for item in classes %}
{%- if not (item.split('.') | last).startswith('lib') %}
{%- set _ = py_classes.append(item) %}
{%- endif %}
{%- endfor %}
{% set py_exceptions = [] %}
{% for item in exceptions %}
{%- if not (item.split('.') | last).startswith('lib') %}
{%- set _ = py_exceptions.append(item) %}
{%- endif %}
{%- endfor %}
{% set py_modules = [] %}
{% for item in modules %}
{%- if not (item.split('.') | last).startswith('lib') %}
{%- set _ = py_modules.append(item) %}
{%- endif %}
{%- endfor %}

.. automodule:: {{ fullname }}

   {% block attributes %}
   {% if py_attributes %}
   .. rubric:: Module attributes

   .. autosummary::
      :toctree:
   {% for item in py_attributes %}
      {{ item }}
   {%- endfor %}
   {% endif %}
   {% endblock %}

   {% block functions %}
   {% if py_functions %}
   .. rubric:: {{ _('Functions') }}

   .. autosummary::
      :toctree:
   {% for item in py_functions %}
      {{ item }}
   {%- endfor %}
   {% endif %}
   {% endblock %}

   {% block classes %}
   {% if py_classes %}
   .. rubric:: {{ _('Classes') }}

   .. autosummary::
      :toctree:
      :template: custom-class-template.rst
   {% for item in py_classes %}
      {{ item }}
   {%- endfor %}
   {% endif %}
   {% endblock %}

   {% block exceptions %}
   {% if py_exceptions %}
   .. rubric:: {{ _('Exceptions') }}

   .. autosummary::
      :toctree:
   {% for item in py_exceptions %}
      {{ item }}
   {%- endfor %}
   {% endif %}
   {% endblock %}

{% block modules %}
{% if py_modules %}
.. rubric:: Submodules

.. autosummary::
   :toctree:
   :template: custom-module-template.rst
   :recursive:
{% for item in py_modules %}
   {{ item }}
{%- endfor %}
{% endif %}
{% endblock %}
