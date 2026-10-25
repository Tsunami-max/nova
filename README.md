# NovaOS 2.0

NovaOS is a desktop operating system for Apple-silicon Macs (running in
**UTM**) built on **Ubuntu 24.04 LTS** and **KDE Plasma 5.27**, styled with its
own look: NovaOS logo, boot and login splash, Start button, a Windows 11-style centred taskbar,
NovaOS Dark colours with a violet accent, boot splash and installer.

You do **not** install anything on your Mac except UTM. macOS is not changed.

---

## 1. Download

Latest build: **Releases** page of this repository → `NovaOS-arm64.iso`
(plus a `.sha256` checksum). Builds are made automatically by GitHub Actions
on every change.

## 2. Create the virtual machine in UTM

1. Install **UTM** from <https://mac.getutm.app>.
2. **+** → **Virtualize** (not Emulate) → **Linux**. Leave *Use Apple
   Virtualization* **off**.
3. **Browse…** → `NovaOS-arm64.iso` → **Continue**.
4. Memory **4096 MB** or more (8192 is better), CPU cores **4** or more.
   **Tick "Hardware OpenGL Acceleration".** → **Continue**.
5. Storage **40 GB** → **Continue** → **Continue** → **Save** → **▶**.
6. On the desktop double-click **Install NovaOS** and follow the steps
   (*Erase disk* only erases the virtual disk). When it is done: shut down,
   VM settings → the USB/CD drive → **Clear**, then start again.

### Graphics acceleration (the most important setting)

NovaOS is smooth at 2K/4K, with window animations and fast web pages, only
when UTM passes your Mac's graphics chip to it. Check: **Start → System Info
→ Graphics** (the OpenGL renderer must be *virgl*, not *llvmpipe*). NovaOS
also shows a message after login when acceleration is missing.

To turn it on for an existing VM: shut NovaOS down → select the VM → **Edit**
(sliders icon) → **Display** → *Emulated Display Card*:
**virtio-gpu-gl-pci (GPU Supported)** → **Save**.

Without acceleration NovaOS turns window effects off automatically so it
stays usable, but large screens and video will be slower.

### Full screen that fills the whole screen (2K / 4K)

NovaOS resizes itself to the UTM window, so full screen covers the whole
screen with no black borders. In UTM: shut NovaOS down → **Edit** →
**Display** → tick **Resize display to window size automatically** (and
**Retina Mode** if you want the sharpest picture) → **Save**. Then use UTM's
full-screen button.

At every login NovaOS picks a matching size for text and buttons: 100 % up
to 2400 pixels wide, 125 % up to 3000, 200 % above (Retina / 4K). Choose your
own in **Settings → Display and Monitor → Scale**; NovaOS then keeps yours.
Retina Mode doubles the pixels, so only use it with graphics acceleration on.

---

## 3. What's inside

| You want | NovaOS app |
|---|---|
| Browse the web | **Firefox** (Mozilla's official build), with video codecs. Chromium and others are in the App Store |
| Install apps & games | **App Store** (Nova Store, NovaOS's own) — thousands of Flathub apps and games for your processor, one click to install, open, update or remove |
| Word / PowerPoint / Excel | **Writer**, **Impress**, **Calc** (LibreOffice; open and save .docx, .pptx, .xlsx) |
| Paint | **Paint** (KolourPaint) |
| Files | **Files** (Dolphin) |
| Photos, PDF, video | **Photos** (Gwenview), Okular, **Video Player** (VLC) |
| Games | Solitaire (KPatience), Minesweeper, Blocks, Mahjong — more in the App Store |
| Notes, calculator, text | Notes (NovaOS), Calculator, Text Editor |
| Specs | **System Info** (processor, memory, graphics, OpenGL renderer) and **Task Manager** |
| Everything else | **Settings** — themes, accent colour, wallpapers, taskbar, display, keyboard, … |

### Customising

**NovaOS Style** (opens on the first login, and in the Start menu) has pages
for *Look*, *Wallpaper* (incl. slideshow), *Taskbar* (position, size, auto-hide,
floating, see-through, clock format/seconds/date), *Windows & effects* (button
side and size, borders, title position, open/close and minimise animations,
wobbly windows, transparency, blur strength, hot corner, night light), *Text &
pointer* (font, text size, pointer style and size, single/double click, mouse
speed), *Start-up & updates* and *Backup*. Four layouts — *NovaOS* (centred taskbar, Windows 11
style), *NovaOS Light*, *NovaOS Mac* (top menu bar + dock) and *NovaOS
Classic* (Windows 10 style) — plus dark/light, 11 accent colours, wallpapers,
taskbar position and size, window buttons left/right, animation speed and
icon style. Kvantum is included for extra app styles, and Settings →
Appearance can download thousands of themes, icons and widgets.

* **Live wallpaper:** NovaOS Style → *Wallpaper* → *Live wallpaper*: Aurora,
  Nebula (with shooting stars), Waves, Lava lamp, Colour flow, or your own
  picture with an effect on top — snow, rain, fireflies, twinkling stars or
  light rays (plus an optional slow zoom). It never uses more than 15 % of
  the processor (adjustable 10–20 %): when drawing costs more, it shows fewer
  frames, and it pauses while a window fills the screen.
* **Wallpaper:** right-click the desktop → *Configure Desktop and Wallpaper*.
  30+ professional KDE wallpapers are included, plus *Picture of the Day*
  (Bing, NASA, Unsplash…) for a new one every day.
* **Taskbar:** right-click it → *Enter Edit Mode*: move it to any edge, change
  its height, add widgets, drag apps on/off. Pin any app by right-clicking it
  in the Start menu → *Pin to Task Manager*.
* **Colours:** Settings → Appearance → Colours (NovaOS Dark / NovaOS Light /
  any accent colour). Global themes, icons, fonts, animations speed, window
  buttons — all in Settings.
* **Uninstall:** App Store → *Installed* → *Remove* (works for the browser
  too; reinstall it from the App Store).

### Updating to a new NovaOS (no reinstall, no new login)

Install NovaOS once. After that, new versions come to you: **Start → NovaOS
Update** (or NovaOS Style → *Start-up & updates* → *Update NovaOS now*).
It downloads the newest NovaOS and installs it on top of the one you have —
your files, apps, settings, Firefox bookmarks and website logins all stay.
NovaOS also tells you after login when a new version is out.

The installed NovaOS logs you in automatically (no password at start-up).
**Logging out** is one click: the ⏻ / log-out buttons next to the clock (also
Ctrl+Alt+Del or Start → Leave). Logging back in needs no password either —
just press Enter on the login screen. All of this can be switched in NovaOS
Style → *Start-up & updates*.

Already have an older NovaOS installed (without NovaOS Update)? Open
**Terminal** once and paste:

```
curl -fsSL https://raw.githubusercontent.com/Tsunami-max/nova/main/rootfs/usr/lib/novaos/update.sh | sudo bash
```

Moving to a fresh install anyway? NovaOS Style → *Backup* → *Save my setup*
saves your whole look, settings and (optionally) Firefox logins to one file;
*Restore a setup* on the new NovaOS puts it all back.

### Keyboard (Mac keyboard in UTM)

| Keys | Action |
|---|---|
| ⌘ (Super) | Start menu / search |
| ⌘ + E | Files |
| Ctrl + Alt + T | Terminal |
| ⌘ + D | Show desktop |
| Print / Shift+⌘+4 in macOS | Screenshot (Spectacle) |

---

## 4. Troubleshooting

| Problem | Fix |
|---|---|
| Everything is slow | Turn on graphics acceleration (section 2). Give the VM 4+ cores, 8 GB. Run the installed system, not the live CD. |
| Only some websites load (YouTube works, others hang) | NovaOS 2.0 already works around this (smaller packet size, TCP MTU probing). If it still happens: UTM VM settings → **Network** → *Network Mode* **Shared Network**, *Emulated Network Card* **virtio-net-pci**; turn off any VPN on the Mac and try again. |
| Websites "can't be reached" | Same network settings as above. DNS uses systemd-resolved with public fallback servers. |
| Netflix / Spotify / Disney+ refuse to play | These need Google's Widevine copy protection, which Google does not publish for ARM Linux, so no Linux browser on an ARM VM can play them. Use macOS for those services. |
| Text too small / too big | Settings → Display and Monitor → Scale. |
| Keyboard types wrong characters | Settings → Input Devices → Keyboard → Layouts (e.g. Belgian). |
| Boots the installer again after installing | VM settings → USB/CD drive → **Clear**. |

---

## 5. Build it yourself

The ISO is built by `.github/workflows/build-iso.yml` on GitHub's ARM runner
(push to `main`, or Actions → *Build NovaOS ISO* → *Run workflow*). Locally,
on an Ubuntu 24.04 machine of the target architecture:

```
sudo ./build.sh            # full build → out/NovaOS-arm64.iso or out/NovaOS.iso
```

```
build.sh                     debootstrap + packages + customise + squashfs + GRUB ISO
scripts/chroot-customize.sh  runs inside the image: branding, colours, App Store, services
scripts/run-selftest*.sh     QEMU test harness (boots the ISO and opens every app)
rootfs/                      files copied into the OS
  usr/share/plasma/look-and-feel/org.novaos.desktop   NovaOS desktop layout & defaults
  usr/lib/novaos/            Notes app, GPU check, pre-session setup, self-test
  etc/xdg/                   KDE defaults (fonts, KWin, power, lock screen)
  etc/calamares/             installer configuration and branding
boot/grub/                   live-ISO boot menu and theme
artwork/                     generators for the logo, icons and boot artwork
```

## 6. Licences

NovaOS's own code is MIT, its artwork CC BY-SA 4.0. Every bundled package
keeps its own licence: see `licenses/LICENSES.md`, and inside NovaOS
`/usr/share/doc/novaos/` and `/usr/share/doc/<package>/copyright`. NovaOS is
not affiliated with Canonical or KDE e.V.
