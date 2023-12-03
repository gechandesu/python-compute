# Compute

Compute instances management library and tools.

## Docs

Run `make serve-docs`. See [Development](#development) below.

## Roadmap

- [x] Create instances
- [x] CDROM
- [ ] cloud-init for provisioning instances
- [x] Power management
- [x] Pause and resume
- [x] vCPU hotplug
- [x] Memory hotplug
- [x] Hot disk resize [not tested]
- [x] CPU customization (emulation mode, model, vendor, features)
- [ ] CPU topology customization
- [ ] BIOS/UEFI settings
- [x] Device attaching
- [x] Device detaching
- [ ] GPU passthrough
- [ ] CPU guarantied resource percent support
- [x] QEMU Guest Agent management
- [ ] Resource usage stats
- [x] SSH-keys management
- [x] Setting user passwords in guest
- [x] QCOW2 disks support
- [ ] ZVOL support
- [ ] Network disks support
- [ ] Images service integration (Images service is not implemented yet)
- [ ] Manage storage pools
- [ ] Idempotency
- [ ] CLI [in progress]
- [ ] HTTP API
- [ ] Migrations
- [ ] Snapshots
- [ ] Backups
- [ ] LXC
- [ ] Attaching CDROM from sources: block, (http|https|ftp|ftps|tftp)://

## Development

Python 3.11+ is required.

Install [poetry](https://python-poetry.org/), clone this repository and run:

```
poetry install --with dev --with docs
```

# Build Debian package

Install Docker first, then run:

```
make build-deb
```

`compute` and `compute-doc` packages will built. See packaging/build directory.

# Installation

Packages can be installed via `dpkg` or `apt-get`:

```
# apt-get install ./compute*.deb
```

After installation prepare environment, run following command to start libvirtd and create required storage pools:

```
# systemctl enable --now libvirtd.service
# virsh net-start default
# virsh net-autostart default
# for pool in images volumes; do
    virsh pool-define-as $pool dir - - - - "/$pool"
    virsh pool-build $pool
    virsh pool-start $pool
    virsh pool-autostart $pool
done
```

Then set environment variables in your `~/.profile`, `~/.bashrc` or global in `/etc/profile.d/compute` or `/etc/bash.bashrc`:

```
export CMP_IMAGES_POOL=images
export CMP_VOLUMES_POOL=volumes
```

Configuration file is yet not supported.

Make sure the variables are exported to the environment:

```
printenv | grep CMP_
```

If the command didn't show anything _source_ your rc files or relogin.


# Basic usage

To get help run:

```
compute --help
```

Also you can use `compute` as generic Python library. For example:

```python
from compute import Session

with Session() as session:
    instance = session.get_instance('myinstance')
    if not instance.is_running():
        instance.start()
    else:
        print('instance is already running')
```

# Create compute instances

Place your qcow2 image in `/images` directory. For example `debian_12.qcow2`.

Create `instance.yaml` file with following content:

```yaml
name: myinstance
memory: 2048  # memory in MiB
vcpus: 2
image: debian_12.qcow2
volumes:
  - type: file
    is_system: true
    target: vda
    capacity:
      value: 10
      unit: GiB
```

Refer to `Instance` class docs for more info. Full `instance.yaml` example will be provided later.

To initialise instance run:

```
compute -l debug init instance.yaml
```

Start instance:

```
compute start myinstance
```
