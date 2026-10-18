#!/usr/bin/env bash
# Boot NovaOS-arm64.iso in QEMU (aarch64 "virt" machine, like UTM Virtualize)
# with the self-test hook, collecting screenshots and results.
#   scripts/run-selftest-arm64.sh path/to/NovaOS-arm64.iso [halt|none]
set -uo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
ISO="${1:?iso}"
ACTION="${2:-halt}"
RUN="${RUN:-/tmp/novaos-arm-selftest}"
rm -rf "$RUN"; mkdir -p "$RUN"
xorriso -osirrox on -indev "$ISO" -extract /casper/vmlinuz "$RUN/vmlinuz" -extract /casper/initrd "$RUN/initrd" >/dev/null 2>&1
truncate -s 64M "$RUN/code.fd" "$RUN/vars.fd"
dd if=/usr/share/AAVMF/AAVMF_CODE.no-secboot.fd of="$RUN/code.fd" conv=notrunc 2>/dev/null
SEL="novaos.selftest"; [ "$ACTION" != none ] && SEL="novaos.selftest=$ACTION"
qemu-system-aarch64 -machine virt -accel tcg,thread=multi -cpu max -smp 4 -m 4096 \
	-drive if=pflash,format=raw,readonly=on,file="$RUN/code.fd" \
	-drive if=pflash,format=raw,file="$RUN/vars.fd" \
	-device qemu-xhci -device usb-storage,drive=cd -drive id=cd,if=none,media=cdrom,file="$ISO" \
	-kernel "$RUN/vmlinuz" -initrd "$RUN/initrd" \
	-append "boot=casper quiet splash noprompt console=tty0 $SEL" \
	-device virtio-gpu-pci -display none \
	-device usb-tablet -device usb-kbd \
	-netdev user,id=n0 -device virtio-net-pci,netdev=n0 \
	-qmp unix:"$RUN/qmp.sock",server,nowait \
	-serial file:"$RUN/serial.log" -no-reboot &
QPID=$!
start=$(date +%s); seen=0
while kill -0 $QPID 2>/dev/null; do
	if [ -f "$RUN/serial.log" ]; then
		mapfile -t shots < <(grep -a "SELFTEST: SHOT" "$RUN/serial.log" | awk '{print $3}' | tr -d '\r')
		while [ $seen -lt ${#shots[@]} ]; do
			python3 "$HERE/scripts/vmctl.py" "$RUN/qmp.sock" shot "$RUN/${shots[$seen]}.png" 2>/dev/null
			seen=$((seen + 1))
		done
		if [ "$ACTION" = none ] && grep -aq "SELFTEST: END" "$RUN/serial.log"; then
			python3 "$HERE/scripts/vmctl.py" "$RUN/qmp.sock" quit 2>/dev/null; break
		fi
	fi
	if [ $(( $(date +%s) - start )) -gt 5400 ]; then echo TIMEOUT; kill $QPID; break; fi
	timeout 3 tail -f /dev/null 2>/dev/null
done
echo "QEMU exited after $(( $(date +%s) - start )) s"
grep -a "SELFTEST" "$RUN/serial.log" | sed 's/\r//'
