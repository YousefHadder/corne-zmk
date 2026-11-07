# **Corne + Nice!Nano + Nice!View — ZMK Config** ✨

A complete ZMK configuration for the Corne keyboard with Nice!Nano v2 controllers and custom Nice!View displays featuring rotating artwork.

## 🎯 **Quick Overview**

- **Keyboard**: Corne (3×6 + 3 thumb keys, split layout — outer columns unused)
- **MCUs**: Nice!Nano v2 (wireless, split left/right halves)
- **Display**: Nice!View OLED with custom status screen and rotating artwork
- **ZMK Version**: Pinned to **v0.3.0** for stability
- **Features**: Custom keymap with tap-preferred hold-taps, bracket combos, automated image conversion, wireless connectivity, and ZMK Studio over USB

## 📋 **Table of Contents**

1. [Getting Started](#getting-started)
2. [Using This Repository](#using-this-repository)
   - [Fork and Use](#fork-and-use)
   - [Direct Usage](#direct-usage)
3. [Repository Structure](#repository-structure)
4. [Nice!View Artwork System](#niceview-artwork-system)
5. [Configuration](#configuration)
   - [Keymap Customization](#keymap-customization)
   - [Keymap Layout](#keymap-layout)
   - [Display Settings](#display-settings)
6. [Building Firmware](#building-firmware)
7. [Image Conversion Details](#image-conversion-details)
8. [Local Development](#local-development)
9. [Contributing](#contributing)

##  **Getting Started**

### Quick Start

1. **Fork this repository** to your GitHub account
2. **Enable GitHub Actions** in your forked repository
3. **Add your images** to the `assets/` folder
4. **Push changes** - GitHub Actions will automatically build firmware
5. **Download firmware** from the Actions tab
6. **Flash to your keyboards** using the instructions below

---

##  **Using This Repository**

### Fork and Use

**This is the recommended approach for most users:**

1. **Fork this repository** to your GitHub account:
   - Click the "Fork" button on GitHub
   - This creates your own copy where you can make changes

2. **Configure GitHub Actions** (required for automated builds):
   - Go to your forked repo → Settings → Actions → General
   - Enable "Read and write permissions" for GITHUB_TOKEN
   - Create a PAT with scope `Contents: Read and write` (fine‑grained) for the forked repo
   - Add it as a repository secret named `ACTIONS_PAT`

3. **Customize your configuration**:
   - Edit `config/corne.keymap` for your preferred key layout
   - Add your images to `assets/` folder for custom Nice!View artwork
   - Modify `config/corne.conf` for display and other settings

4. **Build firmware**:
   - Push your changes to trigger GitHub Actions
   - Download firmware files from the Actions tab
   - Flash to your keyboards

### Direct Usage

**For advanced users who want to use this config as-is:**

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/corne-zmk.git
   cd corne-zmk
   ```

2. **Build locally** (requires ZMK development environment):
   ```bash
   # Follow ZMK's local build instructions
   west build -p -b nice_nano_v2 -S studio-rpc-usb-uart -- -DSHIELD="corne_left nice_view_adapter nice_view" -DCONFIG_ZMK_STUDIO=y
   west build -p -b nice_nano_v2 -- -DSHIELD="corne_right nice_view_adapter nice_view_custom"
   ```

---

##  **Repository Structure**

```
corne-zmk/
├── config/                          # ZMK configuration files
│   ├── corne.keymap                 # Keymap layers, combos, and behaviors
│   ├── corne.conf                   # ZMK settings (enables custom status screen)
│   └── west.yml                     # ZMK upstream reference (pinned to v0.3.0)
├── boards/shields/nice_view_custom/ # Custom Nice!View shield
│   ├── widgets/                     # Custom widget implementations
│   │   ├── peripheral_status.c/.h   # Main status widget (art + status)
│   │   ├── status.c/.h             # Status display components
│   │   ├── bolt.c                  # Bluetooth/power indicators
│   │   ├── util.c/.h               # Utility functions
│   │   └── art.c                   # ⚠️ Auto-generated image data (don't edit)
│   ├── nice_view_custom.overlay     # Device tree overlay
│   ├── nice_view_custom.conf        # Shield configuration
│   └── CMakeLists.txt              # Build configuration
├── assets/                          # 🖼️ Your custom images for Nice!View
│   ├── itachi.jpeg                 # Example artwork
│   ├── me.png                      # Example artwork
│   └── palestine.webp              # Example artwork
├── scripts/
│   └── niceview_lvgl_convert.py    # Image → LVGL C array converter
├── .github/workflows/               # GitHub Actions automation
│   ├── update-images.yml           # Converts images and updates art.c
│   └── build.yml                   # Builds firmware
├── build.yaml                      # Build matrix for left/right halves
└── zephyr/module.yml               # Zephyr module descriptor
```

---

##  **Nice!View Artwork System**

This repository features an **automated artwork system** that converts your images into display-ready formats and rotates them on your Nice!View screens.

### How It Works

**Step 1: Add Images** 📁
- Place PNG/JPG/WEBP files into the `assets/` folder
- Use simple filenames (letters, numbers, underscores only)
- Example: `logo.png` becomes `LV_IMG_DECLARE(logo)` in code

**Step 2: Automated Conversion** 🤖
- GitHub Actions detects new images in `assets/`
- Runs `scripts/niceview_lvgl_convert.py` to:
  - Resize images to 68×140 pixels
  - Rotate 90° clockwise for proper display orientation  
  - Convert to 1-bit black/white with Floyd-Steinberg dithering
  - Generate LVGL C arrays in `art.c`
- Updates widget code to include new images in rotation
- Commits changes back to your repository

**Step 3: Firmware Build** 🏗️
- Build workflow triggers automatically after image conversion
- Compiles firmware for both keyboard halves:
  - **Left**: `nice_nano_v2` + `corne_left` + `nice_view`
  - **Right**: `nice_nano_v2` + `corne_right` + `nice_view_custom`
- Firmware files available in GitHub Actions artifacts

**Step 4: On-Device Display** 🖼️
- Images rotate automatically every **5 minutes**
- Display shows: battery level, connection status, and your artwork
- Works seamlessly with ZMK's power management

---

##  **Configuration**

### Keymap Customization

Edit `config/corne.keymap` to customize your keyboard layout:

- **Layers**: Define different key layouts (base, symbols, numbers, etc.)
- **Combos**: Set key combinations for special functions
- **Mod-tap**: Configure keys that act as modifiers when held, regular keys when tapped
- **Macros**: Create custom key sequences

**Current Layout Features:**
- Top-row home row modifiers (Alt, Shift, Ctrl, GUI) using tap-preferred hold-taps (`mt_repeat`)
- 5 layers: base typing, media/navigation, numbers, symbols/Bluetooth, right-hand modifiers
- Caps Lock combo (both inner thumb keys)
- Bracket/paren combos (adjacent key pairs)
- Custom shortcuts for window management (Rectangle)

## 🗝️ **Keymap Layout**

> **Note:** The Corne's outer columns and outer thumb keys are set to `&none` — the effective layout is 34 keys (5 columns + 2 thumbs per hand), matching a Ferris Sweep.

### Layer 0: Base (QWERTY with home row mods on top row)

```text
┌─────┬─────┬─────┬─────┬─────┬─────┐       ┌─────┬─────┬─────┬─────┬─────┬─────┐
│     │Q/Alt│W/Sft│E/Ctl│R/Gui│  T  │       │  Y  │U/Gui│I/Ctl│O/Sft│P/Alt│     │
├─────┼─────┼─────┼─────┼─────┼─────┤       ├─────┼─────┼─────┼─────┼─────┼─────┤
│     │  A  │  S  │  D  │  F  │  G  │       │  H  │  J  │  K  │  L  │;/L4 │     │
├─────┼─────┼─────┼─────┼─────┼─────┤       ├─────┼─────┼─────┼─────┼─────┼─────┤
│     │Z/L1 │  X  │  C  │  V  │  B  │       │  N  │  M  │  ,  │  .  │  /  │     │
└─────┴─────┴─────┼─────┼─────┼─────┤       ├─────┼─────┼─────┼─────┴─────┴─────┘
                  │     │Bs/L2│Esc/H│       │ Ent │Sp/L3│     │
                  └─────┴─────┴─────┘       └─────┴─────┴─────┘
```

### Layer 1: Media/Navigation (accessed via Z hold)

```text
┌─────┬─────┬─────┬─────┬─────┬─────┐       ┌─────┬─────┬─────┬─────┬─────┬─────┐
│     │Bri- │Bri+ │Prev │Play │Next │       │Vol- │Mute │Vol+ │     │  \  │     │
├─────┼─────┼─────┼─────┼─────┼─────┤       ├─────┼─────┼─────┼─────┼─────┼─────┤
│     │     │     │     │RectF│     │       │  ←  │  ↓  │  ↑  │  →  │  '  │     │
├─────┼─────┼─────┼─────┼─────┼─────┤       ├─────┼─────┼─────┼─────┼─────┼─────┤
│     │█████│Shift│RectC│  ▽  │  ▽  │       │RctLH│RctBH│RctTH│RctRH│  `  │     │
└─────┴─────┴─────┼─────┼─────┼─────┤       ├─────┼─────┼─────┼─────┴─────┴─────┘
                  │     │  ▽  │Space│       │RctEN│RctMV│     │
                  └─────┴─────┴─────┘       └─────┴─────┴─────┘
```

### Layer 2: Numbers (accessed via Backspace hold)

```text
┌─────┬─────┬─────┬─────┬─────┬─────┐       ┌─────┬─────┬─────┬─────┬─────┬─────┐
│     │  1  │2/Sft│3/Ctl│4/Gui│  5  │       │  6  │7/Gui│8/Ctl│9/Sft│  0  │     │
├─────┼─────┼─────┼─────┼─────┼─────┤       ├─────┼─────┼─────┼─────┼─────┼─────┤
│     │  =  │  -  │  '  │Cmd+B│  ▽  │       │     │     │     │     │     │     │
├─────┼─────┼─────┼─────┼─────┼─────┤       ├─────┼─────┼─────┼─────┼─────┼─────┤
│     │ MO1 │  ▽  │  ▽  │  ▽  │  ▽  │       │     │     │  ,  │  .  │     │     │
└─────┴─────┴─────┼─────┼─────┼─────┤       ├─────┼─────┼─────┼─────┴─────┴─────┘
                  │     │█████│Space│       │ Ent │RAlt │     │
                  └─────┴─────┴─────┘       └─────┴─────┴─────┘
```

### Layer 3: Symbols & Bluetooth (accessed via Space hold)

```text
┌─────┬─────┬─────┬─────┬─────┬─────┐       ┌─────┬─────┬─────┬─────┬─────┬─────┐
│     │  !  │  @  │  #  │  $  │  %  │       │  ^  │  &  │  *  │  (  │  -  │     │
├─────┼─────┼─────┼─────┼─────┼─────┤       ├─────┼─────┼─────┼─────┼─────┼─────┤
│     │ USB │ BLE │  {  │  [  │  (  │       │  )  │  ]  │  }  │     │  =  │     │
├─────┼─────┼─────┼─────┼─────┼─────┤       ├─────┼─────┼─────┼─────┼─────┼─────┤
│     │BT 0 │BT 1 │BT 2 │BT 3 │BT 4 │       │BtClr│  ▽  │  ▽  │  ▽  │Unlck│     │
└─────┴─────┴─────┼─────┼─────┼─────┤       ├─────┼─────┼─────┼─────┴─────┴─────┘
                  │     │     │  ▽  │       │  ▽  │█████│     │
                  └─────┴─────┴─────┘       └─────┴─────┴─────┘
```

### Layer 4: Right-hand mods (accessed via ; hold)

```text
┌─────┬─────┬─────┬─────┬─────┬─────┐       ┌─────┬─────┬─────┬─────┬─────┬─────┐
│     │ Tab │  ▽  │  ▽  │  ▽  │  ▽  │       │  ▽  │  ▽  │  ▽  │  ▽  │  ▽  │     │
├─────┼─────┼─────┼─────┼─────┼─────┤       ├─────┼─────┼─────┼─────┼─────┼─────┤
│     │  ▽  │  ▽  │  ▽  │  ▽  │  ▽  │       │  ▽  │ Cmd │ Ctl │Shift│█████│     │
├─────┼─────┼─────┼─────┼─────┼─────┤       ├─────┼─────┼─────┼─────┼─────┼─────┤
│     │  ▽  │  ▽  │  ▽  │  ▽  │  ▽  │       │  ▽  │  ▽  │  ▽  │  ▽  │  ▽  │     │
└─────┴─────┴─────┼─────┼─────┼─────┤       ├─────┼─────┼─────┼─────┴─────┴─────┘
                  │     │  ▽  │  ▽  │       │  ▽  │  ▽  │     │
                  └─────┴─────┴─────┘       └─────┴─────┴─────┘
```

### 🔗 **Combos**

| Combo | Keys | Result |
|-------|------|--------|
| Caps Lock | Both inner thumbs | `CAPSLOCK` |
| `(` | R + T | Left parenthesis |
| `)` | Y + U | Right parenthesis |
| `[` | F + G | Left bracket |
| `]` | H + J | Right bracket |
| `{` | V + B | Left brace |
| `}` | N + M | Right brace |

### 🎯 **Key Legend**
- **Q/Alt**: Tap for Q, hold for Left Alt (tap-preferred, enables key repeat)
- **;/L4**: Tap for semicolon, hold for Layer 4 (right-hand modifiers)
- **Z/L1, Bs/L2, Sp/L3**: Layer-tap keys (tap-preferred)
- **Esc/H**: Tap for Escape, hold for Hyper (Alt+Shift+GUI+Ctrl)
- **█████**: Current layer activation key
- **RectF/C/EN/LH/BH/TH/RH/MV**: Rectangle window manager shortcuts
- **BT 0-4**: Bluetooth profile selection
- **BtClr**: Clear all Bluetooth pairings
- **USB/BLE**: Select the preferred keyboard output
- **Unlck**: Unlock ZMK Studio for editing
- **Blank** = `&none` (key does nothing)
- **▽** = `&trans` (transparent — falls through to the layer below)
- **█████** = layer activation key (held to access this layer)

### ZMK Studio

Studio is enabled on the central (left) half. Connect that half to the computer with a data-capable USB cable and open [ZMK Studio](https://zmk.studio/) in Chrome/Edge or the [desktop app](https://zmk.studio/download). If USB and Bluetooth are both connected, hold the right Space thumb key and press **A** to select USB output; hold Space and press **S** to select Bluetooth output again. To unlock editing, hold Space and press the **/** key. These are positions on the base layer, not characters to type.

Studio saves keymap changes on the keyboard. Once Studio manages the keymap, later changes to `config/corne.keymap` will not take effect until you use **Restore Stock Settings** in Studio. Keep the unlock and output-selection bindings accessible when editing the keymap.

### Display Settings

Modify `config/corne.conf` to control display behavior:

```conf
CONFIG_ZMK_DISPLAY=y                        # Enable OLED display
CONFIG_ZMK_DISPLAY_STATUS_SCREEN_CUSTOM=y   # Use custom status screen
```

**Optional Settings:**
```conf
# Enable RGB underglow (requires additional hardware)
CONFIG_ZMK_RGB_UNDERGLOW=y
CONFIG_WS2812_STRIP=y

# Adjust display timeout and brightness
CONFIG_ZMK_DISPLAY_WORK_QUEUE_DEDICATED=y
```

---

## **Building Firmware**

### Automatic Builds (Recommended)

The reusable build workflow is pinned to the same ZMK release as `config/west.yml` to keep its build tooling compatible.

1. **Push changes** to your forked repository
2. **GitHub Actions** automatically builds firmware
3. **Download** from Actions tab → latest workflow run → Artifacts
4. **Files generated:**
   - `corne_left nice_view_adapter nice_view-nice_nano_v2-zmk.uf2` (left half)
   - `corne_right nice_view_adapter nice_view_custom-nice_nano_v2-zmk.uf2` (right half)

Extract the `firmware` artifact. For each half, connect it via USB, double-press its reset button to enter the bootloader, and copy the matching UF2 to the mounted drive. The controller will restart after flashing. Do not swap the left and right files.

### Manual/Local Builds

**Prerequisites:**
- ZMK development environment set up
- West build tool installed

**Build commands:**
```bash
# Left half
west build -p -b nice_nano_v2 -S studio-rpc-usb-uart -- -DSHIELD="corne_left nice_view_adapter nice_view" -DCONFIG_ZMK_STUDIO=y

# Right half  
west build -p -b nice_nano_v2 -- -DSHIELD="corne_right nice_view_adapter nice_view_custom"
```

---

##  **Image Conversion Details**

### Automatic Conversion

The `niceview_lvgl_convert.py` script processes images with these steps:

1. **Resize** to 68×140 pixels (optimized for Nice!View)
2. **Rotate** 90° clockwise for proper display orientation
3. **Convert** to 1-bit black/white using Floyd-Steinberg dithering
4. **Invert** colors (white ↔ black) for display compatibility
5. **Generate** LVGL C arrays with `LV_IMG_CF_INDEXED_1BIT` format

### Manual Testing

**Install dependencies:**
```bash
pip install Pillow
```

**Convert single image:**
```bash
python3 scripts/niceview_lvgl_convert.py assets/logo.png --outdir converted
```

**Useful flags:**
- `--no-rotate`: Keep original orientation
- `--no-dither`: Disable Floyd-Steinberg dithering  
- `--lsb-first`: Change bit packing order
- `--width 68 --height 140`: Custom dimensions

### Image Guidelines

**Recommended specs:**
- **Format**: PNG, JPG, WEBP, GIF
- **Size**: Any size (auto-resized to 68×140)
- **Content**: High contrast works best
- **Filename**: Letters, numbers, underscores only

**Pro tips:**
- Black and white images convert best
- Avoid fine details (display is only 68×140 pixels)
- Test locally before committing

---

## **Local Development**

### Setting Up Local Environment

1. **Install ZMK dependencies:**
   ```bash
   # Follow ZMK's getting started guide
   pip3 install --user -U west
   west init -l config
   west update
   west zephyr-export
   ```

2. **Install image conversion tools:**
   ```bash
   pip install Pillow
   ```

3. **Test image conversion:**
   ```bash
   python3 scripts/niceview_lvgl_convert.py assets/test.png --outdir test_output
   ```

### Development Workflow

1. **Edit keymap** in `config/corne.keymap`
2. **Add images** to `assets/` folder
3. **Test conversion** locally (optional)
4. **Build firmware** using GitHub Actions or locally
5. **Flash and test** on hardware

---

### Getting Help

- **ZMK Documentation**: [zmk.dev](https://zmk.dev)
- **ZMK Discord**: [discord.gg/8cfMkQksSB](https://discord.gg/8cfMkQksSB)
- **Nice!Keyboards**: [nicekeyboards.com](https://nicekeyboards.com)

### Tips

- **High-contrast artwork** works best on the 1-bit display
- **Keep backups** of your working firmware files
- **Test one change at a time** when troubleshooting
- **Check Actions logs** for detailed error messages

---

##  **Contributing**

Feel free to:
- 🐛 **Report bugs** via GitHub Issues
- 💡 **Suggest improvements** for the artwork system
- 🔧 **Submit PRs** for widget enhancements
- 📚 **Improve documentation**


---

## **License**

This configuration is provided under the MIT License. See individual files for their respective licenses.

---

**Built with ❤️ on ZMK**

*Need help customizing the rotation interval, keymap layout, or adding new features? Open an issue and let's make this configuration even better!*
