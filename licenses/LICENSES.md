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
| NovaOS Notes, session scripts (`/usr/lib/novaos`), desktop layout | MIT |
| Build scripts (`build.sh`, `scripts/`, `artwork/*.py`) | MIT |
| NovaOS logo, icons (`/usr/share/icons/NovaOS*`), wallpapers, GRUB/Plymouth artwork | CC BY-SA 4.0 |
| NovaOS Dark / Light colour schemes | GPL-2.0+ (derived from Breeze) |

## Main bundled applications

| App in NovaOS | Upstream project | Licence |
|---|---|---|
| Desktop (panel, window manager, settings) | KDE Plasma 5.27, KWin, Breeze | GPL-2.0+ / LGPL-2.1+ |
| Login screen | SDDM | GPL-2.0+ |
| App Store | KDE Discover, PackageKit, Flatpak | GPL-2.0+ / LGPL-2.1+ |
| Web Browser | Chromium (xtradeb build) | BSD-3-Clause and others |
| Writer, Impress, Calc | LibreOffice | MPL-2.0 |
| Paint | KolourPaint | BSD-2-Clause / LGPL |
| Files, Terminal, Photos, Text Editor, Calculator | Dolphin, Konsole, Gwenview, KWrite, KCalc | GPL-2.0+ |
| PDF viewer, archives, screenshots | Okular, Ark, Spectacle | GPL-2.0+ |
| Video Player | VLC | GPL-2.0+ |
| Games | KPatience, KMines, KBlocks, KMahjongg | GPL-2.0+ |
| Wallpapers | plasma-workspace-wallpapers | various free licences (see package copyright) |
| Installer | Calamares | GPL-3.0+ |
| Boot splash / boot loader / kernel | Plymouth / GRUB 2 / Linux 6.8 | GPL |
| Icons | Papirus | GPL-3.0 |
| Fonts | Inter, JetBrains Mono (OFL-1.1), Noto Color Emoji (OFL-1.1), DejaVu, Carlito/Caladea (OFL-1.1) | as listed |

Source code for all Ubuntu packages is available from the Ubuntu archive
(`apt-get source <package>`), as required by the GPL.
