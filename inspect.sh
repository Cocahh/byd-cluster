#!/bin/bash
# Read-only snapshot of a BYD DiLink head unit over ADB. Changes nothing on the car.
# Usage: ./inspect.sh <car-ip>[:5555]
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
ADB="$HERE/tools/platform-tools/adb"
TARGET="${1:?usage: ./inspect.sh <car-ip>[:port]}"
[[ "$TARGET" == *:* ]] || TARGET="$TARGET:5555"
OUT="$HERE/snapshots/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$OUT/screens"

"$ADB" connect "$TARGET" | tee "$OUT/connect.txt"
"$ADB" -s "$TARGET" wait-for-device
A() { "$ADB" -s "$TARGET" "$@"; }
S() { A shell "$@" 2>&1; }

echo "== identity"
S getprop > "$OUT/getprop.txt"
grep -E 'ro.build.(display.id|version.release|version.sdk|fingerprint|date)\]|ro.product.(model|device|board)|byd|dilink|persist.sys.car|ro.hardware' "$OUT/getprop.txt" | tee "$OUT/identity.txt"

echo "== displays"
S dumpsys display > "$OUT/dumpsys_display.txt"
grep -E 'mDisplayId=|DisplayDeviceInfo\{|uniqueId=|mBaseDisplayInfo' "$OUT/dumpsys_display.txt" | head -40 | tee "$OUT/displays_short.txt"
S dumpsys SurfaceFlinger --display-id > "$OUT/sf_display_ids.txt"
S cmd display get-displays > "$OUT/cmd_displays.txt" 2>&1
S dumpsys window displays > "$OUT/window_displays.txt"
S wm size; S wm density

echo "== screenshots of every display"
for id in $(grep -oE 'mDisplayId=[0-9]+' "$OUT/dumpsys_display.txt" | cut -d= -f2 | sort -un); do
  A exec-out screencap -p -d "$id" > "$OUT/screens/display-$id.png" 2>/dev/null
  echo "display $id -> $(wc -c < "$OUT/screens/display-$id.png") bytes"
done
for pid in $(grep -oE '^Display [0-9]+' "$OUT/sf_display_ids.txt" | awk '{print $2}'); do
  A exec-out screencap -p -d "$pid" > "$OUT/screens/sf-$pid.png" 2>/dev/null
done

echo "== packages"
S pm list packages -f > "$OUT/packages.txt"
grep -iE 'cluster|instrument|ipc|meter|dashboard|autocontainer|clusterdebug|evsound|unlock|installer|testtool|engineer|launcher|navi|amap|autoservice' "$OUT/packages.txt" | tee "$OUT/packages_interesting.txt"
S pm list packages -3 > "$OUT/packages_third_party.txt"
echo "third-party:"; cat "$OUT/packages_third_party.txt"

echo "== system services"
S service list > "$OUT/services.txt"
grep -iE 'auto|byd|cluster|container|ipc|vehicle|car' "$OUT/services.txt" | tee "$OUT/services_interesting.txt"

echo "== settings"
for ns in global secure system; do S settings list $ns > "$OUT/settings_$ns.txt"; done
grep -hiE 'freeform|cluster|adb|development|overlay|projection' "$OUT"/settings_*.txt | tee "$OUT/settings_interesting.txt"

echo "== activity and window state"
S dumpsys activity activities > "$OUT/activities.txt"
S dumpsys activity services > "$OUT/activity_services.txt"
S dumpsys window windows > "$OUT/windows.txt"
grep -E 'Display #|mResumedActivity|topResumedActivity' "$OUT/activities.txt" | head -30

for p in $(grep -iE 'evsound|cluster' "$OUT/packages.txt" | sed -E 's/.*=//'); do
  S dumpsys package "$p" > "$OUT/pkg_$p.txt"
done

echo
echo "snapshot saved to $OUT"
