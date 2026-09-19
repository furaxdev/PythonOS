# Building PythonOS

## Requirements

Checked automatically by `python3 tools/pyos doctor`:

- Python >= 3.10
- `qemu-system-x86_64`
- `busybox`
- `cpio`, `rsync`
- A Linux kernel image at `/boot/vmlinuz` (e.g. `apt install linux-image-generic`)

On Debian/Ubuntu:

```bash
apt-get install -y qemu-system-x86 busybox-static cpio rsync linux-image-generic
```

## Steps

```bash
python3 -m pytest tests/unit -v      # run the unit test suite
scripts/build_initramfs.sh           # build build/initramfs.cpio.gz
scripts/build_boot_test.sh           # boot-test it in QEMU, verify PID 1
python3 tools/pyos doctor            # full environment + test summary
```

There is no ISO build yet (Phase 10, `PLANNED` — see ROADMAP.md); the
current boot path is `qemu -kernel ... -initrd ...` directly, which is
sufficient to prove the kernel-to-Python-init handoff but skips the
bootloader stage a real ISO needs.
