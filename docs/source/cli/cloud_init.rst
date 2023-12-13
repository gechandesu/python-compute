Using Cloud-init
================

Cloud-init for new instances
----------------------------

Cloud-init configs may be set inplace into :file:`instance.yaml`.

.. code-block:: yaml
   :caption: Example with Debian generic QCOW2 image
   :linenos:

   name: genericdebian
   memory: 1024
   vcpus: 1
   image: debian-12-generic-amd64.qcow2
   volumes:
     - type: file
       is_system: true
       capacity:
         value: 5
         unit: GiB
   cloud_init:
     meta_data:
       hostname: genericdebian
       root_pass: secure_pass
     user_data: |
       ## template: jinja
       #cloud-config
       hostname: {{ ds.meta_data.hostname }}
       fqdn: {{ ds.meta_data.hostname }}.instances.generic.cloud
       manage_etc_hosts: true
       chpasswd:
         users:
           - name: root
             password: {{ ds.meta_data.root_pass }}
             type: text
         expire: False
       ssh_pwauth: True
       package_update: true
       package_upgrade: true
       packages:
         - qemu-guest-agent
         - vim
         - psmisc
         - htop
       runcmd:
         - [ systemctl, daemon-reload ]
         - [ systemctl, enable, qemu-guest-agent.service ]
         - [ systemctl, start, --no-block, qemu-guest-agent.service ]

You can use separate file in this way:

.. code-block:: yaml
   :caption: user-data in separate file
   :emphasize-lines: 11-
   :linenos:

   name: genericdebian
   memory: 1024
   vcpus: 1
   image: debian-12-generic-amd64.qcow2
   volumes:
     - type: file
       is_system: true
       capacity:
         value: 25
         unit: GiB
   cloud_init:
     user_data: user-data.yaml

Base64 encoded string with data must be ``base64:`` prefixed:

.. code-block:: yaml
   :caption: user-data as base64 encoded string
   :emphasize-lines: 11-
   :linenos:

   name: genericdebian
   memory: 1024
   vcpus: 1
   image: debian-12-generic-amd64.qcow2
   volumes:
     - type: file
       is_system: true
       capacity:
         value: 25
         unit: GiB
   cloud_init:
     user_data: base64:I2Nsb3VkLWNvbmZpZwpob3N0bmFtZTogY2xvdWRlYmlhbgpmcWRuOiBjbG91ZGViaWFuLmV4YW1wbGUuY29tCm1hbmFnZV9ldGNfaG9zdHM6IHRydWUK

Also you can write config in YAML. Please note that in this case you will not be able to use the ``#cloud-config`` shebang.

.. code-block:: yaml
   :caption: meta-data as nested YAML
   :emphasize-lines: 12-14
   :linenos:

   name: genericdebian
   memory: 1024
   vcpus: 1
   image: debian-12-generic-amd64.qcow2
   volumes:
     - type: file
       is_system: true
       capacity:
         value: 25
         unit: GiB
   cloud_init:
     meta_data:
       myvar: example
       another_one: example_2
     user_data: |
       #cloud-config
       #something here

Edit Cloud-init config files on existing instance
-------------------------------------------------

Use ``setcloudinit`` subcommand::

    compute setcloudinit myinstance --user-data user_data.yaml

See `setcloudinit <../cli/reference.html#setcloudinit>`_ for details.
