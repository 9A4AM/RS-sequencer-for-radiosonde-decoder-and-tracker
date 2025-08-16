#-------------------------------------------------------------------------------
# Name:        Radiosonde sequencer for Radiosonde decoder and tracker by 9A4AM
# Purpose:
#
# Author:      9A4AM
#
# Created:     16.08.2025
# Copyright:   (c) 9A4AM 2025
# Licence:     <your licence>
#-------------------------------------------------------------------------------

import tkinter as tk
from tkinter import ttk
import configparser
import socket
import json
import threading
import time


# ------------------- send_command -------------------
def send_command(freq=None, tip=None, restart=False):
    print(f"[DEBUG send_command] freq={freq!r}, tip={tip!r}, restart={restart}")
    data = {}
    if freq:
        data["freq"] = freq
    if tip:
        # Normalize RS41 and DFM variants
        if tip.startswith("RS41"):
            data["type"] = "RS41"
        elif tip in ("DFM09", "DFM17", "DFM06", "PS15"):
            data["type"] = "DFM"
        else:
            data["type"] = tip
    if restart:
        data["restart"] = True
    try:
        s = socket.socket()
        s.connect(("127.0.0.1", 65432))
        s.sendall(json.dumps(data).encode())
        response = s.recv(1024).decode().strip()
        print("[CLIENT] Response:", response)
        s.close()
    except Exception as e:
        print("[CLIENT] Failed to send:", e)


# ------------------- GUI + Sequencer -------------------
class SequencerApp:
    def __init__(self, root, config_file="config.ini"):
        self.root = root
        self.root.title("Radiosonde sequencer for Radiosonde decoder and tracker by 9A4AM")
        self.root.configure(bg="black")

        # Load config
        self.config = configparser.ConfigParser()
        self.config.read(config_file)

        self.hold_time = int(self.config.get("SETTINGS", "hold_time", fallback="30"))
        freq_raw = self.config.get("SETTINGS", "frequencies", fallback="")

        # Parse frequencies and types
        self.freq_data = []
        for entry in freq_raw.split(","):
            entry = entry.strip()
            if ";" in entry:
                freq, tip = entry.split(";", 1)
                self.freq_data.append((freq.strip(), tip.strip()))
            elif entry:
                self.freq_data.append((entry.strip(), "RS41"))  # default type

        self.current_index = 0
        self.running = False
        self.remaining = self.hold_time

        # --- GUI ---
        style = ttk.Style()
        style.configure("Dark.TLabel", foreground="gold", background="black", font=("Arial", 14))
        style.configure("Dark.TButton", foreground="black", background="black", font=("Arial", 14))

        ttk.Label(root, text="Frequencies:", style="Dark.TLabel").pack(pady=5)

        self.freq_list = tk.Listbox(root, bg="black", fg="gold", font=("Courier", 12), selectbackground="gray25")
        for f, t in self.freq_data:
            self.freq_list.insert(tk.END, f"{f} ; {t}")
        self.freq_list.pack(pady=5, fill=tk.X)

        self.current_label = ttk.Label(root, text="Current: ---", style="Dark.TLabel")
        self.current_label.pack(pady=5)

        self.time_label = ttk.Label(root, text=f"Hold time: {self.hold_time} s", style="Dark.TLabel")
        self.time_label.pack(pady=5)

        self.countdown_label = ttk.Label(root, text="Remaining: --- s", style="Dark.TLabel")
        self.countdown_label.pack(pady=5)

        self.start_btn = ttk.Button(root, text="START", command=self.start_seq, style="Dark.TButton")
        self.start_btn.pack(side=tk.LEFT, padx=20, pady=10)

        self.stop_btn = ttk.Button(root, text="STOP", command=self.stop_seq, style="Dark.TButton")
        self.stop_btn.pack(side=tk.RIGHT, padx=20, pady=10)

    def start_seq(self):
        if not self.running:
            self.running = True
            threading.Thread(target=self.run_seq, daemon=True).start()

    def stop_seq(self):
        self.running = False

    def run_seq(self):
        while self.running and self.freq_data:
            freq, tip = self.freq_data[self.current_index]
            self.current_label.config(text=f"Current: {freq} ; {tip}")
            self.freq_list.selection_clear(0, tk.END)
            self.freq_list.selection_set(self.current_index)
            self.freq_list.activate(self.current_index)

            # Send to decoder
            send_command(freq=freq, tip=tip, restart=True)

            # Countdown
            self.remaining = self.hold_time
            while self.remaining > 0 and self.running:
                self.countdown_label.config(text=f"Remaining: {self.remaining} s")
                time.sleep(1)
                self.remaining -= 1

            self.current_index = (self.current_index + 1) % len(self.freq_data)


# ------------------- main -------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = SequencerApp(root)
    root.mainloop()

