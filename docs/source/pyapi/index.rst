Python API
==========

The API allows you to perform actions on instances programmatically.

.. code-block:: python

    import compute

    with compute.Session() as session:
        instance = session.get_instance('myinstance')
        info = instance.get_info()

    print(info)


:class:`Session` context manager provides an abstraction over :class:`libvirt.virConnect`
and returns objects of other classes of the present library.

Entity representation
---------------------

Entities such as a compute-instance are represented as classes. These classes directly
call libvirt methods to perform operations on the hypervisor. An example class is
:class:`Volume`.

The configuration files of various libvirt objects in `compute` are described by special
dataclasses. The dataclass stores object parameters in its properties and can return an
XML config for libvirt using the ``to_xml()`` method. For example :class:`VolumeConfig`.

`Pydantic <https://docs.pydantic.dev/>`_ models are used to validate input data.
For example :class:`VolumeSchema`.

Modules documentation
---------------------

.. toctree::
    :maxdepth: 4

    session
    instance/index
    storage/index
    utils
    exceptions
