# NovaOS — licences and notices

NovaOS is a customised distribution built from Ubuntu 24.04 LTS packages.
Every package keeps its own licence. The full copyright text for each
installed package is in `/usr/share/doc/<package>/copyright`, and a table of
all packages with their declared licences is in
`/usr/share/doc/novaos/package-licenses.tsv`.

NovaOS is an independent project. It is not affiliated with or endorsed by
Canonical; "Ubuntu" is a trademark of Canonical Ltd.

## Original NovaOS components

| Component | Licence |
|---|---|
| NovaOS Settings, Notes, session/theme scripts (`/usr/lib/novaos`) | MIT |
| Build scripts (`build.sh`, `scripts/`, `artwork/*.py`) | MIT |
| NovaOS logo, icons (`/usr/share/icons/NovaOS*`), wallpapers, GRUB/Plymouth artwork | CC BY-SA 4.0 |
| NovaOS-Dark / NovaOS-Light GTK themes | GPL-2.0 (derived from Materia) |

## Main bundled applications

| App in NovaOS | Upstream project | Licence |
|---|---|---|
| Desktop shell (panel, window manager, desktop, session) | XFCE 4.18 | GPL-2.0+ / LGPL-2.0+ |
| Files | Thunar | GPL-2.0+ |
| Web Browser | GNOME Web (Epiphany), WebKitGTK | GPL-3.0+ / LGPL-2.1+, BSD |
| Calculator | GNOME Calculator | GPL-3.0+ |
| Terminal | xfce4-terminal | GPL-2.0+ |
| Image Viewer | Ristretto | GPL-2.0+ |
| Text Editor | Mousepad | GPL-2.0+ |
| App Launcher | xfce4-appfinder | GPL-2.0+ |
| Task Manager | xfce4-taskmanager | GPL-2.0+ |
| Volume Mixer | PulseAudio Volume Control (pavucontrol) | GPL-2.0+ |
| Installer | Calamares | GPL-3.0+ |
| Compositor (effects) | picom | MPL-2.0 / MIT |
| Login screen | LightDM, lightdm-gtk-greeter | GPL-3.0+ |
| Boot splash | Plymouth | GPL-2.0+ |
| Boot loader | GNU GRUB 2 | GPL-3.0+ |
| Kernel | Linux 6.8 (Ubuntu) | GPL-2.0 |
| Base GTK theme | Materia | GPL-2.0 |
| Fallback icons | Papirus | GPL-3.0 |
| Fonts | Inter, JetBrains Mono (SIL OFL 1.1); Noto, DejaVu | OFL-1.1 / Bitstream Vera licence |

Source code for all Ubuntu packages is available from the Ubuntu archive
(`apt-get source <package>`), as required by the GPL.
