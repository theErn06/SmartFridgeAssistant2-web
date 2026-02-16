import subprocess
import time
import sys
import os

def main():
    print("==================================================")
    print("      👑 STARTING KING JARVIS SYSTEM 👑")
    print("==================================================")

    processes = []
    
    # 1. Start the Web Server (backend for website)
    print(">> Launching Web Server (jarvis_server.py)...")
    p1 = subprocess.Popen([sys.executable, "jarvis_server.py"])
    processes.append(p1)
    time.sleep(2) 

    # 2. Start the Local Voice Assistant
    print(">> Launching Voice Assistant (fridge_assistant2_5.py)...")
    p2 = subprocess.Popen([sys.executable, "fridge_assistant2_5.py"])
    processes.append(p2)

    # 3. Start the Watcher
    print(">> Launching Google Sync (watcher2.py)...")
    p3 = subprocess.Popen([sys.executable, "watcher2.py"])
    processes.append(p3)

    print("\n✅ All systems operational.")
    print("   - Speak to PC Mic OR Type in Website.")
    print("PRESS CTRL+C TO STOP ALL SYSTEMS\n")

    try:
        while True:
            time.sleep(1)
            # Restart if crashed
            if p1.poll() is not None:
                print("⚠️ Web Server died! Restarting...")
                p1 = subprocess.Popen([sys.executable, "jarvis_server.py"])
                processes[0] = p1
            if p2.poll() is not None:
                print("⚠️ Voice Assistant died! Restarting...")
                p2 = subprocess.Popen([sys.executable, "fridge_assistant2_5.py"])
                processes[1] = p2
            if p3.poll() is not None:
                print("⚠️ Watcher died! Restarting...")
                p3 = subprocess.Popen([sys.executable, "watcher2.py"])
                processes[2] = p3

    except KeyboardInterrupt:
        print("\n🛑 Stopping all systems...")
        for p in processes:
            p.terminate()
        print("Goodbye.")

if __name__ == "__main__":
    main()