#!/usr/bin/env bash
# Boot the NovaOS ISO in QEMU for testing (software emulation, like UTM "Emulate").
#   scripts/test-vm.sh [uefi|bios] [path/to/NovaOS.iso] [disk.qcow2]
# Control the VM with scripts/vmctl.py <run-dir>/qmp.sock ...
set -euo pipefail
MODE="${1:-uefi}"
ISO="${2:-$(dirname "$0")/../out/NovaOS.iso}"
DISK="${3:-}"
RUN="${RUN:-/tmp/novaos-vm}"
mkdir -p "$RUN"
rm -f "$RUN/qmp.sock"

FW=()
if [ "$MODE" = uefi ]; then
	cp /usr/share/OVMF/OVMF_VARS_4M.fd "$RUN/vars.fd"
	FW=(-drive if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.fd
	    -drive if=pflash,format=raw,file="$RUN/vars.fd")
fi
DISKARGS=()
[ -n "$DISK" ] && DISKARGS=(-drive file="$DISK",if=virtio,format=qcow2)

exec qemu-system-x86_64 -machine q35 -accel tcg,thread=multi -cpu max -smp 2 -m 4096 \
	"${FW[@]}" "${DISKARGS[@]}" \
	-cdrom "$ISO" -boot order=cd,menu=off \
	-device virtio-vga -display none \
	-device qemu-xhci -device usb-tablet -device usb-kbd \
	-device intel-hda -audiodev none,id=snd0 -device hda-duplex,audiodev=snd0 \
	-netdev user,id=n0 -device virtio-net-pci,netdev=n0 \
	-qmp unix:"$RUN/qmp.sock",server,nowait \
	-serial file:"$RUN/serial.log" \
	${REBOOT_FLAG--no-reboot} ${QEMU_EXTRA:-}
