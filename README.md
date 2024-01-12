# Compute

Compute instances management library.

## Docs

Documantation is available [here](https://nixhacks.net/hstack/compute/master/index.html).
To build actual docs run `make serve-docs`. See [Development](#development) below.

## Roadmap

- [x] Create instances
- [x] CDROM
- [x] cloud-init for provisioning instances
- [x] Power management
- [x] Pause and resume
- [x] vCPU hotplug
- [x] Memory hotplug
- [x] Hot disk resize [not tested]
- [x] CPU customization (emulation mode, model, vendor, features)
- [x] CPU topology customization
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
- [ ] Instance clones (thin, fat)
- [ ] MicroVM

## Development

Python 3.11+ is required.

Install [poetry](https://python-poetry.org/), clone this repository and run:

```
poetry install --with dev --with docs
```

## Build Debian package

Install Docker first, then run:

```
make build-deb
```

`compute` and `compute-doc` packages will built. See packaging/build directory.

## Installation

See [Installation](https://nixhacks.net/hstack/compute/master/installation.html).

## Basic usage

To get help run:

```
compute --help
```

See [CLI docs](https://nixhacks.net/hstack/compute/master/cli/index.html) for more info.

Also you can use `compute` as generic Python library. For example:

```python
import compute

with compute.Session() as session:
    instance = session.get_instance('myinstance')
    if not instance.is_running():
        instance.start()
    else:
        print('instance is already running')
```
