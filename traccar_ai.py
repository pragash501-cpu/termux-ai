import os, json, base64, urllib.request, urllib.error

API_KEY = os.environ.get("GEMINI_API_KEY", "")
T_URL = os.environ.get("TRACCAR_URL", "").rstrip("/")
T_USER = os.environ.get("TRACCAR_USER", "")
T_PASS = os.environ.get("TRACCAR_PASS", "")
HIST_FILE = os.path.expanduser("~/termux-ai/traccar_history.json")

def traccar_get(endpoint):
    tok = os.environ.get("TRACCAR_TOKEN", "")
    auth = f"Bearer {tok}" if tok else "Basic " + base64.b64encode(f"{T_USER}:{T_PASS}".encode()).decode()
    req = urllib.request.Request(f"{T_URL}/api/{endpoint}", headers={"Authorization": auth, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Traccar HTTP {e.code} on /api/{endpoint}: {e.read().decode()}") from None

def get_fleet_status():
    devs = {d["id"]: d for d in traccar_get("devices")}
    pos = traccar_get("positions")
    fleet = []
    for p in pos:
        d = devs.get(p["deviceId"], {})
        spd = round(p.get("speed", 0) * 1.852, 1)
        fleet.append({
            "vehicle": d.get("name", f"ID-{p['deviceId']}"),
            "status": d.get("status", "unknown"),
            "speed_kmh": spd,
            "lat": p.get("latitude"), "lon": p.get("longitude"),
            "address": p.get("address", "N/A"),
            "ignition": p.get("attributes", {}).get("ignition"),
            "fix_time": p.get("fixTime")
        })
    return fleet

def load_hist():
    if os.path.exists(HIST_FILE):
        with open(HIST_FILE, "r") as f: return json.load(f)
    return []

def ask_gemini(history):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={API_KEY}"
    tools = [{"function_declarations": [{
        "name": "get_fleet_status",
        "description": "Fetch live GPS location, speed, ignition, and status of all vehicles from Traccar."
    }]}]
    payload = {
        "system_instruction": {"parts": [{"text": "You are a fleet tracking assistant. Use get_fleet_status whenever asked about vehicles. Be concise."}]},
        "contents": history, "tools": tools
    }
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {e.read().decode()}") from None

def main():
    history = load_hist()
    print("Traccar AI ready (history loaded). Type 'exit' or 'clear'.\n")
    while True:
        q = input("You: ").strip()
        if not q: continue
        if q.lower() == "exit": break
        if q.lower() == "clear":
            history = []; os.remove(HIST_FILE) if os.path.exists(HIST_FILE) else None
            print("History cleared.\n"); continue
        history.append({"role": "user", "parts": [{"text": q}]})
        try:
            res = ask_gemini(history)
            part = res["candidates"][0]["content"]["parts"][0]
            if "functionCall" in part:
                history.append(res["candidates"][0]["content"])
                data = get_fleet_status()
                history.append({"role": "user", "parts": [{"functionResponse": {"name": "get_fleet_status", "response": {"fleet": data}}}]})
                res = ask_gemini(history)
                part = res["candidates"][0]["content"]["parts"][0]
            reply = part.get("text", "")
            history.append({"role": "model", "parts": [{"text": reply}]})
            with open(HIST_FILE, "w") as f: json.dump(history[-20:], f)
            print(f"\nAI: {reply}\n")
        except Exception as e:
            history.pop()
            print(f"\n[Error] {e}\n")

if __name__ == "__main__": main()
