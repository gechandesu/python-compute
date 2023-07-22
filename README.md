# Node Agent

Агент для работы на ворк-нодах.

# Как это должно выглядеть

`node-agent` должен стать обычным DEB-пакетом. Вместе с самим приложением пойдут вспомагательные утилиты:

- **na-vmctl** "Своя" версия virsh, которая дёргает код из Node Agent. Базовые операции с VM и также установка и миграция ВМ. Реализована частично.
- **na-vmexec**. Обёртка для вызова QEMU guest agent на машинах, больше нчего уметь не должна. Реализована целиком.
- **na-volctl**. Предполагается здесь оставить всю работу с дисками. Не реализовано.

Этими утилитами Нет цели заменять virsh, нужно реализовать только специфичные для Node Agent вещи.

Зависимости (версии из APT репозитория Debian 12):

- `python3-lxml` 4.9.2
- `python3-docopt` 0.6.2
- `python3-libvirt` 9.0.0 (актуальная новее)

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

Класс для базового управления виртуалкой. В конструктор принимает объект LibvirtSession, который в себе содержит объект virConnect и конфиг в виде словаря.

## `QemuAgent`

Класс для работы с агентом на гостях. Его можно считать законченным. Он умеет:

- Выполнять шелл команды через метод `shellexec()`.
- Выполнять команды через `execute()`.

Внутри также способен:

- Поллить выполнение команды. То есть можно дождаться вывода долгой команды.
- Декодирует base64 вывод STDERR и STDOUT если надо.
- Принимать STDIN

# TODO

- [ ] Установка ВМ
    - [ ] Конструктор XML
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
