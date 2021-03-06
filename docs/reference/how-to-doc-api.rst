Documenting your API
--------------------

Each instance of Pulp hosts dynamically generated REST API documentation located at
`http://pulpserver/pulp/api/v3/docs/`.

The documentation is generated using `ReDoc <https://github.com/Rebilly/ReDoc>`_ based on the
`OpenAPI 2.0 <https://github.com/OAI/OpenAPI-Specification/blob/master/versions/2.0.md>`_ schema
generated by Pulp. The schema generator iterates over all the Views and Viewsets in every plugin
and generates the schema based on the information provided by Viewset doc strings, Viewset method
docstrings, associated Model's names, View docstrings, and the help text from serializers.

Individual parameters and responses are documented automatically based on the Serializer field type.
A field's description is generated from the "help_text" kwarg when defining serializer fields.

Response status codes can be generated through the `Meta` class on the serializer:

.. code-block:: python

    from rest_framework.status import HTTP_400_BAD_REQUEST

    class SnippetSerializerV1(serializers.Serializer):
        title = serializers.CharField(required=False, allow_blank=True, max_length=100)

        class Meta:
            error_status_codes = {
                HTTP_400_BAD_REQUEST: 'Bad Request'
            }


.. note::

    Plugin authors can provide manual overrides using the `@swagger_auto_schema decorator
    <https://drf-yasg.readthedocs.io/en/stable/drf_yasg.html#drf_yasg.utils.swagger_auto_schema>`_

The OpenAPI schema for pulpcore and all installed plugins can be downloaded from the ``pulp-api``
server:

.. code-block:: bash

    curl -o api.json http://localhost:24817/pulp/api/v3/docs/api.json

The OpenAPI schema for a specific plugin can be downloaded by specifying the plugin's module name
as a GET parameter. For example for pulp_rpm only endpoints use a query like this:

.. code-block:: bash

    curl -o api.json http://localhost:24817/pulp/api/v3/docs/api.json?plugin=pulp_rpm
