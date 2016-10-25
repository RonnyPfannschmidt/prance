{{ fullname }}
{{ underline }}

.. toctree::
   :maxdepth: 4

.. autosummary::
   :toctree: _autosummary

.. automodule:: {{ fullname }}
   :members:
   :undoc-members:
   :inherited-members:
   :show-inheritance:

{% if exceptions: %}

Exception Summary
-----------------

{% for excname in exceptions: %}
.. autosummary:: {{ excname }}
{% endfor %}

Exception Details
-----------------

{% for excname in exceptions: %}
.. autoexception:: {{ excname }}
   :members:
   :inherited-members:
   :show-inheritance:
{% endfor %}

{% endif %}

{% if classes %}

Class Summary
-------------

{% for classname in classes: %}
.. autosummary:: {{ classname }}
{% endfor %}

Class Details
-------------

{% for classname in classes: %}
.. autoclass:: {{ classname }}
   :members:
   :undoc-members:
   :inherited-members:
   :show-inheritance:
{% endfor %}

{% endif %}

{% if functions %}

Function Summary
----------------

{% for func in functions: %}
.. autosummary:: {{ func }}
{% endfor %}

Function Details
----------------

{% for func in functions: %}
.. autofunction:: {{ func }}
{% endfor %}

{% endif %}

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
