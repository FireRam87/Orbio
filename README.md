# Orbio

A privacy-first Linux browser that breaks the rectangular UI paradigm.

## Features

- **Radial Tab Ring** — tabs arranged in a circular arc, not a flat bar
- **Arc Navigation** — curved URL bar and spatial controls
- **Built-in Privacy** — ad/tracker blocking with no extensions needed (EasyList + EasyPrivacy)
- **Fire Button** — burn your browsing data instantly with particle animation
- **Privacy Dashboard** — real-time stats on blocked trackers and domains
- **Theme Engine** — JSON-based themes with glow effects and accent colors
- **DuckDuckGo Default** — private search out of the box

## Screenshots

*Coming soon — the UI is radial, not rectangular.*

## Install

### From source (recommended for now)

```bash
# Dependencies (Ubuntu/Kubuntu/Debian)
sudo apt install python3-pyqt6 python3-pyqt6.qtwebengine

# Clone and run
git clone https://github.com/FireRam87/Orbio.git
cd Orbio
python3 -m orbio
```

### .deb package

```bash
cd scripts
bash build-deb.sh
sudo dpkg -i orbio_0.1.0_amd64.deb
orbio
```

### AppImage

```bash
cd scripts
bash build-appimage.sh
./Orbio-0.1.0-x86_64.AppImage
```

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+T` | New tab |
| `Ctrl+W` | Close tab |
| `Ctrl+L` | Focus URL bar |
| `Ctrl+R` / `F5` | Reload |
| `Alt+Left` / `Alt+Right` | Back / Forward |
| `Ctrl+Tab` | Next tab |
| `Ctrl+Shift+Tab` | Previous tab |
| `Ctrl+Shift+R` | Toggle radial/linear tabs |
| `Ctrl+Shift+P` | Privacy dashboard |

## Themes

Orbio ships with three built-in themes:
- **Orbio Blue** — the signature look (default)
- **Midnight Purple** — deep purple with violet glow
- **Emerald Night** — forest green with teal accents

Create custom themes by placing `.json` files in `~/.local/share/orbio/themes/`.

## Architecture

```
orbio/
  main.py              # Entry point
  app.py               # QApplication setup
  browser_window.py    # Main window coordinator
  webview.py           # QWebEngineView wrapper
  ui/
    radial_tabs.py     # Circular tab ring
    tab_bar.py         # Linear tab bar (alt mode)
    arc_navbar.py      # Curved navigation bar
    fire_button.py     # Fire button + animation
    privacy_dash.py    # Privacy stats overlay
  engine/
    privacy.py         # Request interception + blocking
    filters.py         # EasyList/ABP format parser
    cookies.py         # Cookie management
  themes/
    engine.py          # Theme loading + application
    default.json       # Orbio Blue
    midnight.json      # Midnight Purple
    emerald.json       # Emerald Night
```

## Requirements

- Python 3.12+
- PyQt6 with Qt WebEngine
- Linux (primary target)

## License

GPLv3 — free software, forever.
