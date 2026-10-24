# NovaOS: without 3D acceleration (e.g. UTM without "GPU Supported" display),
# make GTK4 apps draw with Cairo instead of a slow software OpenGL path.
if [ -n "$DISPLAY" ] && [ -x /usr/lib/novaos/gl-check.sh ] && \
   [ "$(/usr/lib/novaos/gl-check.sh 2>/dev/null)" = no ]; then
	export GSK_RENDERER=cairo
	export WEBKIT_DISABLE_COMPOSITING_MODE=1
fi

# Firefox: in UTM/QEMU the virtual tablet pointer sends events that Firefox's
# XInput2 code sometimes drops, so clicks do nothing. Use the classic input path.
export MOZ_USE_XINPUT2=0
