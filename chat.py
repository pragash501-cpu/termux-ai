import os, sys, json, urllib.request, urllib.error

MODEL = "gemini-3.5-flash-lite"

def ask_gemini(api_key, history):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={api_key}"
    body = {
        "system_instruction": {"parts": [{"text": "You are a helpful, concise Termux personal AI assistant."}]},
        "contents": history
    }
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())["candidates"][0]["content"]

def main():
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        sys.exit("Error: GEMINI_API_KEY is not set. Run: export GEMINI_API_KEY='your_key'")
    history = []
    print(f"Gemini Terminal Chat ({MODEL}) — type 'exit' to quit\n" + "-" * 50)
    while True:
        try:
            prompt = input("\nYou > ").strip()
            if not prompt:
                continue
            if prompt.lower() in ["exit", "quit"]:
                break
            history.append({"role": "user", "parts": [{"text": prompt}]})
            reply = ask_gemini(api_key, history)
            history.append(reply)
            print(f"\nGemini > {reply['parts'][0]['text'].strip()}")
        except urllib.error.HTTPError as e:
            print(f"\nAPI Error ({e.code}): {e.read().decode()}")
            history.pop()
        except (KeyboardInterrupt, EOFError):
            break

if __name__ == "__main__":
    main()
