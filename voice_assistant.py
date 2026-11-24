import os, re, json, time, datetime, subprocess, urllib.request

API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={API_KEY}"
NOTES_DIR = os.path.expanduser("~/termux-ai/notes")
PID = os.getpid()

def run_cmd(cmd, inp=None, timeout=15):
    try:
        r = subprocess.run(cmd, input=inp, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except subprocess.TimeoutExpired:
        return "ERROR: TIMEOUT"
    except Exception as e:
        return f"ERROR: {e}"

def set_status(msg):
    stop = f"kill -9 {PID}; termux-notification-remove voice_ai; termux-wake-unlock"
    try:
        subprocess.Popen(["termux-notification", "--id", "voice_ai", "--ongoing",
                          "--title", "Gemini Voice AI", "--content", msg,
                          "--button1", "Stop", "--button1-action", stop],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

def speak(text):
    clean = re.sub(r"[*#_`\[\]]", "", text).strip()
    if clean:
        set_status("Speaking...")
        run_cmd(["termux-tts-speak"], inp=clean, timeout=60)

def run_tool(name, args):
    today = os.path.join(NOTES_DIR, f"{datetime.date.today().isoformat()}.md")
    if name == "save_note":
        os.makedirs(NOTES_DIR, exist_ok=True)
        ts = datetime.datetime.now().strftime("%H:%M")
        with open(today, "a", encoding="utf-8") as f:
            f.write(f"- **[{ts}]** {args.get('note', '').strip()}\n")
        return f"Saved to {os.path.basename(today)}."
    if name == "read_notes":
        return open(today, encoding="utf-8").read() if os.path.exists(today) else "No notes for today."
    if name == "summarize_notes":
        if not os.path.exists(today):
            return "No notes found for today."
        raw = open(today, encoding="utf-8").read().strip()
        return f"Notes:\n{raw}\n\nInstruction: Summarize these concisely, call set_clipboard with the summary, then speak the summary."
    if name == "get_battery_status":
        return run_cmd(["termux-battery-status"], timeout=8)
    if name == "get_clipboard":
        return run_cmd(["termux-clipboard-get"], timeout=8)
    if name == "set_clipboard":
        run_cmd(["termux-clipboard-set", args.get("text", "")], timeout=8)
        return "Copied to clipboard."
    return "Unsupported tool."

TOOLS = [{"function_declarations": [
    {"name": "save_note", "description": "Save a voice note to today's dated markdown file.",
     "parameters": {"type": "OBJECT", "properties": {"note": {"type": "STRING"}}, "required": ["note"]}},
    {"name": "read_notes", "description": "Read all voice notes saved today."},
    {"name": "summarize_notes", "description": "Summarize today's saved markdown notes and copy the summary to the clipboard."},
    {"name": "get_battery_status", "description": "Get phone battery percentage and charging status."},
    {"name": "get_clipboard", "description": "Read current text from Android clipboard."},
    {"name": "set_clipboard", "description": "Copy text to Android clipboard.",
     "parameters": {"type": "OBJECT", "properties": {"text": {"type": "STRING"}}, "required": ["text"]}}
]}]

def ask_gemini(history):
    body = {"system_instruction": {"parts": [{"text": "Concise voice assistant. Plain text only, no markdown."}]},
            "contents": history, "tools": TOOLS}
    req = urllib.request.Request(URL, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=25) as resp:
        data = json.loads(resp.read().decode())
    parts = data["candidates"][0]["content"]["parts"]
    history.append({"role": "model", "parts": parts})
    for p in parts:
        if "functionCall" in p:
            fc = p["functionCall"]
            res = run_tool(fc["name"], fc.get("args", {}))
            history.append({"role": "user", "parts": [{"functionResponse": {"name": fc["name"], "response": {"result": res}}}]})
            return ask_gemini(history)
    return " ".join(p.get("text", "") for p in parts).strip()

def main():
    if not API_KEY:
        speak("Gemini API key is missing.")
        return
    history, errs = [], 0
    speak("Assistant ready.")
    try:
        while True:
            set_status("Listening...")
            txt = run_cmd(["termux-speech-to-text"], timeout=25)
            if not txt or txt.startswith("ERROR:"):
                if "NO_MATCH" not in txt and "TIMEOUT" not in txt:
                    errs += 1
                    if errs >= 5:
                        speak("Microphone error. Stopping.")
                        break
                time.sleep(0.5)
                continue
            errs = 0
            if txt.lower() in ("stop assistant", "exit assistant", "goodbye"):
                speak("Goodbye.")
                break
            set_status("Thinking...")
            history.append({"role": "user", "parts": [{"text": txt}]})
            history = history[-10:]
            try:
                speak(ask_gemini(history))
            except Exception as e:
                print("API error:", e, flush=True)
                speak("Connection error. Try again.")
    finally:
        run_cmd(["termux-notification-remove", "voice_ai"], timeout=5)

if __name__ == "__main__":
    main()
