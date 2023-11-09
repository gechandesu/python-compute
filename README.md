# Compute

Compute instances management library and tools.

## Docs

Run `make serve-docs`. See [Development](#development) below.

## Roadmap

- [x] Create instances
- [ ] CDROM
- [ ] cloud-init for provisioning instances
- [x] Instance power management
- [x] Instance pause and resume
- [x] vCPU hotplug
- [x] Memory hotplug
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
- [x] QCOW2 disks support
- [ ] ZVOL support
- [ ] Network disks support
- [ ] Images service integration (Images service is not implemented yet)
- [ ] Manage storage pools
- [ ] Idempotency
- [ ] CLI [in progress]
- [ ] HTTP API
- [ ] Instance migrations
- [ ] Instance snapshots
- [ ] Instance backups
- [ ] LXC

## Development

Python 3.11+ is required.

Install [poetry](https://python-poetry.org/), clone this repository and run:

```
poetry install --with dev --with docs
```
