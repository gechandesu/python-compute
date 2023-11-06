# Compute

Compute-instance management library and tools.

Currently supports only QEMU/KVM based virtual machines.

## Docs

Run `make serve-docs`.

## Roadmap

- [x] Create instances
- [ ] CDROM
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
- [ ] HTTP API
- [ ] Full functional CLI [in progress]
