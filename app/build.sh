#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
export JAVA_HOME="${JAVA_HOME:-/opt/homebrew/opt/openjdk}"
PATH="$JAVA_HOME/bin:$PATH"
BT=../tools/android/build-tools
JAR=../tools/android/platform/android.jar
rm -rf build && mkdir -p build/classes build/dex
(cd ../panel && /opt/homebrew/bin/python3.14 build.py >/dev/null)
cp ../panel/king-home.html ../panel/king-road.html assets/
javac -nowarn --release 11 -cp "$JAR" -d build/classes src/com/luiz/king/*.java
"$BT/d8" --lib "$JAR" --min-api 24 --output build/dex $(find build/classes -name '*.class')
"$BT/aapt2" link -o build/base.apk --manifest AndroidManifest.xml -I "$JAR" -A assets
(cd build/dex && zip -q -j ../base.apk classes.dex)
"$BT/zipalign" -f 4 build/base.apk build/aligned.apk
[ -f debug.keystore ] || keytool -genkeypair -keystore debug.keystore -storepass android -keypass android -alias king -keyalg RSA -keysize 2048 -validity 10000 -dname "CN=King" >/dev/null 2>&1
"$BT/apksigner" sign --ks debug.keystore --ks-pass pass:android --key-pass pass:android --out build/king.apk build/aligned.apk
"$BT/apksigner" verify build/king.apk && ls -la build/king.apk | awk '{print "king.apk", $5}'
