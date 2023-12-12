Getting started
===============

Creating compute instances
--------------------------

Compute instances are created through a description in yaml format. The description may be partial, the configuration will be supplemented with default parameters.

This page describes how to start up a basic instance, you'll probably want to use cloud-init to get the guest up and running, see the instructions at `Using cloud-init <cloud_init.html>`_.

The following examples contains minimal instance configuration. See also full example `here <instance_file.html>`_

Using prebuilt QCOW2 disk image
```````````````````````````````

First place your image into ``images`` pool path.

Create :file:`instance.yaml` config file with following content. Replace `debian_12.qcow2` with your actual image filename.

.. code-block:: yaml
   :caption: Using prebuilt QCOW2 disk image
   :emphasize-lines: 4
   :linenos:

   name: myinstance
   memory: 2048
   vcpus: 2
   image: debian_12.qcow2
   volumes:
     - type: file
       is_system: true
       capacity:
         value: 10
         unit: GiB

Check out what configuration will be applied when ``init``::

   compute init --test

Initialise instance with command::

   compute init

Also you can use following syntax::

  compute init yourfile.yaml

Start instance::

   compute start myinstance

Using ISO installation medium
`````````````````````````````

Download ISO image and set it as source for ``cdrom`` device.

Note that the ``image`` parameter is not used here.

.. code-block:: yaml
   :caption: Using ISO image
   :emphasize-lines: 10-12
   :linenos:

   name: myinstance
   memory: 2048
   vcpus: 2
   volumes:
     - type: file
       is_system: true
       capacity:
         value: 10
         unit: GiB
     - type: file
       device: cdrom
       source: /images/debian-12.2.0-amd64-netinst.iso

::

   compute init

Now edit instance XML configuration to add VNC-server listen address::

   virsh edit myinstance

Add ``address`` attribute to start listen on all host network interfaces.

.. code-block:: xml
   :caption: libvirt XML config fragment
   :emphasize-lines: 2

   <graphics type='vnc' port='-1' autoport='yes'>
     <listen type='address' address='0.0.0.0'/>
   </graphics>

Also you can specify VNC server port. This is **5900** by default.

Start instance and connect to VNC via any VNC client such as `Remmina <https://remmina.org/>`_ or something else.

::

   compute start myinstance

Finish the OS installation over VNC and then do::

   compute setcdrom myinstance --detach /images/debian-12.2.0-amd64-netinst.iso
   compute powrst myinstance

CDROM will be detached. ``powrst`` command will perform instance shutdown and start. Instance will booted from `vda` disk.

Using existing disk
```````````````````

Place your disk image in ``volumes`` storage pool.

Replace `/volume/myvolume.qcow2` with actual path to disk.

.. code-block:: yaml
   :caption: Using existing disk
   :emphasize-lines: 7
   :linenos:

   name: myinstance
   memory: 2048
   vcpus: 2
   volumes:
     - type: file
       is_system: true
       source: /volumes/myvolume.qcow2

Initialise and start instance::

    compute init --start
