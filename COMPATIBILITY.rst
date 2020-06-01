Compatibility Issues
====================

Because no specification is perfect, and OpenAPI certainly isn't, there are
a number of compatibility issues that prance users have found. Here is some
explanation and rationale of them.

Most of the issues stem from the fact that OpenAPI refers to JSON schema and
related standards for its specification, but then subtly violates JSON schema
or those other standards.

Strict Mode
-----------

JSON only accepts string keys in objects. However, some keys in the specs tend
to be integer values, most notably the status codes for responses. Strict mode
rejects non-string keys; the default lenient mode accepts them.

Since the ``flex`` validator is not based on JSON, it does not have this issue.
The ``strict`` option therefore does not apply here.

JSON References #1 - Ignoring Additional Keys
---------------------------------------------

The relevant parts of the RFC for JSON references can be condensed like this:

    A JSON Reference is a JSON object, which contains a member named
    "$ref", which has a JSON string value.  Example:

    { "$ref": "http://example.com/example.json#/foo/bar" }

    (...)

    Any members other than "$ref" in a JSON Reference object SHALL be
    ignored.

    (...)

    Resolution of a JSON Reference object SHOULD yield the referenced
    JSON value.  Implementations MAY choose to replace the reference with
    the referenced value.

Prance is strict about ignoring additional keys, and does so by replacing the reference with
the referenced value.

In practice, that means that given such a reference:

.. code:: yaml

    # main file
    ---
    foo: bar
    $ref: /path/to/ref

    # and at /path/to/ref
    ---
    baz: quux

Then, after resolution, the result is the following:

.. code:: yaml

    # resolved
    ---
    baz: quux

That is, the key ``foo`` is ignored as the specs require. That is the reason
the OpenAPI specs tend to use JSON references within ``schema`` objects, and
place any other parameters as siblings of the ``schema`` object.

JSON References #2 - Recursion Limits
-------------------------------------

Since JSON references can reference an object that references the first object,
we can create recursive references. By default, when a recursion is detected,
an exception is raised. There are two ways you can modify this behaviour:

1. Increase the ``recursion_limit`` from it's default value of ``1`` to some higher
   number. This doesn't actually help much on its own.

2. Set the ``recursion_limit_handler`` parameter to a callable. It accepts the
   recursion limit, the reference URL of the element being resolved, and the
   currently known recursions.

``prance.util.resolver.default_reclimit_handler`` is the default handler, and
will always raise an exception.

If the handler you set does not raise an exception, its return value is used
as the "resolved" value. To simply ignore recursions, use a handler that
returns ``None`` - this will translate to the null value in the specs.

JSON References #3 - What is a Reference?
-----------------------------------------

While OpenAPI specifies that ``$ref`` is only to be interpreted as a
reference in specific places, the JSON specs say nothing of the sort. Since
most backends are based on JSON schema validators, prance simply treats all
occurrences of ``$ref`` as references. This works well with the expecations of
JSON schema/JSON references, albeit not OpenAPI's interpretation of them.

This limitation is also not present in OpenAPI 2.0 specs. While those specs
are older, they're still supported by prance. Compatibility between the
interpretation of 2.0 vs. 3.0.0 is probably more user friendly than allowing
`$ref` to be interpreted in different ways in different places, in violation
of JSON reference specs.


