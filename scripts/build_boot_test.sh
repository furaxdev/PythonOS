#!/usr/bin/env bash
# Build the initramfs (if needed) and boot it in QEMU against a real Linux
# kernel, headless, capturing the serial console to build/boot.log as proof
# that the kernel + PythonOS Python init actually ran.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
KERNEL="${KERNEL:-/boot/vmlinuz}"
INITRAMFS="$REPO_ROOT/build/initramfs.cpio.gz"
LOG="$REPO_ROOT/build/boot.log"

if [ ! -f "$INITRAMFS" ] || [ "${1:-}" = "--rebuild" ]; then
  bash "$REPO_ROOT/scripts/build_initramfs.sh"
fi

echo "==> Booting PythonOS in QEMU (kernel=$KERNEL)"
timeout 20 qemu-system-x86_64 \
  -kernel "$KERNEL" \
  -initrd "$INITRAMFS" \
  -append "console=ttyS0 panic=1 quiet" \
  -nographic \
  -no-reboot \
  -m 512M \
  -serial file:"$LOG" \
  -display none \
  || true

echo "==> Boot log:"
cat "$LOG" || true

if grep -q "PythonOS init starting" "$LOG"; then
  echo "==> SUCCESS: PythonOS Python init ran as PID 1 under a real Linux kernel."
  exit 0
else
  echo "==> FAILURE: PythonOS init did not report starting. See $LOG"
  exit 1
fi
