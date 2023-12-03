Usage
=====

Creating compute instances
--------------------------

First place your image into images pool path.

Create :file:`inatance.yaml` config file with following content. Replace `debian_12.qcow2` with your actual image filename.

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
       target: vda
       capacity:
         value: 10
         unit: GiB

Check out what configuration will be applied when ``init``::

   compute init -t

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
   :emphasize-lines: 11-13
   :linenos:

   name: myinstance
   memory: 2048
   vcpus: 2
   volumes:
     - type: file
       is_system: true
       target: vda
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
   :linenos:

   <graphics type='vnc' port='-1' autoport='yes' listen='0.0.0.0'>
     <listen type='address' address='0.0.0.0'/>
   </graphics>

Also you can specify VNC server port. This is **5900** by default.

Start instance and connect to VNC via any VNC client such as `Remmina <https://remmina.org/>`_ or something else.

::

   compute start myinstance

Finish the OS installation over VNC and then do::

   compute setcdrom myinstance /images/debian-12.2.0-amd64-netinst.iso --detach
   compute powrst myinstance

CDROM will be detached. ``powrst`` command will perform instance shutdown and start. Instance will booted from `vda` disk.
