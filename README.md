# NovaOS 1.0

NovaOS is a desktop operating system built on **Ubuntu 24.04 LTS** with a
customised XFCE desktop. It has its own look (logo, icons, wallpapers, window
style, boot splash, login screen), its own Settings and Notes apps, and an
installer.

You do **not** need to install Linux or Ubuntu on your Mac. NovaOS runs inside
**UTM**, a free virtual-machine app. Your Mac and macOS are not changed.

---

## 1. What you get

| File | What it is |
|---|---|
| `NovaOS.iso` | The bootable operating system (x86_64 / "Intel 64-bit"), about 390 MB. This is the file you open in UTM. |
| `NovaOS.iso.sha256` | Checksum, to check the download isn't damaged. |
| `NovaOS-source.tar.gz` | All source files, scripts and artwork used to build the ISO. |
| `README.md` | This guide. |
| `licenses/LICENSES.md` | Licences of included software. |

### Architecture: why x86_64?

Your Mac has an Apple Silicon (ARM64) processor. The ISO I could build is
**x86_64** (also called x64, amd64 or Intel 64-bit), because my build machine
could not reach Ubuntu's ARM64 package servers.

UTM runs x86_64 systems on Apple Silicon by **emulation**. This works, but it
is noticeably slower than a native ARM64 system: expect a slow boot and
slightly sluggish windows. For a native, fast ARM64 version see
[section 7](#7-building-a-native-arm64-version).

---

## 2. Check the download (optional)

Open the **Terminal** app on your Mac (Applications → Utilities → Terminal),
paste this and press **Enter**:

```
shasum -a 256 ~/Downloads/NovaOS.iso
```

The code it prints must match the one in `NovaOS.iso.sha256`.

---

## 3a. Fast version for Apple-silicon Macs (NovaOS-arm64.iso)

`NovaOS-arm64.iso` runs natively on M1/M2/M3/M4 Macs, so it is much smoother
than the Intel version. In UTM:

1. **+** → **Virtualize** (not Emulate) → **Linux**.
2. Leave "Use Apple Virtualization" **off**. **Browse…** → pick `NovaOS-arm64.iso` → **Continue**.
3. Memory **4096 MB** or more, CPU cores **4** → **Continue**.
4. Storage 25 GB → **Continue** → **Continue** → **Save** → **▶**.

It includes Chromium (the open-source base of Google Chrome) as the web
browser, with video codecs for YouTube.

## 3. Run the Intel version in UTM (NovaOS.iso, step by step)

1. Install **UTM** from <https://mac.getutm.app> (or the Mac App Store) and open it.
2. Click **+** (Create a New Virtual Machine).
3. Choose **Emulate**. *(Not "Virtualize" — that only works for ARM64 systems.)*
4. Choose **Linux**.
5. Boot Image Type: **Boot from ISO image** → **Browse…** → select `NovaOS.iso` → **Continue**.
6. Hardware:
   - Architecture: **x86_64**
   - System: leave the default (**Standard PC (Q35 + ICH9)**)
   - Memory: **4096 MB** (more is better)
   - CPU cores: **4** if your Mac has 8 or more cores
   - **Continue**
7. Storage: **25 GB** (only needed if you want to install NovaOS; the space is
   used inside UTM, not taken from macOS until it fills) → **Continue**.
8. Shared Directory: skip → **Continue**.
9. Name it **NovaOS** → **Save**.
10. Press the big **▶ Play** button.

You'll see the NovaOS boot menu. Press **Enter** (or wait 8 seconds) on
**"Try or install NovaOS"**. Booting under emulation can take several minutes:
the purple NovaOS splash appears, then the desktop opens automatically
(no password needed in the live session).

**Display setting (if the screen stays black):** stop the VM, open its
settings (the sliders icon) → **Display** → set *Emulated Display Card* to
**virtio-vga** (or **VGA**), then start it again. You can also pick
**"NovaOS (safe graphics)"** in the boot menu.

---

## 4. Using NovaOS

### Live session vs installed

* **Live session** (what you get after booting the ISO): everything works, but
  changes are lost when you shut down.
* **Installed**: double-click **Install NovaOS** on the desktop. The installer
  asks for language, time zone, keyboard, disk ("Erase disk" is correct — it
  only erases the **virtual** UTM disk) and your user name/password. When it
  finishes, shut down, then in UTM **clear the ISO** from the CD/DVD drive
  (VM settings → the CD/DVD drive → **Clear**) and start the VM again.
  NovaOS now starts from its virtual disk, keeps your files and works fully offline.

### Size trade-offs

To fit in one download (under 400 MB) NovaOS 1.0 is tuned for virtual machines:

* translations only for English, French, German, Spanish, Italian, Dutch,
  Portuguese and Romanian; no man pages; everyday font weights only;
* fallback app icons (Papirus) in one SVG size, which scales sharply;
* no kernel drivers for Wi-Fi, Bluetooth, webcams/TV tuners, discrete
  AMD/NVIDIA/Intel GPUs or data-centre network/storage cards;
* a boot image (initramfs) with VM storage drivers only
  (`/etc/initramfs-tools/modules`; set `MODULES=most` in
  `/etc/initramfs-tools/conf.d/novaos.conf` to undo).

A kernel update with `sudo apt upgrade` brings the full driver set back.

### Built-in apps

| NovaOS app | Based on |
|---|---|
| Files | Thunar |
| Settings | NovaOS Settings (original) |
| Web Browser | GNOME Web (Epiphany) — needs the VM to have internet; opens an offline welcome page |
| Notes | Nova Notes (original) — notes are saved in `Documents/Notes` |
| Calculator | GNOME Calculator |
| Terminal | xfce4-terminal ("Nova Night" colours) |
| Image Viewer | Ristretto |
| Wallpapers | NovaOS Settings → Personalization |
| App Launcher | xfce4-appfinder (**Alt+F3**) |
| Also | Text Editor (Mousepad), Task Manager, Screenshot, Volume Mixer |

### Settings app

* **Personalization**: Dark / Light mode, 11 accent colours, 11 4K wallpapers (or your
  own picture), visual effects (Off / Balanced / Full), taskbar transparency, text size,
  window-button side (left like macOS / right like Windows) and desktop icon size.
* **Taskbar**: size, show app names, top or bottom of the screen.
* **Dock**: pick, reorder and remove the pinned apps; bottom / left / right; icon size;
  auto-hide.
* **Display**: resolution, refresh rate (defaults to the highest your screen offers) and
  scale 100–200 % for high-resolution (1440p / 4K / Retina) screens.
* **Apps**: uninstall apps (including the web browser) and install new ones
  (one-click VLC, GIMP, LibreOffice, Chromium, Thunderbird, or search everything).
* **Keyboard**: layout (e.g. Belgian, French, German, US…).
* **Date & time**, **Sound**, **Network**, **About NovaOS**.

### Keyboard shortcuts

| Keys | Action |
|---|---|
| Alt+F3 | Search and launch apps |
| Super+E | Files |
| Ctrl+Alt+T or Super+T | Terminal |
| Super+I | Settings |
| Super+N | Notes |
| Super+D | Show desktop |
| Print | Screenshot |
| Alt+F4 | Close window |

On a Mac keyboard, **Super** is the **⌘ Command** key inside UTM.

### Shut down / restart

Click your user name (top-right of the panel) → **Shut Down**, or
→ **Log Out…** to get the dialog with **Restart** and **Shut Down**.
Pressing **Alt+F4** on the empty desktop opens the same dialog.

### Customising the taskbar layout

NovaOS 1.0 ships with XFCE's standard panel layout. To arrange it Windows-style:

1. Right-click an empty part of the panel → **Panel** → **Panel Preferences…**
2. **Display** tab: Mode *Horizontal*, untick *Lock panel*, then drag the panel
   by its handle to the bottom edge (or set it there and re-lock). Set **Row size**
   to about 44.
3. **Items** tab: click **+** to add items such as **Whisker Menu** (a
   searchable Start menu), **Window Buttons**, **Clock**, **Notification Area**,
   **PulseAudio Plugin** and **Show Desktop**. Use the arrows to reorder them.
4. In the Whisker Menu's **Properties** you can set its icon to the NovaOS
   logo (icon name `novaos-start`).

The NovaOS theme already styles the panel, Whisker Menu, clock and window
buttons to match.

---

## 5. Troubleshooting

| Problem | Fix |
|---|---|
| Black screen after the boot menu | Wait — emulation is slow (up to ~5 min on first boot). If still black, use **"NovaOS (safe graphics)"** or change UTM Display to **virtio-vga**/**VGA**. |
| Very slow / laggy | Expected with x86_64 emulation. In Settings → Personalization set **Effects: Off**. Give the VM 4 cores and 4–8 GB RAM. For real speed build the ARM64 version (section 7). |
| Keyboard types wrong characters | Settings → **Keyboard** → choose your layout (e.g. *Belgian*). |
| Screen resolution too small | Settings → **Display** → choose a resolution → **Apply**. |
| No internet in the browser | In UTM VM settings → **Network** → mode **Shared Network**. |
| After installing, it boots the installer again | Remove the ISO: VM settings → CD/DVD → **Clear**. |
| UTM says "UEFI" errors | VM settings → **QEMU** → make sure **UEFI Boot** is ticked (BIOS boot also works). |
| Boot messages for debugging | Choose **"NovaOS (text boot messages)"** in the boot menu. |

---

## 6. Build it yourself

The ISO is fully reproducible from the files in `NovaOS-source.tar.gz`.

Requirements: an **Ubuntu 24.04** machine or VM (not your Mac directly), root
access, ~25 GB free disk, internet. The build machine's architecture decides
the ISO architecture.

```
tar xzf NovaOS-source.tar.gz
cd novaos
sudo ./build.sh            # full build, 30–90 minutes
# result: out/NovaOS.iso (x86_64) or out/NovaOS-arm64.iso (ARM64)
```

Stages can be run one by one: `bootstrap`, `packages`, `customize`, `image`, `clean`.

Project layout:

```
build.sh                    main build script (debootstrap + squashfs + GRUB ISO)
scripts/chroot-customize.sh runs inside the image: themes, branding, services, initramfs
scripts/test-vm.sh, vmctl.py QEMU test harness used for testing
rootfs/                     files copied into the OS (apps, configs, icons, wallpapers, themes)
  usr/lib/novaos/           NovaOS Settings, Notes, theme generator, session setup (Python/GTK3)
  etc/calamares/            installer configuration and branding
boot/grub/                  live-ISO boot menu and GRUB theme
artwork/                    generators for logo, icons, wallpapers and boot artwork
licenses/LICENSES.md        licence summary
.github/workflows/          GitHub Actions workflow (builds ARM64 or x86_64 ISOs)
```

To regenerate artwork: `python3 artwork/gen_icons.py rootfs`,
`python3 artwork/gen_wallpapers.py rootfs`, `python3 artwork/gen_boot.py`
(needs `python3-numpy python3-pil librsvg2-bin imagemagick grub-common fonts-inter`).

---

## 7. Building a native ARM64 version

A native ARM64 build runs at full speed in UTM using **Virtualize** instead of
Emulate. **This ARM64 build has not been tested** — I could not build or
boot it in my environment.

**Option A — GitHub (no Linux needed on your side):**

1. Create a free GitHub account and a new **public** repository.
2. Upload the contents of `NovaOS-source.tar.gz` (keep the `.github` folder).
3. Open the **Actions** tab → **Build NovaOS ISO** → **Run workflow** → arch **arm64**.
4. After ~1 hour, download the **NovaOS-arm64** artifact (a zip containing the ISO).
5. In UTM choose **Virtualize** → **Linux** → select the ISO.

**Option B — in a UTM VM:** create a UTM **Virtualize** VM with Ubuntu Server
24.04 for **ARM** (arm64), copy the source in, and run `sudo ./build.sh`.

---

## 8. Testing status

Testing was done on my build machine with **QEMU 8.2 in pure software
emulation (TCG, no KVM, no GPU)**, the same technology UTM uses for "Emulate".
I could **not** test inside UTM itself or on a Mac.

| Check | Result |
|---|---|
| ISO has BIOS + UEFI boot records (`xorriso -report_el_torito`) | ✅ |
| Final 390 MB ISO: live boot, 12/12 app test, shutdown, full install, installed system boots | ✅ re-tested after slimming |
| UEFI boot → NovaOS GRUB menu → boot splash → desktop (auto-login) | ✅ tested |
| BIOS (legacy) boot → GRUB menu → desktop | ✅ tested |
| Wallpapers, NovaOS icons, window theme, login screen load | ✅ screenshots checked |
| Settings: dark/light mode, accent colour, wallpaper switching | ✅ tested live |
| Automated app test: Files, Settings, Web Browser, Notes, Calculator, Terminal, Image Viewer, Text Editor, App Launcher, Task Manager, Volume Mixer, Installer | ✅ 12/12 opened a working window (CPU models `max` and `qemu64`) |
| Shut down from the session | ✅ VM powers off |
| Restart from the session | ✅ VM restarts and comes back to the desktop |
| Log out → login screen → log in again | ✅ |
| Full install with the installer on a 25 GB virtual disk (UEFI, erase disk) | ✅ completed in ~20 min |
| Installed system boots from disk, password login works, live packages removed | ✅ |
| Running inside UTM on Apple Silicon | ❌ not tested (no Mac available to me) |
| Native ARM64 build | ❌ not built or tested |

Bugs found during testing and fixed before delivery: Calculator and Web
Browser crashed under CPU emulation (software OpenGL) → NovaOS now uses
non-GL rendering in VMs; the installer's "Erase disk" layout had no root
partition → fixed; the live session waited for a key press on shutdown →
fixed; screen blanking in VMs → disabled.

The ISO contains a self-test hook used for this testing: it does nothing
unless the system is booted with the kernel option `novaos.selftest`
(see `scripts/run-selftest.sh`).

---

## 9. Licences

NovaOS original code (Settings, Notes, scripts) is MIT-licensed; original
artwork (logo, icons, wallpapers, boot themes) is CC BY-SA 4.0; the NovaOS GTK
themes are GPL-2.0 because they are derived from Materia. All bundled
software keeps its own licence — see `licenses/LICENSES.md`, and inside NovaOS
`/usr/share/doc/novaos/` and `/usr/share/doc/<package>/copyright`.
NovaOS is not affiliated with or endorsed by Canonical.
