# Car day

Everything below runs from this Mac, next to the car. Each step can be undone and nothing is written to BYD's own software.

## Before you start

1. Car in P, parking brake on. Keep it parked for the whole session.
2. Put the car and the Mac on the same Wi-Fi. Your phone's hotspot works.
3. On the car's phone dialer, type `*#91532547#*`. A hidden menu should open. Turn on wireless ADB (it may be called "ADB over network" or "Debug mode").
   - If no menu opens, stop here and tell Claude. Build 2410 may need an update first.
4. Find the car's IP address in its Wi-Fi settings.

## Steps

Run these one at a time, replacing `CAR_IP`. The first connection shows "Allow debugging?" on the car screen. Tick "Always allow" and accept.

```bash
cd ~/Projects/byd-cluster && ./car.sh CAR_IP check
```

```bash
cd ~/Projects/byd-cluster && ./inspect.sh CAR_IP
```

```bash
cd ~/Projects/byd-cluster && ./car.sh CAR_IP install
```

The new home screen should now be on the center display. Try the car turning, the settings page and themes, and the CarPlay, Navigation and Browser buttons. Numbers that show `--` are expected on the first visit.

If you like it, make it the home screen:

```bash
cd ~/Projects/byd-cluster && ./car.sh CAR_IP home on
```

Then try the driver display, still parked:

```bash
cd ~/Projects/byd-cluster && ./car.sh CAR_IP cluster on
```

Check that BYD's own warning lights are still visible and that the speed reads 0. If anything looks wrong:

```bash
cd ~/Projects/byd-cluster && ./car.sh CAR_IP cluster off
```

## Undo everything

```bash
cd ~/Projects/byd-cluster && ./car.sh CAR_IP uninstall
```

This closes the driver display projection, gives the home screen back to BYD and removes the app.

## What to send back to Claude

The `snapshots` folder. It holds `probe-*.json`, the list of every data call this car offers, which is what turns the `--` values into real numbers.

## Known limits on the first visit

- The app has never run on a real car. Opening apps, themes and the home screen do not depend on BYD data. Battery, fuel, range, temperature, speed and turn signals do, and their names in `app/assets/mapping.json` are best guesses until the probe file confirms them.
- Window buttons animate on screen but do not move the real glass yet. Real control stays off until the probe shows the exact call.
- The driver display refuses to show unless the car's speed can be read, so it may stay on BYD's panel on the first visit. That is the safe result.
- The driver display has to be started from the Mac each time for now. Starting it from the car itself comes after this first test proves the projection works on build 2410.
- Do not drive with the custom driver display until a parked test has confirmed speed, warning lights and `cluster off` all behave.
