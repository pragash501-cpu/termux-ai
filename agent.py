import os, sys, re, time, json, subprocess, urllib.request, urllib.error

PID = os.getpid()

def set_status(msg):
    stop_cmd = f"kill -9 {PID}; termux-notification-remove voice_ai; termux-wake-unlock"
    subprocess.run([
        "termux-notification", "--id", "voice_ai", "--ongoing",
        "--title", "Gemini Voice AI", "--content", msg,
        "--button1", "Stop", "--button1-action", stop_cmd
    ])

def speak_text(text):
    clean = re.sub(r"[*#_`\]\[]", "", text or "").strip()
    if clean:
        set_status("Speaking...")
        subprocess.run(["termux-tts-speak"], input=clean, text=True)

def get_voice_input():
    set_status("Listening...")
    return subprocess.run(["termux-speech-to-text"], capture_output=True, text=True).stdout.strip()

def run_tool(name, args):
    if name == "check_battery_status":
        return subprocess.run(["termux-battery-status"], capture_output=True, text=True).stdout.strip()
    if name == "check_storage_usage":
        return subprocess.run(["df", "-h"], capture_output=True, text=True).stdout.strip()
    if name == "send_notification":
        subprocess.run(["termux-notification", "--title", args.get("title", "AI"), "--content", args.get("content", "")])
        return "Notification sent."
    if name == "send_sms":
        num = "".join(c for c in args.get("phone_number", "") if c.isdigit() or c == "+")
        if len(num) < 7:
            return "Invalid phone number."
        subprocess.run(["termux-sms-send", "-n", num, args.get("message", "")])
        return f"SMS sent to {num}."
    return "Unknown tool."

TOOLS = [{"function_declarations": [
    {"name": "check_battery_status", "description": "Get device battery status."},
    {"name": "check_storage_usage", "description": "Check free disk space."},
    {"name": "send_notification", "description": "Show Android notification.",
     "parameters": {"type": "OBJECT", "properties": {"title": {"type": "STRING"}, "content": {"type": "STRING"}}, "required": ["title", "content"]}},
    {"name": "send_sms", "description": "Send SMS after confirmation.",
     "parameters": {"type": "OBJECT", "properties": {"phone_number": {"type": "STRING"}, "message": {"type": "STRING"}}, "required": ["phone_number", "message"]}}
]}]

def call_gemini(api_key, history):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    body = {
        "system_instruction": {"parts": [{"text": "You are a concise hands-free Android voice assistant. Always read back number and message and ask confirmation before calling send_sms."}]},
        "contents": history, "tools": TOOLS, "generationConfig": {"temperature": 0.2}
    }
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())

def run_agent():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        sys.exit("Missing GEMINI_API_KEY")
    history = []
    speak_text("Listening.")
    try:
        while True:
            text = get_voice_input()
            if not text:
                time.sleep(1)
                continue
            print(f"Heard: {text}")
            if text.lower().strip(".!?") in ["exit", "quit", "stop", "goodbye"]:
                speak_text("Goodbye.")
                break
            history.append({"role": "user", "parts": [{"text": text}]})
            set_status("Thinking...")
            res = call_gemini(api_key, history)
            msg = res["candidates"][0]["content"]
            history.append(msg)
            part = msg["parts"][0]
            if "functionCall" in part:
                fc = part["functionCall"]
                out = run_tool(fc["name"], fc.get("args", {}))
                history.append({"role": "user", "parts": [{"functionResponse": {"name": fc["name"], "response": {"result": out}}}]})
                res = call_gemini(api_key, history)
                msg = res["candidates"][0]["content"]
                history.append(msg)
                part = msg["parts"][0]
            reply = part.get("text", "").strip()
            print(f"AI: {reply}")
            speak_text(reply)
    except urllib.error.HTTPError as e:
        print("API Error:", e.read().decode())
    finally:
        subprocess.run(["termux-notification-remove", "voice_ai"])

if __name__ == "__main__":
    run_agent()
