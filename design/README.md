# Design

| Folder / file | What it is |
|---|---|
| `brand-flag.jpg` | Project flag; source of the app colours (referenced from the Android and Nextcloud code) |
| `screenshots/` | App screenshots (the Nextcloud app store loads some of them by URL, so keep the names) |
| `ascher/` | Photos of the ashtrays the knob is made for (Value spin ashtray, a cheap one) |
| `fotoshooting/` | Renders of the current knob design on the Value ashtray: single shots from several angles and distances, close-ups, group shots in different button colours |
| `aufkleber/` | "Butt Bin by crazy-midi.de" sticker: print-ready SVGs (text as outlines), PNG previews, generator `gen_aufkleber.py` |

The renders come from the FreeCAD scripts in `hardware/freecad/` (`knauf.py`, `gruppe.py`, `ascher_value.py`)
and are rendered with `hardware/freecad/render_blender.py` (Blender, Cycles).
The early AI concept images (stainless cylinder with a display) were dropped when the design moved to the
knob on the spin ashtray; they are still in the git history.
