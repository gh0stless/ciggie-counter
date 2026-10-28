#!/bin/bash
# Flasht eine mit build_b85.sh gebaute Firmware per Telink-Programmer (BDT-Kommandozeile) auf den TLSR8258.
# Befehle wie in der Vorlage der Telink-VS-Code-Extension (.tlk/flash_download.ps1).
#
# Aufruf (Git Bash):  firmware/flash_b85.sh [projekt] [usb-index]
#   ohne usb-index werden nur die gefundenen Programmer aufgelistet.
# Verkabelung: GND-GND, SWM-SWS (VCC-VCC nur, wenn das Board nicht ueber eigenes USB versorgt wird)

set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
BDT="$HOME/.Telink_Tools/BDT/BDT/release_v5.9.5/config/Cmd_download_tool.exe"
PROJ=${1:-superascher}
IDX=$2
CHIP=B85
ADDR=0x00
BIN="$HERE/out/$PROJ/$PROJ.bin"

[ -f "$BIN" ] || { echo "Nicht gefunden: $BIN (erst build_b85.sh laufen lassen)"; exit 1; }

if [ -z "$IDX" ]; then
    "$BDT" all
    echo
    echo "Device-ID aus der Liste oben waehlen und erneut aufrufen: firmware/flash_b85.sh $PROJ <id>"
    exit 0
fi

BIN_WIN=$(cygpath -w "$BIN")
# Activate: haelt den Chip an, sonst antwortet SWS nicht, solange die Firmware im Deep Sleep ist
"$BDT" "$IDX" $CHIP ac
"$BDT" "$IDX" $CHIP lf 0 0 || echo "Warnung: Entsperren fehlgeschlagen, schreibe trotzdem"
"$BDT" "$IDX" $CHIP wf $ADDR -i "$BIN_WIN"
"$BDT" "$IDX" $CHIP rst -f
echo "Fertig: $PROJ auf Programmer $IDX geflasht."
