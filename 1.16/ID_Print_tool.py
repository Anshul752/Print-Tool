import tkinter as tk
from tkinter import messagebox
import license_manager,threading,time

# === License Window ===
def show_license_window():
    def center_window(win, width, height):
        screen_width = win.winfo_screenwidth()
        
        screen_height = win.winfo_screenheight()
        x = int((screen_width / 2) - (width / 2))
        y = int((screen_height / 2) - (height / 2))
        win.geometry(f'{width}x{height}+{x}+{y}')
 
    license_window = tk.Tk()
    license_window.title("ID Print Tool - License Activation")
    license_window.configure(bg='#DDEEFF')
    center_window(license_window, 400, 300)
    license_window.resizable(False, False)
 
    label_font = ("Arial", 11, "bold")
    button_font = ("Arial", 10, "bold")
    button_style = {"width": 30, "height": 2, "font": button_font, "bg": "#4CAF50",
                    "fg": "white", "activebackground": "#45a049", "bd": 0, "relief": "ridge"}
 
    pc_id_label = tk.Label(license_window, text=f"Your PC ID: {license_manager.get_pc_identifier()}", font=label_font, bg='#DDEEFF')
    pc_id_label.pack(pady=5)
    tk.Label(license_window, text="Enter License Key:", font=label_font, bg='#DDEEFF').pack(pady=(15, 5))
    entry = tk.Entry(license_window, width=35, font=("Arial", 10))
    entry.pack(pady=5)
 
    animation_running = False
 
    def start_animation():
        nonlocal animation_running
        animation_running = True
 
        def animate():
            positions = ["●     ", " ●    ", "  ●   ", "   ●  ", "    ● ", "     ●", "    ● ", "   ●  ", "  ●   ", " ●    "]
            index = 0
            while animation_running:
                animation_label.config(text=f"Connecting {positions[index % len(positions)]}")
                index += 1
                time.sleep(0.1)
 
            animation_label.config(text="")  # Clear after stop
 
        threading.Thread(target=animate, daemon=True).start()
 
    def stop_animation():
        nonlocal animation_running
        animation_running = False
 
    def run_task_with_animation(task_function):
        start_animation()
        def wrapper():
            try:
                task_function()
            finally:
                stop_animation()
        threading.Thread(target=wrapper, daemon=True).start()
 
    def activate():
        def task():
            try:
                key = entry.get().strip()
                result = license_manager.activate_license(key)
                if result is True:
                    def on_success():
                        messagebox.showinfo("Success", "License activated successfully!")
                        license_window.destroy()
                        start_app()
                    license_window.after(0, on_success)
    
                elif result == "invalid":
                    license_window.after(0, lambda: messagebox.showerror("Invalid", "License key is invalid or already used!"))
    
                elif result == "connection_error":
                    license_window.after(0, lambda: messagebox.showerror("Connection Error", "Could not reach license server. Please check your internet connection and try again."))
            except Exception as e:
                print(f"[Activate Error] {e}")
                license_window.after(0, lambda: messagebox.showerror("Error", "An unexpected error occurred."))
        run_task_with_animation(task)
    
    def start_trial():
        def task():
            try:
                result = license_manager.start_trial()
                if result == "started":
                    def on_trial_success():
                        messagebox.showinfo("Trial", "Welcome To ID Print Tool your 30-days free trial started now !")
                        license_window.destroy()
                        start_app()
                    license_window.after(0, on_trial_success)
    
                elif result == "server_blocked":
                    license_window.after(0, lambda: messagebox.showerror("Trial Blocked", "Trial already used on this PC. Please activate license."))
    
                elif result == "connection_error":
                    license_window.after(0, lambda: messagebox.showerror("Connection Error", "Could not reach license server. Please check your internet connection and try again."))
    
                else:
                    license_window.after(0, lambda: messagebox.showerror("Error", "Could not reach license server. Please try again later.!"))
            except Exception as e:
                print(f"[Trial Error] {e}")
                license_window.after(0, lambda: messagebox.showerror("Error", "An unexpected error occurred."))
        run_task_with_animation(task)
 
    tk.Button(license_window, text="Activate License", command=activate, **button_style).pack(pady=7)
    trial_allowed = not license_manager.is_trial_active() and not license_manager.is_activated()
    if trial_allowed:
        tk.Button(license_window, text="Start 30-Day Free Trial", command=start_trial, **button_style).pack(pady=5)
    # === Animation Label ===
    animation_label = tk.Label(license_window, text="", font=("Arial", 11, "bold"), bg='#DDEEFF', fg="#333")
    animation_label.pack(pady=10)
 
    license_window.mainloop()
    
license_manager.check_and_delete_license_file()
license_manager.update_license_status_on_server()

def start_app():
    import ID_Print_tool_Onlinewala  # Your main app module
 
# === License Check Flow ===
status = license_manager.is_license_valid()
if status == "licensed":
    start_app()
elif status and status.startswith("trial_"):
    start_app()
elif status == "expired":
    messagebox.showwarning("Trial Expired", "Trial expired. Please activate license to continue.")
    show_license_window()
elif status == "blocked":
    messagebox.showerror("Blocked", "System date rollback detected. Please correct system date.")
    show_license_window()
else:
    show_license_window()