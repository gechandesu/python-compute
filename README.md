# Node Agent

Агент для работы на ворк-нодах.

# Как это должно выглядеть

`node-agent` должен стать обычным DEB-пакетом. Вместе с самим приложением пойдут вспомагательные утилиты:

- `na-vmctl` virsh на минималках, который дёргает код из Node Agent. Выполняет базовые операции с VM, установку и миграцию и т.п. Реализована частично.
- `na-vmexec`. Обёртка для вызова QEMU guest agent на машинах, больше нчего уметь не должна. Реализована целиком.
- `na-volctl`. Предполагается здесь оставить всю работу с дисками. Не реализована.

Этими утилитами нет цели заменять virsh, бцдет реализован только специфичный для Node Agent функционал.

Зависимости (версии из APT репозитория Debian 12):

- `python3-lxml` 4.9.2
- `python3-docopt` 0.6.2
- `python3-libvirt` 9.0.0 (актуальная новее)

Минимальная поддерживаемая версия Python — `3.11`, потому, что можем.

# Классы

Весь пакет разбит на модули, а основной функционал на классы.

## `ConfigLoader`

Наследуется от `UserDict`. Принимает в конструктор путь до файла, после чего экземпляром `ConfigLoader` можно пользоваться как обычным словарём. Вызывается внутри `LibvirtSession` при инициализации.

## `LibvirtSession`

Устанавливает сессию с libvirtd и создаёт объект virConnect. Класс умеет принимать в конструктор один аргумент — путь до файла конфигурации, но его можно опустить.

```python
from node_agent import LibvirtSession

session = LibvirtSession()
session.close()
```

Также этот класс является контекстным менеджером и его можно использвоать так:

```python
from node_agent import LibvirtSession, VirtualMachine

with LibvirtSession() as session:
    vm = VirtualMachine(session, 'имя_вм')
    vm.status
```

## `VirtualMachine`

Класс для базового управления виртуалкой. В конструктор принимает объект LibvirtSession и создаёт объект `virDomain`.

## `QemuAgent`

Класс для работы с агентом на гостях. Инициализируется аналогично `VirtualMachine`. Его можно считать законченным. Он умеет:

- Выполнять шелл команды через метод `shellexec()`.
- Выполнять любые команды QEMU через `execute()`.

Также способен:

- Поллить выполнение команды. То есть можно дождаться вывода долгой команды.
- Декодировать base64 вывод STDERR и STDOUT если надо.
- Отправлять данные на STDIN.

## `XMLConstructor`

Класс для генерации XML конфигов для либвирта и редактирования XML. Пока умеет очень мало и требует перепиливания. Возможно стоит разбить его на несколько классов. Пример работы с ним:

```python
from node_agent.xml import XMLConstructor

domain_xml = XMLConstructor()
domain_xml.gen_domain_xml(
    name='13',
    title='',
    vcpus=2,
    cpu_vendor='Intel',
    cpu_model='Broadwell',
    memory=2048,
    volume='/srv/vm-volumes/ef0bcd68-02c2-4f31-ae96-14d2bda5a97b.qcow2',
)
tags_meta = {
    'name': 'tags',
    'children': [
        {'name': 'god_mode'},
        {'name': 'service'}
    ]
}
domain_xml.add_meta(tags_meta, namespace='http://half-it-stack.org/xmlns/tags-meta', nsprefix='tags')
print(domain_xml.to_string())
```

В итоге должен получиться какой-то конфиг для ВМ.

Имеет метод `construct_xml()`, который позволяет привести словарь Python в XML элемент (обхект `lxml.etree.Element`). Пример:

```python
>>> from lxml.etree import tostring
>>> from na.xml import XMLConstructor
>>> xml = XMLConstructor()
>>> tag = {
...     'name': 'mytag',
...     'values': {
...             'firstname': 'John',
...             'lastname': 'Doe'
...     },
...     'text': 'Hello!',
...     'children': [{'name': 'okay'}]
... }
>>> element = xml.construct_xml(tag)
>>> print(tostring(element).decode())
'<mytag firstname="John" lastname="Doe">Hello!<okay/></mytag>'
>>>
```

Функция рекурсивная, так что теоретически можно положить бесконечное число вложенных элементов в `children`. С аргументами `namespace` и `nsprefix` будет сгенерирован XML с неймспейсом, Ваш кэп.

# TODO

- [ ] Установка ВМ
    - [x] Конструктор XML (базовый)
- [ ] Управление дисками
- [ ] Удаление ВМ
- [ ] Изменение CPU
- [ ] Изменение RAM
- [ ] Миграция ВМ между нодами
- [x] Работа с qemu-ga
- [x] Управление питанием
- [ ] Вкл/выкл автостарт ВМ
- [ ] Статистика потребления ресурсов
- [ ] Получение инфомрации из/о ВМ
- [ ] SSH-ключи
- [ ] Сеть
- [ ] ???

# Заметки

xml.py наверное лучше реализовать через lxml.objectify: https://stackoverflow.com/questions/47304314/adding-child-element-to-xml-in-python

???: https://www.geeksforgeeks.org/reading-and-writing-xml-files-in-python/

Минимальный рабочий XML: https://access.redhat.com/documentation/ru-ru/red_hat_enterprise_linux/6/html/virtualization_administration_guide/section-libvirt-dom-xml-example
