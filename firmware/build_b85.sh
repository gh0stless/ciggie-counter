#!/bin/bash
# Baut ein Projekt fuer B85 (TLSR8258) mit dem TC BLE SDK, ohne IDE.
# Flags/Defines/Linkerskript 1:1 aus tc_ble_sdk/build/B85/.cproject (Konfiguration acl_peripheral_demo).
#
# Aufruf (Git Bash):  firmware/build_b85.sh [projekt] [clean]
#   projekt = Ordner unter firmware/ (eigenes Projekt, z. B. superascher; Standard)
#             oder ein SDK-Beispiel unter vendor/ (z. B. acl_peripheral_demo)
# Ergebnis:           firmware/out/<projekt>/<projekt>.bin

set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
SDK="$HERE/tc_ble_sdk/tc_ble_sdk"
TC32="$HOME/.Telink_Tools/tc32_130_Windows/tc32/bin"
export PATH="$TC32:$PATH"

PROJ=${1:-superascher}
LIB=lt_8258_c0p4
OUT_REL="../../out/$PROJ"          # relativ zum SDK, damit keine Leerzeichen in Pfaden landen
INC="-I. -Ivendor/common -Idrivers/B85 -Icommon"

if [ -d "$HERE/$PROJ" ]; then
    # eigenes Projekt: kein __PROJECT_xxx__, stattdessen eigene app_config.h vorab einbinden
    PROJ_SRC="../../$PROJ"
    DEFS="-DCHIP_TYPE=CHIP_TYPE_825x -include $PROJ_SRC/app_config.h"
    INC="-I$PROJ_SRC $INC"
elif [ "$PROJ" = acl_peripheral_demo ]; then
    PROJ_SRC=""
    DEFS="-D__PROJECT_ACL_PER_DEMO__=1 -DCHIP_TYPE=CHIP_TYPE_825x"
else
    echo "Unbekanntes Projekt: $PROJ"; exit 1
fi

EXCLUDE="build drivers/TC123X boot/TC123x stack/ble/profile boot/TC321x boot/B87 drivers/TC321X drivers/B87"

cd "$SDK"
[ "$2" = clean ] && rm -rf "$OUT_REL"
mkdir -p "$OUT_REL/obj"

# aus vendor/ nur common und ggf. das SDK-Beispiel bauen
for d in vendor/*/; do
    d=${d%/}
    [ "$d" = vendor/common ] || [ "$d" = "vendor/$PROJ" ] || EXCLUDE="$EXCLUDE $d"
done

CFLAGS="-ffunction-sections -fdata-sections $INC $DEFS -O2 -std=gnu99 -fshort-wchar -fms-extensions \
-fpack-struct -fshort-enums -finline-small-functions"
ASFLAGS="-ffunction-sections -fdata-sections $INC $DEFS -DMCU_STARTUP_8258"

prune=""
for d in $EXCLUDE; do prune="$prune -path ./$d -prune -o"; done
SRCS=$(eval find . $prune \\\( -name "'*.c'" -o -name "'*.S'" \\\) -print | sed 's|^\./||' | sort)
[ -n "$PROJ_SRC" ] && SRCS="$SRCS
$(ls $PROJ_SRC/*.c)"

compile() {
    src="$1"; obj="$OUT_REL/obj/${src#../../}"; obj="${obj%.*}.o"
    [ "$obj" -nt "$src" ] && return 0
    mkdir -p "$(dirname "$obj")"
    case "$src" in
        *.S) tc32-elf-gcc $ASFLAGS -c "$src" -o "$obj" ;;
        *)   tc32-elf-gcc $CFLAGS  -c "$src" -o "$obj" ;;
    esac || { echo "FEHLER: $src"; return 1; }
}
export -f compile; export OUT_REL CFLAGS ASFLAGS

echo "Kompiliere $(echo "$SRCS" | wc -l) Dateien ..."
echo "$SRCS" | xargs -P "$(nproc)" -I{} bash -c 'compile "$@"' _ {}

OBJS=$(echo "$SRCS" | sed -E -e "s|^\.\./\.\./||" -e "s|^(.*)\.[cS]$|$OUT_REL/obj/\1.o|")
tc32-elf-ld --gc-sections -L proj_lib -T build/B85/boot.link -o "$OUT_REL/$PROJ.elf" $OBJS -l$LIB
tc32-elf-objcopy -O binary "$OUT_REL/$PROJ.elf" "$OUT_REL/$PROJ.bin"
./tl_check_fw2.exe "$OUT_REL/$PROJ.bin"
tc32-elf-size -t "$OUT_REL/$PROJ.elf"
ls -l "$OUT_REL/$PROJ.bin"
