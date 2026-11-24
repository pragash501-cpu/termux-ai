import os, json, urllib.request, urllib.error

API_KEY = os.getenv("GCP_API_KEY")
URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={API_KEY}"
history = []

def ask_gemini(prompt):
    history.append({"role": "user", "parts": [{"text": prompt}]})
    data = json.dumps({"contents": history}).encode("utf-8")
    req = urllib.request.Request(URL, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            body = json.loads(res.read().decode("utf-8"))
            reply = body["candidates"][0]["content"]["parts"][0]["text"]
            history.append({"role": "model", "parts": [{"text": reply}]})
            return reply
    except urllib.error.HTTPError as e:
        history.pop()
        return f"HTTP Error {e.code}: {e.read().decode('utf-8')}"
    except Exception as e:
        history.pop()
        return f"Error: {e}"

print("Gemini Text Assistant ready. Type 'exit' to quit.\n")
while True:
    try:
        user_input = input("You: ").strip()
        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            break
        print(f"\nAI: {ask_gemini(user_input)}\n")
    except (KeyboardInterrupt, EOFError):
        break
