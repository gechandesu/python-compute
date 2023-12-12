# This file is part of Compute
#
# Compute is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Compute is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Compute.  If not, see <http://www.gnu.org/licenses/>.

"""CLI commands."""

import argparse
import base64
import json
import logging
import pathlib
import re
import shlex
import sys
import uuid

import libvirt
import pydantic
import yaml

from compute import Session
from compute.cli.term import Table, confirm
from compute.exceptions import GuestAgentTimeoutExpired
from compute.instance import CloudInit, GuestAgent, InstanceSchema
from compute.instance.devices import DiskConfig, DiskDriver
from compute.utils import dictutil, diskutils, ids


log = logging.getLogger(__name__)

libvirt.registerErrorHandler(
    lambda userdata, err: None,  # noqa: ARG005
    ctx=None,
)


def init(session: Session, args: argparse.Namespace) -> None:
    """Initialise compute instance using YAML config."""
    try:
        data = yaml.load(args.file.read(), Loader=yaml.SafeLoader)
        log.debug('Read from file: %s', data)
    except yaml.YAMLError as e:
        sys.exit(f'error: cannot parse YAML: {e}')
    capabilities = session.get_capabilities()
    node_info = session.get_node_info()
    base_instance_config = {
        'name': str(uuid.uuid4()),
        'title': None,
        'description': None,
        'arch': capabilities.arch,
        'machine': capabilities.machine,
        'emulator': capabilities.emulator,
        'max_vcpus': node_info.cpus,
        'max_memory': node_info.memory,
        'cpu': {
            'emulation_mode': 'host-passthrough',
            'model': None,
            'vendor': None,
            'topology': None,
            'features': None,
        },
        'network_interfaces': [
            {
                'source': 'default',
                'mac': ids.random_mac(),
            },
        ],
        'boot': {'order': ['cdrom', 'hd']},
        'cloud_init': None,
    }
    data = dictutil.override(base_instance_config, data)
    volumes = []
    targets = []
    for volume in data['volumes']:
        base_disk_config = {
            'bus': 'virtio',
            'is_readonly': False,
            'driver': {
                'name': 'qemu',
                'type': 'qcow2',
                'cache': 'writethrough',
            },
        }
        base_cdrom_config = {
            'bus': 'ide',
            'is_readonly': True,
            'driver': {
                'name': 'qemu',
                'type': 'raw',
                'cache': 'writethrough',
            },
        }
        if volume.get('device') is None:
            volume['device'] = 'disk'
        if volume.get('target') is None:
            prefix = 'hd' if volume['device'] == 'cdrom' else 'vd'
            target = diskutils.get_disk_target(targets, prefix)
            volume['target'] = target
            targets.append(target)
        else:
            targets.append(volume['target'])
        if volume['device'] == 'disk':
            volumes.append(dictutil.override(base_disk_config, volume))
        if volume['device'] == 'cdrom':
            volumes.append(dictutil.override(base_cdrom_config, volume))
    data['volumes'] = volumes
    if data['cloud_init'] is not None:
        cloud_init_config = {
            'user_data': None,
            'meta_data': None,
            'vendor_data': None,
            'network_config': None,
        }
        data['cloud_init'] = dictutil.override(
            cloud_init_config,
            data['cloud_init'],
        )
        for item in data['cloud_init']:
            cidata = data['cloud_init'][item]
            if cidata is None:
                pass
            elif isinstance(cidata, str):
                if cidata.startswith('base64:'):
                    data['cloud_init'][item] = base64.b64decode(
                        cidata.split(':')[1]
                    ).decode('utf-8')
                elif re.fullmatch(r'^[^\n]{1,1024}$', cidata, re.I):
                    data_file = pathlib.Path(cidata)
                    if data_file.exists():
                        with data_file.open('r') as f:
                            data['cloud_init'][item] = f.read()
                else:
                    pass
            else:
                data['cloud_init'][item] = yaml.dump(cidata)
    try:
        log.debug('Input data: %s', data)
        if args.test:
            _ = InstanceSchema(**data)
            print(json.dumps(dict(data), indent=4, sort_keys=True))
            sys.exit()
        instance = session.create_instance(**data)
        print(f'Initialised: {instance.name}')
        if args.start:
            instance.start()
            print(f'Started: {instance.name}')
    except pydantic.ValidationError as e:
        for error in e.errors():
            fields = '.'.join([str(lc) for lc in error['loc']])
            print(
                f"validation error: {fields}: {error['msg']}",
                file=sys.stderr,
            )


def exec_(session: Session, args: argparse.Namespace) -> None:
    """
    Execute command in guest via guest agent.

    NOTE: any argument after instance name will be passed into guest's shell
    """
    instance = session.get_instance(args.instance)
    ga = GuestAgent(instance.domain, timeout=args.timeout)
    arguments = args.arguments.copy()
    if len(arguments) > 1 and not args.no_join_args:
        arguments = [shlex.join(arguments)]
    if not args.no_join_args:
        arguments.insert(0, '-c')
    stdin = None
    if not sys.stdin.isatty():
        stdin = sys.stdin.read()
    try:
        output = ga.guest_exec(
            path=args.executable,
            args=arguments,
            env=args.env,
            stdin=stdin,
            capture_output=True,
            decode_output=True,
            poll=True,
        )
    except GuestAgentTimeoutExpired as e:
        sys.exit(
            f'{e}. NOTE: command may still running in guest, '
            f'PID={ga.last_pid}'
        )
    if output.stderr:
        print(output.stderr.strip(), file=sys.stderr)
    if output.stdout:
        print(output.stdout.strip(), file=sys.stdout)
    sys.exit(output.exitcode)


def ls(session: Session, args: argparse.Namespace) -> None:  # noqa: ARG001
    """List compute instances."""
    table = Table()
    table.header = ['NAME', 'STATE', 'NVCPUS', 'MEMORY']
    for instance in session.list_instances():
        info = instance.get_info()
        table.add_row(
            [
                instance.name,
                instance.get_status() + ' ',
                info.nproc,
                f'{int(info.memory / 1024)} MiB',
            ]
        )
    print(table)


def lsdisks(session: Session, args: argparse.Namespace) -> None:
    """List block devices attached to instance."""
    instance = session.get_instance(args.instance)
    if args.persistent:
        disks = instance.list_disks(persistent=True)
    else:
        disks = instance.list_disks()
    table = Table()
    table.header = ['TARGET', 'SOURCE']
    for disk in disks:
        table.add_row([disk.target, disk.source])
    print(table)


def start(session: Session, args: argparse.Namespace) -> None:
    """Start instance."""
    instance = session.get_instance(args.instance)
    instance.start()


def shutdown(session: Session, args: argparse.Namespace) -> None:
    """Shutdown instance."""
    instance = session.get_instance(args.instance)
    if args.soft:
        method = 'SOFT'
    elif args.hard:
        method = 'HARD'
    elif args.unsafe:
        method = 'UNSAFE'
    else:
        method = 'NORMAL'
    instance.shutdown(method)


def reboot(session: Session, args: argparse.Namespace) -> None:
    """Reboot instance."""
    instance = session.get_instance(args.instance)
    instance.reboot()


def reset(session: Session, args: argparse.Namespace) -> None:
    """Reset instance."""
    instance = session.get_instance(args.instance)
    instance.reset()


def powrst(session: Session, args: argparse.Namespace) -> None:
    """Power reset instance."""
    instance = session.get_instance(args.instance)
    instance.power_reset()


def pause(session: Session, args: argparse.Namespace) -> None:
    """Pause instance."""
    instance = session.get_instance(args.instance)
    instance.pause()


def resume(session: Session, args: argparse.Namespace) -> None:
    """Resume instance."""
    instance = session.get_instance(args.instance)
    instance.resume()


def status(session: Session, args: argparse.Namespace) -> None:
    """Display instance status."""
    instance = session.get_instance(args.instance)
    print(instance.get_status())


def setvcpus(session: Session, args: argparse.Namespace) -> None:
    """Set instance vCPU number."""
    instance = session.get_instance(args.instance)
    instance.set_vcpus(args.nvcpus, live=True)


def setmem(session: Session, args: argparse.Namespace) -> None:
    """Set instance memory size."""
    instance = session.get_instance(args.instance)
    instance.set_memory(args.memory, live=True)


def setpass(session: Session, args: argparse.Namespace) -> None:
    """Set user password in guest."""
    instance = session.get_instance(args.instance)
    instance.set_user_password(
        args.username,
        args.password,
        encrypted=args.encrypted,
    )


def setcdrom(session: Session, args: argparse.Namespace) -> None:
    """Manage CDROM devices."""
    instance = session.get_instance(args.instance)
    if args.detach:
        for disk in instance.list_disks(persistent=True):
            if disk.device == 'cdrom' and disk.source == args.source:
                instance.detach_disk(disk.target, live=False)
                print(
                    f"disk '{disk.target}' detached, "
                    'perform power reset to apply changes'
                )
        return
    disks_live = instance.list_disks(persistent=False)
    disks_inactive = instance.list_disks(persistent=True)
    disks = [d.target for d in disks_inactive if d not in disks_live]
    target = diskutils.get_disk_target(disks, 'hd')
    cdrom = DiskConfig(
        type='file',
        device='cdrom',
        source=args.source,
        target=target,
        is_readonly=True,
        bus='ide',
        driver=DiskDriver('qemu', 'raw', 'writethrough'),
    )
    instance.attach_device(cdrom, live=False)
    print(
        f"CDROM attached as disk '{target}', "
        'perform power reset to apply changes'
    )


def setcloudinit(session: Session, args: argparse.Namespace) -> None:
    """
    Set cloud-init configuration.

    The cloud-init disk must not be mounted to the host system while making
    changes using this command! In this case, data may be damaged when writing
    to disk - if the new content of the file is longer than the old one, it
    will be truncated.
    """
    if (
        args.user_data is None
        and args.vendor_data is None
        and args.network_config is None
        and args.meta_data is None
    ):
        sys.exit('nothing to do')
    instance = session.get_instance(args.instance)
    disks = instance.list_disks()
    cloud_init_disk_path = None
    cloud_init_disk_target = diskutils.get_disk_target(
        [d.target for d in disks], prefix='vd'
    )
    cloud_init = CloudInit()
    if args.user_data:
        cloud_init.user_data = args.user_data.read()
    if args.vendor_data:
        cloud_init.vendor_data = args.vendor_data.read()
    if args.network_config:
        cloud_init.network_config = args.network_config.read()
    if args.meta_data:
        cloud_init.meta_data = args.meta_data.read()
    for disk in disks:
        if disk.source.endswith('cloud-init.img'):
            cloud_init_disk_path = disk.source
            break
    if cloud_init_disk_path is None:
        volumes = session.get_storage_pool(session.VOLUMES_POOL)
        cloud_init_disk_path = volumes.path.joinpath(
            f'{instance.name}-cloud-init.img'
        )
        cloud_init.create_disk(cloud_init_disk_path)
        volumes.refresh()
        cloud_init.attach_disk(
            cloud_init_disk_path,
            cloud_init_disk_target,
            instance,
        )
    else:
        cloud_init.update_disk(cloud_init_disk_path)


def delete(session: Session, args: argparse.Namespace) -> None:
    """Delete instance with local storage volumes."""
    if args.yes is True or confirm(
        'this action is irreversible, continue?',
        default=False,
    ):
        instance = session.get_instance(args.instance)
        if args.save_volumes is False:
            instance.delete(with_volumes=True)
        else:
            instance.delete()
    else:
        print('aborted')
