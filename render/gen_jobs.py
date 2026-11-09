import json, math
old = json.load(open("passes.json"))
setups = {"c": old[0]["setup"], "o": old[24]["setup"], "g": old[48]["setup"], "w": old[72]["setup"]}
R, el, tz, N = 0.2, math.radians(9), 0.0076, 48
jobs = []
for p in "cogw":
    first = True
    for i in range(N):
        a = math.radians(i * 360 / N)
        j = {"name": f"{p}_{i:02d}", "pos": [R*math.cos(el)*math.sin(a), -R*math.cos(el)*math.cos(a), tz + R*math.sin(el)], "target": [0, 0, tz], "w": 1600, "h": 1000}
        if first: j["setup"] = setups[p]; first = False
        jobs.append(j)
json.dump(jobs, open("jobs.json", "w"))
print(len(jobs))
