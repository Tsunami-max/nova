#!/usr/bin/env bash
# Boot the ISO in QEMU with the self-test hook enabled and collect results.
#   scripts/run-selftest.sh [halt|reboot|none] [cpu-model]
# Screenshots + serial log land in $RUN (default /tmp/novaos-selftest).
set -uo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
ACTION="${1:-halt}"
CPU="${2:-max}"
RUN="${RUN:-/tmp/novaos-selftest}"
ISO="$HERE/out/NovaOS.iso"
rm -rf "$RUN"; mkdir -p "$RUN"
xorriso -osirrox on -indev "$ISO" -extract /casper/vmlinuz "$RUN/vmlinuz" -extract /casper/initrd "$RUN/initrd" >/dev/null 2>&1
cp /usr/share/OVMF/OVMF_VARS_4M.fd "$RUN/vars.fd"
RBFLAG="-no-reboot"; [ -n "${REBOOT_LOOP:-}" ] && RBFLAG=""
SEL="novaos.selftest"; [ "$ACTION" != none ] && SEL="novaos.selftest=$ACTION"

qemu-system-x86_64 -machine q35 -accel tcg,thread=multi -cpu "$CPU" -smp 2 -m 4096 \
	-drive if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.fd \
	-drive if=pflash,format=raw,file="$RUN/vars.fd" \
	-cdrom "$ISO" -kernel "$RUN/vmlinuz" -initrd "$RUN/initrd" \
	-append "boot=casper quiet splash noprompt $SEL" \
	-device virtio-vga -display none \
	-device qemu-xhci -device usb-tablet -device usb-kbd \
	-device intel-hda -audiodev none,id=snd0 -device hda-duplex,audiodev=snd0 \
	-netdev user,id=n0 -device virtio-net-pci,netdev=n0 \
	-qmp unix:"$RUN/qmp.sock",server,nowait \
	-serial file:"$RUN/serial.log" $RBFLAG &
QPID=$!
start=$(date +%s)
seen=0
while kill -0 $QPID 2>/dev/null; do
	if [ -f "$RUN/serial.log" ]; then
		mapfile -t shots < <(grep -a "SELFTEST: SHOT" "$RUN/serial.log" | awk '{print $3}' | tr -d '\r')
		while [ $seen -lt ${#shots[@]} ]; do
			python3 "$HERE/scripts/vmctl.py" "$RUN/qmp.sock" shot "$RUN/${shots[$seen]}.png" 2>/dev/null
			seen=$((seen + 1))
		done
	fi
	if [ -n "${REBOOT_LOOP:-}" ] && [ "$(grep -ac "SELFTEST: BEGIN" "$RUN/serial.log" 2>/dev/null || echo 0)" -ge 2 ]; then
		echo "Second boot reached the desktop after restart"; sleep 5
		python3 "$HERE/scripts/vmctl.py" "$RUN/qmp.sock" shot "$RUN/after-restart.png"
		python3 "$HERE/scripts/vmctl.py" "$RUN/qmp.sock" quit 2>/dev/null; break
	fi
	if [ "$ACTION" = none ] && grep -aq "SELFTEST: END" "$RUN/serial.log" 2>/dev/null; then
		python3 "$HERE/scripts/vmctl.py" "$RUN/qmp.sock" quit 2>/dev/null; break
	fi
	now=$(date +%s)
	if [ $((now - start)) -gt 3000 ]; then echo "TIMEOUT"; kill $QPID; break; fi
	timeout 2 tail -f /dev/null 2>/dev/null
done
echo "QEMU exited after $(( $(date +%s) - start )) s"
grep -a "SELFTEST" "$RUN/serial.log" | sed 's/\r//'
