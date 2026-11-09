# BYD King custom screens

Custom designs for the 8.8 inch driver display and the 12.8 inch center screen on Luiz's 2025 King GS (Brazil).

## The car

- Multimedia: `13.1.32.2410130.1` (DiLink 3.0 family, build of 13 Oct 2024)
- FWC: `13.5.5.2407180.2.13.5.2.2307280.1`
- Hardware: `V02.E03.00.04.03`
- Community ADB method needs build 2412 or newer. Builds from 2503 may show a QR code that blocks it.

## How the driver display can be reached (learned from EvSound 3.30)

- The driver display is not an Android display by default. BYD's `AutoContainer` system service opens a projection window on it.
  - Open: `service call AutoContainer 2 i32 1000 i32 16 s16 null` (full) or `17` (half), then `35`.
  - Close: `46` (or `45`), then `18`, then `0`, about 1.2 s apart.
  - Success reply starts with `Result: Parcel(00000000`.
- Once open, Android exposes a presentation display named `fission_bg_xdjaVirtualSurface`. An activity or `Presentation` placed on it shows on the driver display.
- Known panel sizes in the wild: 1920x720 and 1280x480 (both 8:3).
- `service call` needs shell rights, so the app talks to the head unit's own ADB at `127.0.0.1:5555`. Wi-Fi ADB must be on and the app authorized once ("Always allow").
- Vehicle data comes from BYD's `android.hardware.bydauto.*` classes (speed, gearbox, engine, energy, instrument warning lights, fuel and battery).
- EvSound renders its panel skins as HTML in a WebView. Its code is proprietary, so nothing here is copied from it; only the system interfaces above are used.

## Running it on the car

`CAR-DAY.md` is the step by step for the first visit. `car.sh` wraps every command (install, probe, home on or off, cluster on or off, uninstall).

The Android app lives in `app/` and builds without Gradle: `app/build.sh` compiles the three Java files against `tools/android/platform/android.jar`, packs both screens into the APK and signs it. It needs the Homebrew JDK, and nested classes must stay static because the bundled d8 fails on JDK 27 inner class metadata.

- `HomeActivity` is the launcher. It hosts `king-home.html`, exposes `KingHost` to the page and pushes state every 400 ms.
- `ClusterService` watches for the projected driver display, shows `king-road.html` on it and pushes state every 100 ms. It will not show unless speed is readable.
- `Byd` reads the car through reflection on `android.hardware.bydauto.*`, driven by `app/assets/mapping.json`. A copy pushed with `./car.sh <ip> mapping` overrides it without a rebuild. `probe` dumps every class, constant and getter value to `probe.json`.
- Opening the driver display projection still needs shell rights, so `car.sh cluster on` does it from the Mac. An in-app ADB client is the next step once the projection is proven on build 2410.

## Panel data contract

`KingPanel.setTheme('standard'|'halloween'|'christmas')` and `KingPanel.fault(true)` (speed shows `--`) are also available.

`window.KingPanel.update({ speed, gear, powerKw, engineOn, soc, fuelPct, evRangeKm, totalRangeKm, odoKm, tripKm, tripL100, tripKwh100, outsideC, clock, turnL, turnR, warnings: [{ label, level }] })`

`#car` shows the panel full screen with no simulation; `#car-demo` runs the simulated drive full screen.

## Home screen

`panel/home.src.html` builds to `panel/king-home.html` (`python3 build.py` builds both screens).

- The car is a 48 frame turntable rendered from the Sketchfab model, not live 3D. Each angle has a closed frame (`cNN.webp`), an open window overlay (`oNN.webp`), a window id mask (`mNN.png`, value 60 per id, order fl, fr, rl, rr), a lamp overlay (`eNN.webp`) and a snow overlay (`nNN.webp`) in `panel/assets/home`.
- Camera: 7.5 m from the car, 1.6 m high, looking at a point 0.7 m up, 215 px per metre on screen. `meta.json` carries it. Halloween and Christmas backdrops are Poly Haven panoramas (CC0: misty_farm_road, blaubeuren_church_square) reprojected into that same camera by `render/plate.py`, so the ground lines up with the car.
- Themes are chosen on the page's own Settings view, not on the home screen. The page calls `KingHost.setTheme(name)` so the driver display follows.
- The model has no separate window nodes. Material `Glass` is all window glass and `D_Glass` is only the sunroof, so windows are split from a glass mask render and labelled by projecting onto the door planes.
- Contract in: `window.KingHome.update({ clock, date, outsideC, soc, fuelPct, evRangeKm, totalRangeKm, carplay, parked, windows: { fl, fr, rl, rr } })` with windows as 0 to 100 percent open. `KingHome.setMode('auto'|'standard'|'halloween'|'christmas'|'carnaval')`.
- Contract out: `window.KingHost.openApp('carplay'|'nav'|'browser'|'settings')` and `KingHost.setWindow(id, 'open'|'close')`, `KingHost.flashLights()`. Without a host the page simulates window travel.
- The scene is drawn in true perspective from the render camera (`meta.json` carries it): floor light, car shadow and the platter ring turn with the car, while theme props stay fixed around it. Lamps are a per angle overlay (`eNN.webp`) that wakes after the intro and can be flashed.
- Labels on leader lines sit on each visible door window and the headlamp, and hide while the car is turning.
- Theme props (`prop-*.webp`) are stills of CC licensed Sketchfab models, credited in the page footer. `render/props2.sh` and `render/matte.py` remake them, `render/lights.py` remakes the lamp overlays.
- The browser row is disabled unless `parked` is true.
- `#car` shows it full screen. `?still` skips the intro, `?mode=`, `?open=fl,rr` and `?ang=` set up a state for screenshots.

## Safety rules for any design

- Speed shown must be the car's own speed value, never GPS or a smoothed estimate that lags more than a fraction of a second.
- BYD's own warning lights must stay visible. Check on the car whether they remain in projection mode before driving with a custom panel.
- Closing the app or a crash must return the display to BYD's original panel.

## Re-rendering the car

`render/` holds the pipeline: `gen_jobs.py` writes the camera jobs (48 angles, four passes: closed, glass hidden, glass mask, silhouette), `node cdp.mjs file://$PWD/sk.html jobs.json out` renders them through the Sketchfab viewer in headless Chrome, and `compose.py` turns the output into `panel/assets/home`. Paths inside the scripts point at a scratch folder and need adjusting before a new run.
