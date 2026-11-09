#!/bin/bash
# Installs and controls the King screens on the car over Wi-Fi ADB.
# Usage: ./car.sh <car-ip> <command>
#   check          show what the car is and whether ADB works
#   install        install the app, grant what it needs, start it
#   probe          dump every BYD data call the car offers into snapshots/
#   mapping        push app/assets/mapping.json to the car without reinstalling
#   home on|off    make King the home screen, or give it back to BYD
#   cluster on|off open or close the driver display projection
#   logs           follow the app log
#   uninstall      close everything, restore BYD home, remove the app
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
ADB="$HERE/tools/platform-tools/adb"
PKG=com.luiz.king
TARGET="${1:?usage: ./car.sh <car-ip> <command>}"; CMD="${2:-check}"; ARG="${3:-}"
[[ "$TARGET" == *:* ]] || TARGET="$TARGET:5555"
SNAP="$HERE/snapshots"; mkdir -p "$SNAP"
A() { "$ADB" -s "$TARGET" "$@"; }
S() { A shell "$@" 2>&1; }
"$ADB" connect "$TARGET" >/dev/null 2>&1
if ! A get-state >/dev/null 2>&1; then
  echo "Cannot reach $TARGET. Check that the car and this Mac are on the same Wi-Fi, that wireless ADB is on, and accept the prompt on the car screen."; exit 1
fi
service_call() { local out; out="$(S service call AutoContainer "$@")"; echo "  AutoContainer $* -> $out"; [[ "$out" == *"Parcel(00000000"* ]]; }
cluster_off() { service_call 46 || service_call 45; sleep 1.2; service_call 18; sleep 1.2; service_call 0; }
home_save() { [ -f "$SNAP/home_before.txt" ] || S cmd package resolve-activity --brief -c android.intent.category.HOME -a android.intent.action.MAIN | tail -1 > "$SNAP/home_before.txt"; }
case "$CMD" in
  check)
    echo "Build:   $(S getprop ro.build.display.id)"; echo "Android: $(S getprop ro.build.version.release) (SDK $(S getprop ro.build.version.sdk))"
    echo "Screen:  $(S wm size | tail -1)"; echo "Home:    $(S cmd package resolve-activity --brief -c android.intent.category.HOME -a android.intent.action.MAIN | tail -1)"
    echo "King:    $(S pm list packages $PKG | head -1)"; echo "Displays:"; S dumpsys display | grep -E 'mDisplayId=|DisplayDeviceInfo\{"' | head -12 ;;
  install)
    [ -f "$HERE/app/build/king.apk" ] || { echo "Build first: app/build.sh"; exit 1; }
    home_save
    A install -r -g "$HERE/app/build/king.apk" || { echo "Install failed. If the car blocks installs from ADB, tell Claude what it printed."; exit 1; }
    S appops set $PKG SYSTEM_ALERT_WINDOW allow >/dev/null
    S settings put global hidden_api_policy 1 >/dev/null
    S am start -n $PKG/.HomeActivity --ez probe true >/dev/null
    sleep 6; A pull /sdcard/Android/data/$PKG/files/probe.json "$SNAP/probe-$(date +%Y%m%d-%H%M%S).json" 2>&1 | tail -1
    echo "Installed and started. The home screen should be on the center display now."
    echo "Next: ./car.sh ${TARGET%:*} home on    (only after you like what you see)" ;;
  probe)
    S am start -n $PKG/.HomeActivity --ez probe true >/dev/null; sleep 6
    A pull /sdcard/Android/data/$PKG/files/probe.json "$SNAP/probe-$(date +%Y%m%d-%H%M%S).json" 2>&1 | tail -1 ;;
  mapping)
    A push "$HERE/app/assets/mapping.json" /sdcard/Android/data/$PKG/files/mapping.json | tail -1
    S am start -n $PKG/.HomeActivity --ez reload true >/dev/null; echo "Mapping pushed and reloaded." ;;
  home)
    home_save
    if [ "$ARG" = "on" ]; then S cmd package set-home-activity $PKG/.HomeActivity; S am start -a android.intent.action.MAIN -c android.intent.category.HOME >/dev/null
    elif [ "$ARG" = "off" ]; then
      BEFORE="$(cat "$SNAP/home_before.txt" 2>/dev/null)"
      if [[ "$BEFORE" == */* && "$BEFORE" != $PKG/* ]]; then S cmd package set-home-activity "$BEFORE"; S am start -a android.intent.action.MAIN -c android.intent.category.HOME >/dev/null; echo "Home restored to $BEFORE"
      else echo "No saved BYD home found. Use the Home chooser on the car, or run uninstall."; fi
    else echo "usage: ./car.sh <ip> home on|off"; fi ;;
  cluster)
    if [ "$ARG" = "on" ]; then
      echo "Park the car first. Opening the driver display projection:"
      service_call 2 i32 1000 i32 16 s16 null || { echo "The car refused. Nothing was changed."; exit 1; }
      sleep 1.2; service_call 35; sleep 1.5
      S am startservice -n $PKG/.ClusterService >/dev/null
      sleep 2; S dumpsys display | grep -iE 'fission|xdja' | head -3
      echo "If the driver display looks wrong in any way, run: ./car.sh ${TARGET%:*} cluster off"
    elif [ "$ARG" = "off" ]; then cluster_off; echo "Projection closed. BYD's own panel should be back."
    else echo "usage: ./car.sh <ip> cluster on|off"; fi ;;
  logs) A logcat -s King:V AndroidRuntime:E ;;
  uninstall)
    cluster_off >/dev/null 2>&1
    BEFORE="$(cat "$SNAP/home_before.txt" 2>/dev/null)"; [[ "$BEFORE" == */* && "$BEFORE" != $PKG/* ]] && S cmd package set-home-activity "$BEFORE" >/dev/null
    A uninstall $PKG; S settings delete global hidden_api_policy >/dev/null; echo "Removed. The car is back to stock." ;;
  *) sed -n '2,12p' "$0" ;;
esac
