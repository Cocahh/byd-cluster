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

## Plan

1. Get ADB on the car (dialer code test on 2410, else an update to 2412 to 2502).
2. Run `./inspect.sh <car-ip>` to snapshot displays, services and packages and screenshot the driver display.
3. Prove the projection by hand with the `AutoContainer` calls and a test page.
4. Build a small Android host app: WebView on the driver display, fed by `bydauto` data, calling `KingPanel.update(state)`.
5. Load `panel/king-panel.html#car` in it.

## Panel data contract

`window.KingPanel.update({ speed, gear, powerKw, engineOn, soc, fuelPct, evRangeKm, totalRangeKm, odoKm, tripKm, tripL100, tripKwh100, outsideC, clock, turnL, turnR, warnings: [{ label, level }] })`

`#car` shows the panel full screen with no simulation; `#car-demo` runs the simulated drive full screen.

## Home screen

`panel/home.src.html` builds to `panel/king-home.html` (`python3 build.py` builds both screens).

- The car is a 48 frame turntable rendered from the Sketchfab model, not live 3D. Each angle has a closed frame (`cNN.webp`), an open window overlay (`oNN.webp`) and a window id mask (`mNN.png`, value 60 per id, order fl, fr, rl, rr) in `panel/assets/home`.
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
