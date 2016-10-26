{{ fullname }}
{{ underline }}

.. toctree::

.. automodule:: {{ fullname }}
   :members:
   :undoc-members:
   :inherited-members:
   :show-inheritance:

{% block exceptions %}
{% if exceptions: %}

Exceptions
----------

{% for excname in exceptions: %}
.. autoexception:: {{ excname }}
   :members:
   :inherited-members:
   :show-inheritance:
{% endfor %}

{% endif %}
{% endblock %}

{% block classes %}
{% if classes %}

Classes
-------

{% for classname in classes: %}
.. autoclass:: {{ classname }}
   :members:
   :undoc-members:
   :inherited-members:
   :show-inheritance:
{% endfor %}

{% endif %}
{% endblock %}

{% block functions %}
{% if functions %}

Functions
---------

{% for func in functions: %}
.. autofunction:: {{ func }}
{% endfor %}

{% endif %}
{% endblock %}
