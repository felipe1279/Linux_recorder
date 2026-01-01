import tkinter as tk
from tkinter import filedialog
from pynput import keyboard, mouse
import threading
import time
import json
import os

FPS = 60
FRAME_TIME = 1 / FPS

CONTROL_COOLDOWN = 0.30  # segundos

is_recording = False
is_playing = False
current_frame = 0

frames = []
frame_events = []

lock = threading.Lock()

mouse_ctl = mouse.Controller()
key_ctl = keyboard.Controller()

# cooldown por tecla de controle
last_control_time = {
    "U": 0.0,
    "K": 0.0,
    "L": 0.0
}

root = tk.Tk()
root.title("Macro Recorder FIXED")
root.geometry("320x220")
root.attributes("-topmost", True)

label = tk.Label(root, text="U: Gravar | K: Replay | L: Sair")
label.pack(pady=10)

def status(txt, c="black"):
    root.after(0, lambda: label.config(text=txt, fg=c))

# ================= GRAVAÇÃO FRAME =================

def frame_loop():
    global current_frame

    while is_recording:
        start = time.perf_counter()

        with lock:
            frames.append({
                "frame": current_frame,
                "events": frame_events.copy()
            })
            frame_events.clear()
            current_frame += 1

        elapsed = time.perf_counter() - start
        time.sleep(max(0, FRAME_TIME - elapsed))

def record_event(ev):
    with lock:
        frame_events.append(ev)

# ================= INPUT =================

def on_key(key, pressed):
    global is_recording, is_playing, current_frame

    try:
        char = key.char.upper()
    except:
        char = None

    now = time.perf_counter()

    # ---------- TECLAS DE CONTROLE ----------
    if char in ("U", "K", "L"):
        if not pressed:
            return

        if now - last_control_time[char] < CONTROL_COOLDOWN:
            return

        last_control_time[char] = now

        # ----- U -----
        if char == "U":
            if not is_recording:
                frames.clear()
                current_frame = 0
                is_recording = True
                threading.Thread(target=frame_loop, daemon=True).start()
                status("GRAVANDO", "red")
            else:
                is_recording = False
                status(f"Gravado {len(frames)} frames", "purple")

        # ----- K -----
        elif char == "K":
            if not is_playing:
                is_playing = True
                threading.Thread(target=replay_loop, daemon=True).start()
            else:
                is_playing = False
                status("Replay parado", "orange")

        # ----- L -----
        elif char == "L":
            os._exit(0)

        return  # 🚫 nunca cai na gravação

    # ---------- TECLAS NORMAIS ----------
    if is_recording:
        record_event({
            "type": "key",
            "key": str(key),
            "pressed": pressed
        })

def on_move(x, y):
    if is_recording:
        record_event({"type": "move", "x": x, "y": y})

def on_click(x, y, button, pressed):
    if is_recording:
        record_event({
            "type": "click",
            "button": str(button),
            "pressed": pressed
        })

# ================= REPLAY (INFINITO) =================

def replay_loop():
    status("REPLAY (LOOP)", "blue")

    while is_playing:
        for frame in frames:
            if not is_playing:
                break

            start = time.perf_counter()

            for ev in frame["events"]:
                if ev["type"] == "move":
                    mouse_ctl.position = (ev["x"], ev["y"])

                elif ev["type"] == "click":
                    btn = mouse.Button.left if "left" in ev["button"] else mouse.Button.right
                    mouse_ctl.press(btn) if ev["pressed"] else mouse_ctl.release(btn)

                elif ev["type"] == "key":
                    k = ev["key"]
                    if "Key." in k:
                        key_obj = getattr(keyboard.Key, k.split(".")[1])
                    else:
                        key_obj = k.replace("'", "")
                    key_ctl.press(key_obj) if ev["pressed"] else key_ctl.release(key_obj)

            elapsed = time.perf_counter() - start
            time.sleep(max(0, FRAME_TIME - elapsed))

    status("Replay parado", "green")

# ================= SAVE / LOAD =================

def save():
    p = filedialog.asksaveasfilename(defaultextension=".json")
    if p:
        json.dump(frames, open(p, "w"))

def load():
    global frames
    p = filedialog.askopenfilename()
    if p:
        frames = json.load(open(p))
        status("Macro carregada", "blue")

tk.Button(root, text="💾 Salvar", command=save).pack(fill="x", padx=20)
tk.Button(root, text="📁 Carregar", command=load).pack(fill="x", padx=20)

mouse.Listener(on_move=on_move, on_click=on_click).start()
keyboard.Listener(
    on_press=lambda k: on_key(k, True),
    on_release=lambda k: on_key(k, False)
).start()

root.mainloop()

