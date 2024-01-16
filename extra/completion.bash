# compute bash completion script

_compute_global_opts="--connect --log-level"
_compute_root_cmd="
    $_compute_global_opts
    --version
    init
    exec
    ls
    lsdisks
    start
    shutdown
    reboot
    reset
    powrst
    pause
    resume
    status
    setvcpus
    setmem
    setpass
    setcdrom
    setcloudinit
    delete"
_compute_init_opts="$_compute_global_opts --test --start"
_compute_exec_opts="$_compute_global_opts
    --timeout
    --executable
    --env
    --no-join-args"
_compute_ls_opts="$_compute_global_opts"
_compute_lsdisks_opts="$_compute_global_opts --persistent"
_compute_start_opts="$_compute_global_opts"
_compute_shutdown_opts="$_compute_global_opts --soft --normal --hard --unsafe"
_compute_reboot_opts="$_compute_global_opts"
_compute_reset_opts="$_compute_global_opts"
_compute_powrst_opts="$_compute_global_opts"
_compute_pause_opts="$_compute_global_opts"
_compute_resume_opts="$_compute_global_opts"
_compute_status_opts="$_compute_global_opts"
_compute_setvcpus_opts="$_compute_global_opts"
_compute_setmem_opts="$_compute_global_opts"
_compute_setpass_opts="$_compute_global_opts --encrypted"
_compute_setcdrom_opts="$_compute_global_opts --detach"
_compute_setcloudinit_opts="$_compute_global_opts
    --user-data
    --vendor-data
    --meta-data
    --network-config"
_compute_delete_opts="$_compute_global_opts --yes --save-volumes"

_compute_complete_instances()
{
    local base_name
    for file in /etc/libvirt/qemu/*.xml; do
        base_name="${file##*/}"
        printf '%s ' "${base_name//\.xml}"
    done
}

_compute_compreply()
{
    local cgopts=

    if [[ "$1" == '-f' ]]; then
        cgopts="-f"
        shift
    fi

    if [[ "$current" = [a-z]* ]]; then
        _compute_compwords="$(_compute_complete_instances)"
    else
        _compute_compwords="$*"
    fi
    COMPREPLY=($(compgen $cgopts -W "$_compute_compwords" -- "$current"))
}

_compute_complete()
{
    local current previous nshift
    current="${COMP_WORDS[COMP_CWORD]}"
    case "$COMP_CWORD" in
        1)  COMPREPLY=($(compgen -W "$_compute_root_cmd" -- "$current"))
        ;;
        2|3|4|5)
            nshift=$((COMP_CWORD-1))
            previous="${COMP_WORDS[COMP_CWORD-nshift]}"
            case "$previous" in
                init) COMPREPLY=($(compgen -f -W "$_compute_init_opts" -- "$current"));;
                exec) _compute_compreply "$_compute_exec_opts";;
                ls) COMPREPLY=($(compgen -W "$_compute_ls_opts" -- "$current"));;
                lsdisks) _compute_compreply "$_compute_lsdisks_opts";;
                start) _compute_compreply "$_compute_start_opts";;
                shutdown) _compute_compreply "$_compute_shutdown_opts";;
                reboot) _compute_compreply "$_compute_reboot_opts";;
                reset) _compute_compreply "$_compute_reset_opts";;
                powrst) _compute_compreply "$_compute_powrst_opts";;
                pause) _compute_compreply "$_compute_pause_opts";;
                resume) _compute_compreply "$_compute_resume_opts";;
                status) _compute_compreply "$_compute_status_opts";;
                setvcpus) _compute_compreply "$_compute_setvcpus_opts";;
                setmem) _compute_compreply "$_compute_setmem_opts";;
                setpass) _compute_compreply "$_compute_setpass_opts";;
                setcdrom) _compute_compreply "$_compute_setcdrom_opts";;
                setcloudinit) _compute_compreply -f "$_compute_setcloudinit_opts";;
                delete) _compute_compreply "$_compute_delete_opts";;
                *) COMPREPLY=()
            esac
            ;;
        *)  COMPREPLY=($(compgen -W "$_compute_compwords" -- "$current"))
    esac
}

complete -F _compute_complete compute

# vim: ft=bash
