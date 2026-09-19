#!/usr/bin/env bash
# Build a minimal initramfs containing busybox + a real Python 3 interpreter,
# used to boot PythonOS's init (system/init/pyinit.py) as PID 1 under QEMU.
#
# This is NOT a simulation: the resulting cpio archive is unpacked by the
# real Linux kernel at boot and its /init script is exec'd as PID 1.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="$REPO_ROOT/build/initramfs-root"
OUT="$REPO_ROOT/build/initramfs.cpio.gz"
PYTHON_BIN="$(command -v python3.11 || command -v python3)"
PYTHON_VER="$("$PYTHON_BIN" -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")')"

echo "==> Using $PYTHON_BIN (python $PYTHON_VER)"

rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"/{bin,sbin,usr/bin,usr/lib,lib,lib64,dev,proc,sys,etc/pythonos/services,pythonos}

echo "==> Installing busybox"
cp /usr/bin/busybox "$BUILD_DIR/bin/busybox"
for applet in sh mount umount poweroff reboot switch_root mkdir ls cat echo sleep ps; do
  ln -sf busybox "$BUILD_DIR/bin/$applet"
done

echo "==> Installing Python interpreter and its shared library closure"
cp "$PYTHON_BIN" "$BUILD_DIR/usr/bin/python3"

copy_lib_closure() {
  local bin="$1"
  ldd "$bin" 2>/dev/null | awk '{print $3; print $1}' | grep '^/' | while read -r lib; do
    [ -f "$lib" ] || continue
    dest="$BUILD_DIR$lib"
    mkdir -p "$(dirname "$dest")"
    cp -n "$lib" "$dest" 2>/dev/null || true
  done || true
  # ld-linux loader itself
  loader=$(ldd "$bin" 2>/dev/null | grep -o '/lib64/ld-linux[^ ]*' | head -1) || true
  if [ -n "$loader" ]; then
    mkdir -p "$BUILD_DIR/lib64"
    cp -n "$loader" "$BUILD_DIR/lib64/" 2>/dev/null || true
  fi
  return 0
}
copy_lib_closure "$PYTHON_BIN"
copy_lib_closure "$BUILD_DIR/bin/busybox"

echo "==> Copying Python standard library (trimmed)"
STDLIB_SRC="/usr/lib/python${PYTHON_VER}"
STDLIB_DST="$BUILD_DIR/usr/lib/python${PYTHON_VER}"
mkdir -p "$STDLIB_DST"
rsync -a --exclude 'test' --exclude 'tests' --exclude '__pycache__' \
  --exclude 'idlelib' --exclude 'tkinter' \
  "$STDLIB_SRC/" "$STDLIB_DST/"

DYNLOAD_SRC="/usr/lib/python3/dist-packages"
[ -d "$DYNLOAD_SRC" ] && rsync -a "$DYNLOAD_SRC/" "$BUILD_DIR/usr/lib/python3/dist-packages/" || true

echo "==> Copying PythonOS source tree"
rsync -a \
  --exclude '.git' --exclude 'build' --exclude 'dist' --exclude '__pycache__' \
  --exclude '.pytest_cache' --exclude 'tests' \
  "$REPO_ROOT"/system "$REPO_ROOT"/shell "$BUILD_DIR/pythonos/"

echo "==> Installing example service units"
cp "$REPO_ROOT"/system/services/examples/*.json "$BUILD_DIR/etc/pythonos/services/"

echo "==> Writing /init"
cat > "$BUILD_DIR/init" <<'EOF'
#!/bin/sh
mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t devtmpfs devtmpfs /dev 2>/dev/null || true

echo "[initramfs] Linux kernel is up. Handing off to PythonOS init (Python)."
export PYTHONHOME=/usr
export PYTHONPATH=/pythonos
exec /usr/bin/python3 /pythonos/system/init/pyinit.py /etc/pythonos/services
EOF
chmod +x "$BUILD_DIR/init"

echo "==> Packing cpio.gz"
( cd "$BUILD_DIR" && find . -print0 | cpio --null -ov --format=newc 2>/dev/null | gzip -9 > "$OUT" )

echo "==> Built $OUT ($(du -h "$OUT" | cut -f1))"
