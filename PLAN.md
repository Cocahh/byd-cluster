# King custom screens plan

Two products, one app, one 3D car.

1. **Driver display (Road)**: speed and hybrid data on the left, lane ahead with the King from behind on the right.
2. **Home screen (Garage)**: replaces BYD's home on the 12.8 inch screen. The King in 3D, tap a window to open or close it, big shortcuts to CarPlay, Navigation and Stremio, seasonal themes.

## Shared foundation

- **3D model**: Sketchfab "2025 BYD Seal 5 DM-i (Chazor King Destroyer 05)" by ddiaz-design, uid `c3bdefa332384e95a9fd249d0abb25c3`, CC BY-NC-SA. Same body as the Brazilian King: slatted grille, lit BYD bar, full-width rear light bar. 470k faces, separate materials (`CarPaint`, `Glass`, `Red_emiss`, `Light_glass`, `CHROME`...). Personal, non-commercial use with credit.
  - Needs the glTF download, which needs a Sketchfab login.
  - Decimate to about 60k faces for the head unit GPU (Snapdragon 625 class), bake lighting, recolor `CarPaint` to the owner's paint.
- **Type**: Neue Haas Display (Light, Roman, Medium), bundled in the app. Tracking 0.
- **Data**: BYD `android.hardware.bydauto.*` (speed, gear, engine, energy, instrument lights, bodywork windows and doors).
- **Access**: head unit ADB (build 2410 now; dialer code test pending).

## Phase 1: driver display (Road)

Design rules, from Polestar, Tesla FSD, XPeng references:
- Chase camera behind the car, about 1.5 car heights up, looking down about 15 degrees. Car centred in the right panel, rear bumper at about 78% of the height, about 20% of the panel width.
- Road is a flat plane a step above black that fades to pure black over its top third. No horizon or scenery.
- Lane edges are 1.5 to 2px hairlines at 25 to 40% white, fading with distance. Dashes slide toward the camera at true road speed.
- The King renders in its real paint with soft top light and a contact shadow. The tail light bar is the one bright detail and gets brighter under braking.
- Speed is regular weight Neue Haas, about 170px, with km/h small. P R N D with only the active gear lit. Battery and fuel as value plus thin bar. One accent colour.
- Motion: dashes match speed, the car sways slightly on lane change (turn signal), the brake light bar responds to deceleration, numbers move smoothly, a short start-up sequence when the car turns on.

Production path:
1. Render the King offline from the chase camera in three.js (headless), as transparent PNG layers: body, tail lights normal, tail lights braking, and a few yaw angles for sway. Cheap to draw on the cluster.
2. Road, lanes and data drawn live on canvas at 30 fps.
3. Package in the Android host app on the `fission_bg_xdjaVirtualSurface` display after the `AutoContainer` projection call.

## Phase 2: home screen (Garage)

- Android app registered as HOME (BYD lets the owner pick it). One page:
  - The King in real-time 3D (three.js in a WebView or Filament natively), slow idle turntable, drag to rotate.
  - Tap a window: the glass animates down, the app calls BYD bodywork window control, and the 3D state follows the real `getWindowOpenPercent`. Same for the trunk and lock status if exposed.
  - Large shortcuts: CarPlay (`com.byd.carplay.ui`), Navigation (`com.byd.automap` or Waze), Stremio. BYD's own home stays one tap away.
  - Seasonal themes: Christmas, Halloween, Carnaval, Festa Junina. Each changes the scene around the car (light, ground, a few props) and the accent colour.
- To verify on the car: window control permissions from a third-party app, GPU frame rate with the decimated model, HOME selection on DiLink 3.0.

## Needed from Luiz

- Sketchfab: sign in (free account) and download the model as glTF, or sign in inside Claude's browser so it can download it.
- King paint colour.
- Dialer code result (`*#91532547#*` on the car's phone app).
