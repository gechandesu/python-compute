Python API
==========

API позволяет выполнять действия над инстансами программно. Ниже описано пример
изменения параметров и запуска инстанса `myinstance`.

.. code-block:: python

    import logging

    from compute import Session


    logging.basicConfig(level=logging.DEBUG)

    with Session() as session:
        instance = session.get_instance('myinstance')
        instance.set_vcpus(4)
        instance.start()
        instance.set_autostart(enabled=True)


Контекстный менеджер :class:`Session` предоставляет абстракцию над :class:`libvirt.virConnect`
и возвращает объекты других классов настоящей билиотеки.

Представление сущностей
-----------------------

Такие сущности как Сompute-инстанс представлены в виде классов. Эти классы напрямую
вызывают методы libvirt для выполнения операций на гипервизоре. Пример класса — :data:`Volume`.

Конфигурационные файлы различных объектов libvirt в compute описаны специальными
датаклассами. Датакласс хранит в своих свойствах параметры объекта и может вернуть XML
конфиг для libvirt с помощью метода ``to_xml()``. Пример — :py:class:`VolumeConfig`.

Для валидации входных данных используются модели `Pydantic <https://docs.pydantic.dev/>`_.
Пример — :py:class:`VolumeSchema`.

Документация модулей
--------------------

.. toctree::
    :maxdepth: 4

    session
    instance/index
    storage
