# NovaOS: in virtual machines without GPU acceleration (e.g. UTM emulation),
# avoid the software OpenGL path (llvmpipe), which can crash under CPU
# emulation. GTK4 apps draw with Cairo and WebKit renders without GL compositing.
if command -v systemd-detect-virt >/dev/null 2>&1 && systemd-detect-virt -q --vm; then
	export GSK_RENDERER=cairo
	export WEBKIT_DISABLE_COMPOSITING_MODE=1
	export WEBKIT_DISABLE_DMABUF_RENDERER=1
	export LP_NATIVE_VECTOR_WIDTH=128
fi
