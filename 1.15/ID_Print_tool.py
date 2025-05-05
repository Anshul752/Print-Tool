# main.py
import tkinter as tk
from tkinter import messagebox
import license_manager
 
def show_license_window():
    # Center window function
    def center_window(win, width, height):
        screen_width = win.winfo_screenwidth()
        screen_height = win.winfo_screenheight()
        x = int((screen_width / 2) - (width / 2))
        y = int((screen_height / 2) - (height / 2))
        win.geometry(f'{width}x{height}+{x}+{y}')
 
    license_window = tk.Tk()
    license_window.title("ID Print Tool - License Activation")
    license_window.configure(bg='#DDEEFF')
    window_width = 400
    window_height = 210
    center_window(license_window, window_width, window_height)
    license_window.resizable(False, False)
 
    # Fonts
    label_font = ("Arial", 11, "bold")
    button_font = ("Arial", 10, "bold")
 
    # Label
    tk.Label(license_window, text="Enter License Key:", font=label_font, bg='#DDEEFF').pack(pady=(15, 5))
 
    # Entry
    entry = tk.Entry(license_window, width=35, font=("Arial", 10))
    entry.pack(pady=5)
 
    # Buttons
    button_style = {"width": 30,"height": 2,"font": button_font,"bg": "#4CAF50","fg": "white","activebackground": "#45a049","bd": 0,"relief": "ridge"}
 
    def activate():
        key = entry.get().strip()
        if license_manager.activate_license(key):
            messagebox.showinfo("Success", "License activated successfully!")
            license_window.destroy()
            start_app()
        else:
            messagebox.showerror("Invalid", "License key is invalid!")
 
    def start_trial():
        license_manager.start_trial()
        messagebox.showinfo("Trial", "3-day trial started!")
        license_window.destroy()
        start_app()
 
    tk.Button(license_window, text="Activate License", command=activate, **button_style).pack(pady=7)
    tk.Button(license_window, text="Start 3-Days Free Trial", command=start_trial, **button_style).pack(pady=5)
 
    license_window.mainloop()
 
def start_app():
    import ID_Print_tool_Onlinewala
 
# ==== License Check Flow ====

status = license_manager.is_license_valid()
if status == True or status == "trial":
    start_app()
else:
    show_license_window()

 