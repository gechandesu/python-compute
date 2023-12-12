Configuration
=============

Configuration can be stored in configration file or in environment variables prefixed with ``CMP_``.

Configuration file must have TOML format. Example configuration:

.. literalinclude:: ../../computed.toml
   :caption: /etc/compute/computed.toml
   :language: toml

There are:

``libvirt.uri``
    Libvirt connection URI.

    | Env: ``CMP_LIBVIRT_URI``
    | Default: ``qemu:///system``

``storage.images``
    Name of libvirt storage pool to store compute instance etalon images.
    `compute` takes images from here and creates disks for compute instances
    based on them.

    | Env: ``CMP_IMAGES_POOL``
    | Default: ``images``

``storage.volumes``
    Name of libvirt storage pool to store compute instance disks.

    | Env: ``CMP_VOLUMES_POOL``
    | Default: ``volumes``

.. NOTE::

   ``storage.images`` and ``storage.volumes`` must be exist. Make sure that these
   pools are defined, running, and have the autostart flag.
