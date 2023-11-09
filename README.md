# Compute

Compute instances management library and tools.

## Docs

Run `make serve-docs`. See [Development](#development) below.

## Roadmap

- [x] Create instances
- [ ] CDROM
- [ ] cloud-init for provisioning instances
- [x] Instance power management
- [ ] Instance pause and resume
- [x] vCPU hotplug
- [ ] Memory hotplug
- [x] Hot disk resize [not tested]
- [ ] CPU topology customization
- [x] CPU customization (emulation mode, model, vendor, features)
- [ ] BIOS/UEFI settings
- [x] Device attaching
- [ ] Device detaching
- [ ] GPU passthrough
- [ ] CPU guarantied resource percent support
- [x] QEMU Guest Agent management
- [ ] Instance resources usage stats
- [ ] SSH-keys management
- [x] Setting user passwords in guest [not tested]
- [ ] LXC
- [x] QCOW2 disks support
- [ ] ZVOL support
- [ ] Network disks support
- [ ] Images service integration (Images service is not implemented yet)
- [ ] Manage storage pools
- [ ] Instance snapshots
- [ ] Instance backups
- [ ] Instance migrations
- [ ] Idempotency
- [ ] HTTP API
- [ ] CLI [in progress]

## Development

Python 3.11+ is required.

Install [poetry](https://python-poetry.org/), clone this repository and run:

```
poetry install --with dev --with docs
```
