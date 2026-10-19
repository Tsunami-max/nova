#!/bin/sh
# Prints "yes" when this machine has hardware-accelerated OpenGL (for example
# UTM with "Hardware OpenGL Acceleration" / virtio-gpu-gl), otherwise "no".
# The answer is cached for the session because it never changes while running.
CACHE="${XDG_RUNTIME_DIR:-/tmp}/novaos-gl"
if [ -s "$CACHE" ]; then cat "$CACHE"; exit 0; fi
R="$(timeout 8 glxinfo -B 2>/dev/null | sed -n 's/.*OpenGL renderer string: *//p' | head -1)"
case "$R" in
	""|*llvmpipe*|*softpipe*|*swrast*|*"Software Rasterizer"*) A=no ;;
	*) A=yes ;;
esac
echo "$A" > "$CACHE" 2>/dev/null
printf '%s\n' "$R" > "${CACHE}-renderer" 2>/dev/null
echo "$A"
