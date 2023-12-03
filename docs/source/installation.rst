Installation
============

Install Debian 12 on your host system. If you want use virtual machine as host make sure that nested virtualization is enabled.

1. Download or build ``compute`` DEB packages.
2. Install packages::

      apt-get install ./compute*

3. Make sure that ``libvirtd`` and ``dnsmasq`` are enabled and running::

      systemctl enable --now libvirtd.service
      systemctl enable --now dnsmasq.service

4. Prepare storage pools. You need storage pool for images and for instance volumes.

   ::

      for pool in images volumes; do
          virsh pool-define-as $pool dir - - - - "/$pool"
          virsh pool-build $pool
          virsh pool-start $pool
          virsh pool-autostart $pool
      done

5. Prepare env. Set environment variables in your `~/.profile`, `~/.bashrc` or global in `/etc/profile.d/compute` or `/etc/bash.bashrc`:

   .. code-block:: sh

      export CMP_IMAGES_POOL=images
      export CMP_VOLUMES_POOL=volumes

   Configuration file is yet not supported.

   Make sure the variables are exported to the environment::

      printenv | grep CMP_

   If the command didn't show anything source your rc files or relogin.

6. Prepare network::

      virsh net-start default
      virsh net-autostart default

7. Done. Now you can follow `CLI instructions <cli/index.html>`_
