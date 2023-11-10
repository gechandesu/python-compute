_cmp_get_domains()
{
    for file in /etc/libvirt/qemu/*.xml; do
        nodir="${file##*/}"
        printf '%s\n' "${nodir//\.xml}"
    done
}

_compute()
{
    :
}

complete -o filenames -F _compute compute
