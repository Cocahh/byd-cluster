#!/bin/bash
cd "$(dirname "$0")"
mkdir -p out/props2
for u in "$@"; do
  echo "[{\"name\":\"${u%@*}_b\",\"setup\":{\"bg\":[0,0,0],\"pp\":{\"vignetteEnable\":false}},\"pos\":\"auto:${u#*@}\",\"target\":null,\"w\":900,\"h\":900},{\"name\":\"${u%@*}_w\",\"setup\":{\"bg\":[1,1,1]},\"pos\":\"auto:${u#*@}\",\"target\":null,\"w\":900,\"h\":900}]" > out/props2/j.json
  node cdp2.mjs "file://$PWD/prop.html?${u%@*}" out/props2/j.json out/props2 2>&1 | grep -E "state|saved|fail" | tr '\n' ' '; echo
done
echo done
