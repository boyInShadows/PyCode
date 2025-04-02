import tkinter as tk
import time
import threading

# Timer duration in seconds (25 minutes)
TIMER_DURATION = 25 * 60

def start_timer():
    def countdown():
        total = TIMER_DURATION
        while total >= 0 and running[0]:
            mins, secs = divmod(total, 60)
            time_str = f"{mins:02d}:{secs:02d}"
            label.config(text=time_str)
            time.sleep(1)
            total -= 1
        if total < 0:
            label.config(text="⏰ Time's Up!")

    running[0] = True
    threading.Thread(target=countdown, daemon=True).start()

def stop_timer():
    running[0] = False
    label.config(text="Timer Stopped")

# Create the GUI window
root = tk.Tk()
root.title("25-Minute Countdown Timer")
root.geometry("300x200")

label = tk.Label(root, text="25:00", font=("Helvetica", 40))
label.pack(pady=20)

start_button = tk.Button(root, text="Start", command=start_timer)
start_button.pack(side="left", padx=20, pady=10)

stop_button = tk.Button(root, text="Stop", command=stop_timer)
stop_button.pack(side="right", padx=20, pady=10)

running = [False]  # Mutable container to control timer loop

root.mainloop()
