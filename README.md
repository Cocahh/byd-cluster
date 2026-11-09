# BYD King driver panel

A custom design for the 8.8 inch driver display on Luiz's 2025 King GS (Brazil).

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

## Safety rules for any design

- Speed shown must be the car's own speed value, never GPS or a smoothed estimate that lags more than a fraction of a second.
- BYD's own warning lights must stay visible. Check on the car whether they remain in projection mode before driving with a custom panel.
- Closing the app or a crash must return the display to BYD's original panel.
