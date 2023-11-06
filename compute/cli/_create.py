import argparse

from compute import Session
from compute.utils import identifiers


def _create_instance(session: Session, args: argparse.Namespace) -> None:
    """
    Умолчания (достать информацию из либвирта):
    - arch
    - machine
    - emulator
    - CPU
        - cpu_vendor
        - cpu_model
        - фичи
    - max_memory
    - max_vcpus

    (сегнерировать):
    - MAC адрес
    - boot_order = ('cdrom', 'hd')
    - title = ''
    - name = uuid.uuid4().hex
    """
    print(args)
