import tkinter as tk
import pyautogui
 
def update_mouse_position():
    x, y = pyautogui.position()
    label.config(text=f"X: {x}, Y: {y}")
    root.after(100, update_mouse_position)  # Update every 100ms
 
def capture_position():
    x, y = pyautogui.position()
    captured_label.config(text=f"Captured Position: X={x}, Y={y}")
 
root = tk.Tk()
root.title("Mouse Position Capture")
root.geometry("300x150")
 
label = tk.Label(root, text="X: 0, Y: 0", font=("Helvetica", 14))
label.pack(pady=10)
 
capture_button = tk.Button(root, text="Capture Position", command=capture_position)
capture_button.pack(pady=10)
 
captured_label = tk.Label(root, text="Captured Position: None", font=("Helvetica", 12))
captured_label.pack(pady=10)
 
update_mouse_position()
root.mainloop()