import subprocess
import time
import sys
import os
import re
import socket

# ================= CONFIG =================
JS_FILE = "script.js" 
SERVER_SCRIPT = "jarvis_server.py"
ASSISTANT_SCRIPT = "fridge_assistant2_5.py"
WATCHER_SCRIPT = "watcher2.py"

def get_local_ip():
    """Finds the actual Wi-Fi IP address of this PC"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Connect to a public DNS (doesn't send data) to find local route
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def update_js_url(local_ip):
    """Updates script.js with the correct IP automatically"""
    # FORCE PORT 5000 HERE
    new_url = f"http://{local_ip}:5000/chat"
    
    try:
        with open(JS_FILE, "r", encoding="utf-8") as f:
            content = f.read()

        # Regex to replace the JARVIS_URL line
        # This looks for: const JARVIS_URL = '...'; and replaces it
        new_content = re.sub(
            r"const JARVIS_URL = ['.\"].*['\"];", 
            f"const JARVIS_URL = '{new_url}';", 
            content
        )

        with open(JS_FILE, "w", encoding="utf-8") as f:
            f.write(new_content)
        
        print(f"✅ Auto-Updated script.js -> {new_url}")
    except Exception as e:
        print(f"❌ Failed to update {JS_FILE}: {e}")

def main():
    print("==================================================")
    print("      👑 STARTING KING JARVIS SYSTEM 👑")
    print("==================================================")

    # 1. Get IP and Update JS
    my_ip = get_local_ip()
    print(f"📍 Detected PC IP: {my_ip}")
    update_js_url(my_ip)

    processes = []
    
    # 2. Start Processes
    print(">> Launching Web Server (jarvis_server.py)...")
    p1 = subprocess.Popen([sys.executable, SERVER_SCRIPT])
    processes.append(p1)
    time.sleep(1)

    print(">> Launching Voice Assistant (fridge_assistant2_5.py)...")
    p2 = subprocess.Popen([sys.executable, ASSISTANT_SCRIPT])
    processes.append(p2)

    print(">> Launching Google Sync (watcher2.py)...")
    p3 = subprocess.Popen([sys.executable, WATCHER_SCRIPT])
    processes.append(p3)

    print("\n✅ SYSTEM ONLINE.")
    print("--------------------------------------------------")
    print(f"📲 ON PHONE BROWSER, TYPE THIS EXACTLY:")
    print(f"   http://{my_ip}:5000")
    print("   (Note: Use http:// NOT https://)")
    print("--------------------------------------------------")
    print("PRESS CTRL+C TO STOP\n")

    try:
        while True:
            time.sleep(1)
            # Restart if died
            if p1.poll() is not None:
                print("⚠️ Web Server died! Restarting...")
                p1 = subprocess.Popen([sys.executable, SERVER_SCRIPT])
                processes[0] = p1
            if p2.poll() is not None:
                p2 = subprocess.Popen([sys.executable, ASSISTANT_SCRIPT])
                processes[1] = p2
            if p3.poll() is not None:
                p3 = subprocess.Popen([sys.executable, WATCHER_SCRIPT])
                processes[2] = p3

    except KeyboardInterrupt:
        print("\n🛑 Stopping...")
        for p in processes: p.terminate()
        print("Goodbye.")

if __name__ == "__main__":
    main()
