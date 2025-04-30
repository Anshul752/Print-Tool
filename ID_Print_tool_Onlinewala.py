import tkinter as tk
import fitz,json,os,sys,threading,requests,shutil,subprocess,time,zipfile,random,cv2
from tkinter import filedialog, Toplevel, Canvas, Scrollbar, Frame, messagebox,ttk
from PIL import Image, ImageTk,ImageDraw,ImageEnhance,ImageFont
from datetime import datetime
from io import BytesIO 
from packaging import version
import numpy as np
import pygetwindow as gw
 

doc = None  # Global variable to store the loaded document
file_path = None  # Global variable to store the file path
zoom_level = 2.0  # Default zoom level
attempts = 3  # Global variable to track the number of attempts
crop_coordinates = {}
preview_window = None  # Initialize globally
Settings = "Settings.json"  # Store all settings in this file
CROP_DATA_FILE = "crop_coordinates.json" # File path for storing crop coordinates
crop_btn = None  # Initialize crop_btn as None
current_front_image = None
current_back_image = None
front_cropped_img=None
back_cropped_img=None
apply_mode = "normal"         # "normal" or "inverted"
inverse_mask_id = None        # list of canvas rect IDs
selection_area = None
rect_id = None
current_pdf_page_index = 0
total_pdf_pages = 0
ID_CARD_SIZE = (975, 625)  # Width x Height at 300 DPI
border_size = 5
current_crop_step = 0  # 0 for front, 1 for back
prepared_id_cards = []  # Stores tuples of (card_name, front_image, back_image)
epson_photo_plus_path = r"C:\Program Files (x86)\Epson Software\PhotoPlus\EPPlusG.exe"  # <-- Your path
Print_Data_Folder = r"C:\Print_ID_Tool\Print Data" # Define Print Data folder

# URLs
VERSION_URL = "https://raw.githubusercontent.com/Anshul752/Print-Tool/main/version.txt"
ZIP_URL = "https://github.com/Anshul752/Print-Tool/releases/download/latest/dist.zip"
LOCAL_VERSION_FILE = "version.txt"
UPDATE_ZIP = "update.zip"
TMP_DIR = "update_tmp"

def get_latest_version():
    try:
        response = requests.get(VERSION_URL)
        response.raise_for_status()
        return response.text.strip()
    except:
        messagebox.showerror("Error", "Could not fetch latest version.")
        return None

def get_current_version():
    if os.path.exists(LOCAL_VERSION_FILE):
        with open(LOCAL_VERSION_FILE, "r") as f:
            return f.read().strip()
    return "1.0"

def download_zip_with_progress(progress_callback):
    try:
        response = requests.get(ZIP_URL, stream=True)
        response.raise_for_status()
        total_length = int(response.headers.get('content-length', 0))
        downloaded = 0

        with open(UPDATE_ZIP, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    percent = int((downloaded / total_length) * 100)
                    progress_callback(percent)
        return True
    except:
        messagebox.showerror("Error", "Download failed.")
        return False

def extract_and_apply_zip():
    try:
        if os.path.exists(TMP_DIR):
            shutil.rmtree(TMP_DIR)
        os.makedirs(TMP_DIR)

        with zipfile.ZipFile(UPDATE_ZIP, 'r') as zip_ref:
            zip_ref.extractall(TMP_DIR)

        extracted_path = os.path.join(TMP_DIR, "dist", "ID_Print_tool")
        current_dir = os.path.dirname(os.path.abspath(sys.executable))

        new_exe = os.path.join(extracted_path, "ID_Print_tool.exe")
        old_exe = os.path.join(current_dir, "ID_Print_tool.exe")
        backup_exe = os.path.join(current_dir, "ID_Print_tool_old.exe")
        new_internal = os.path.join(extracted_path, "_internal")
        old_internal = os.path.join(current_dir, "_internal")
        version_file_path = os.path.join(current_dir, LOCAL_VERSION_FILE)
        latest_version = get_latest_version()

        # Write batch updater
        updater_bat = os.path.join(TMP_DIR, "updater.bat")
        with open(updater_bat, "w") as f:
            f.write(f"""@echo off
timeout /t 1 > NUL
taskkill /f /im ID_Print_tool.exe > NUL 2>&1
timeout /t 1 > NUL

REM Backup old exe
rename "{old_exe}" "ID_Print_tool_old.exe"

REM Copy new exe
xcopy "{new_exe}" "{current_dir}" /Y

REM Replace internal folder
rmdir /s /q "{old_internal}"
xcopy "{new_internal}" "{old_internal}" /E /I /Y

REM Write version file
echo {latest_version} > "{version_file_path}"

REM Delete log.txt if exists
if exist "{os.path.join(current_dir, 'log.txt')}" del /f /q "{os.path.join(current_dir, 'log.txt')}"

REM Delete downloaded zip
del "{UPDATE_ZIP}"

REM Start the updated app
start "" "{os.path.join(current_dir, 'ID_Print_tool.exe')}"
exit
""")
        subprocess.Popen(['cmd', '/c', updater_bat], shell=True)
        sys.exit()

    except Exception as e:
        messagebox.showerror("Update Error", f"Update failed:\n\n{e}")

def check_for_updates(silent=True):

    def run_update():
        current = get_current_version()
        latest = get_latest_version()

        if latest and version.parse(latest) > version.parse(current):
            # Always show update prompt if there's a new version
            if messagebox.askyesno("Update Available", f"New version ({latest}) available. Update now?"):
                progress_bar.grid()
                progress_label.grid()
                progress_bar["value"] = 0

                def update_progress(val):
                    progress_bar["value"] = val
                    progress_label.config(text=f"Downloading... {val}%")
                    root.update_idletasks()

                if download_zip_with_progress(update_progress):
                    progress_label.config(text="Download complete. Installing...")
                    extract_and_apply_zip()
        else:
            # Only show "up to date" if not silent
            if not silent:
                messagebox.showinfo("Up to Date", "You already have the latest version.")
            # Silent mode does not show any message when no update is available

    threading.Thread(target=run_update).start()

def load_buttons():
    default_buttons = [
        ("Aadhar Card", "#17A2B8"),   # Blue
        ("PAN Card", "#28A745"),      # Green
        ("Voter Card", "#DC3545"),    # Red
        ("Ayushman Card", "#FBA518"), # Yellow
        ("E-Shram Card", "#17A2B8"),  # Blue
        ("Test-1", "#28A745"),        # Green
        ("Test-2", "#DC3545"),        # Red
        ("Test-3", "#6F42C1"),        # Purple
        ("Test-4", "#FD7E14"),        # Orange
        ("Test-5", "#20C997"),        # Teal
    ]

    if os.path.exists(Settings):
        with open(Settings, "r") as file:
            try:
                data = json.load(file)
                return (
                    data.get("buttons", default_buttons), 
                    data.get("Reverse_state", False), 
                    data.get("Mirror_state", False)   # ✅ Load Mirror state properly
                )
            except json.JSONDecodeError:
                return default_buttons, False, False
    else:
        return default_buttons, False, False

# Save button names and Reverse state to file
def save_buttons(buttons, reverse_state, mirror_state):
    """Save button names, Reverse state, and Mirror state to JSON."""
    data = {
        "buttons": buttons,
        "Reverse_state": reverse_state,
        "Mirror_state": mirror_state  # ✅ Ensure Mirror state is saved
    }
    with open(Settings, "w") as file:
        json.dump(data, file, indent=4)

# Function to save coordinates to a JSON file
def save_coordinates_to_json(card_name, coordinates):
    """ Save or overwrite the crop coordinates to a JSON file. """
    try:
        # Load existing coordinates from the JSON file (if it exists)
        try:
            with open("crop_coordinates.json", "r") as json_file:
                crop_coordinates = json.load(json_file)
        except FileNotFoundError:
            crop_coordinates = {}

        # Overwrite the coordinates for the given card_name
        crop_coordinates[card_name] = [coordinates]

        # Save the updated coordinates back to the JSON file
        with open("crop_coordinates.json", "w") as json_file:
            json.dump(crop_coordinates, json_file, indent=4)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save coordinates to JSON: {str(e)}")

def load_crop_coordinates():
    """ Load crop coordinates from the JSON file if it exists. """
    try:
        with open("crop_coordinates.json", "r") as json_file:
            return json.load(json_file)
    except FileNotFoundError:
        return {}  # Return an empty dictionary if file doesn't exist

def crop_image(card_name):
    global front_crop, back_crop, img, img_tk, canvas
    global front_crop_selected, file_path, doc, current_pdf_page_index, total_pdf_pages

    front_crop = None
    back_crop = None
    front_crop_selected = True

    if not file_path:
        messagebox.showerror("Error", "No file selected.")
        return

    if file_path.endswith(".pdf"):
        try:
            if doc is None:
                raise Exception("PDF not loaded or encrypted.")
            
            current_pdf_page_index = 0
            total_pdf_pages = len(doc)
            show_pdf_page(current_pdf_page_index)  # Show first page

        except Exception as e:
            messagebox.showerror("Error", f"Failed to open PDF: {str(e)}")
    else:
        try:
            img = Image.open(file_path)
            img = img.resize((int(img.width * zoom_level), int(img.height * zoom_level)))
            img_tk = ImageTk.PhotoImage(img)

            canvas.delete("all")
            canvas.create_image(0, 0, anchor="nw", image=img_tk)
            canvas.config(scrollregion=canvas.bbox("all"))

        except Exception as e:
            messagebox.showerror("Error", f"Failed to open image: {str(e)}")

    img_tk = ImageTk.PhotoImage(img)
    canvas.delete("all")
    canvas.create_image(0, 0, anchor="nw", image=img_tk)
    canvas.config(scrollregion=canvas.bbox("all"))

    if total_pdf_pages > 1:
        prev_btn.pack(side="top", padx=10, pady=10, fill="x")
        next_btn.pack(side="top", padx=10, pady=10, fill="x")
        page_label.pack(side="top", padx=10, pady=10, fill="x")
    else:
        pass

    # Load saved coordinates if available
    crop_coordinates = load_crop_coordinates()
    if card_name in crop_coordinates:
        front_coords = crop_coordinates[card_name][0].get("front")
        back_coords = crop_coordinates[card_name][0].get("back")
        
        if front_coords and back_coords:
            crop_and_display_images(front_coords, back_coords, card_name)
            return

    # Manual cropping instructions
    instructions = tk.Label(canvas, text=f"Select {card_name} front crop area", bg="white", font=("Arial", 12))
    instructions.place(x=10, y=10)
    messagebox.showinfo("Information", f"✂️ Crop front image of {card_name}")

    if crop_btn:
        crop_btn.pack_forget()

    def on_canvas_click(event):
        global front_crop_selected, front_crop, back_crop

        canvas_x, canvas_y = canvas.canvasx(event.x), canvas.canvasy(event.y)
        x1, y1 = canvas_x, canvas_y
        x2, y2 = x1, y1

        def on_drag(event):
            nonlocal x2, y2
            canvas_x, canvas_y = canvas.canvasx(event.x), canvas.canvasy(event.y)
            x2, y2 = canvas_x, canvas_y

            if front_crop_selected:
                canvas.delete("front_rect")
                canvas.create_rectangle(x1, y1, x2, y2, outline="red", width=2, tags="front_rect")
            else:
                canvas.delete("back_rect")
                canvas.create_rectangle(x1, y1, x2, y2, outline="blue", width=2, tags="back_rect")

        def on_release(event):
            global front_crop, back_crop, front_crop_selected

            x_end, y_end = canvas.canvasx(event.x), canvas.canvasy(event.y)
            crop_area = (min(x1, x_end), min(y1, y_end), max(x1, x_end), max(y1, y_end))

            if front_crop_selected:
                front_crop = crop_area
                front_crop_selected = False
                instructions.config(text=f"Select {card_name} back crop area")
                messagebox.showinfo("Information", f"✂️ Crop Back image of {card_name}.")
            else:
                back_crop = crop_area
                if instructions.winfo_exists():
                    instructions.destroy()

            canvas.unbind("<ButtonRelease-1>")
            canvas.unbind("<B1-Motion>")

        canvas.bind("<B1-Motion>", on_drag)
        canvas.bind("<ButtonRelease-1>", on_release)

    canvas.bind("<Button-1>", on_canvas_click)

def crop_and_display_images(front_crop, back_crop, card_name):
    """ Crop the selected areas (front and back) and display both cropped images on the canvas. """
    global img, canvas, front_image_box, back_image_box, preview_window

    if img is None:
        messagebox.showerror("Error", "No image loaded.")
        return

    if not front_crop or not back_crop:
        messagebox.showerror("Error", "Both front and back areas must be selected.")
        return

    # Crop images
    front_img = img.crop(tuple(front_crop))
    back_img = img.crop(tuple(back_crop))

    # Save crop coordinates
    save_coordinates_to_json(card_name, {"front": front_crop, "back": back_crop})

    # Create PhotoImage to keep them alive
    front_img_tk = ImageTk.PhotoImage(front_img)
    back_img_tk = ImageTk.PhotoImage(back_img)

    # Safely delete canvas content
    try:
        if canvas and canvas.winfo_exists():
            canvas.delete("all")
    except Exception as e:
        print(f"[Warning] Canvas not accessible: {e}")

    # Safely destroy preview window
    try:
        if preview_window and preview_window.winfo_exists():
            preview_window.destroy()
    except Exception as e:
        print(f"[Warning] Preview window already destroyed: {e}")
    preview_window = None

    # Show cropped images in the image boxes
    front_image_box.config(image=front_img_tk)
    back_image_box.config(image=back_img_tk)

    # Keep reference to prevent garbage collection
    canvas.front_img_tk = front_img_tk
    canvas.back_img_tk = back_img_tk

    # Update main display with cropped images
    update_images_to_boxes(front_img, back_img)

    # Show main window again
    root.deiconify()

    if is_multi_card_mode.get():
        # 🔽 Ask for editing only in Multi Card Mode
        ask_to_edit_then_continue(card_name, front_img, back_img)
    else:
        pass

def ask_to_edit_then_continue(card_name, front_img, back_img):
    edit_now = messagebox.askyesno("Edit Image", "Do you want to edit this ID card before saving?")
    if edit_now:
        def after_edit_callback(edited_front, edited_back):
            # After edit, continue with preview/confirm step
            show_crop_preview_and_confirm(card_name, edited_front, edited_back)

        # Open the edit window and provide a callback
        open_edit_image_window(front_img, back_img, callback=after_edit_callback)
    else:
        show_crop_preview_and_confirm(card_name, front_img, back_img)

def show_crop_preview_and_confirm(card_name, front_img, back_img):
    prepared_id_cards.append({
        "name": card_name,
        "front": front_img.copy(),
        "back": back_img.copy()
    })

    if is_multi_card_mode.get():
        # In multi mode, skip popup and just ask for next
        ask_to_add_more()
    else:
        # In single mode, directly go to print
        show_multi_print_preview()

def ask_to_add_more():
    if not is_multi_card_mode.get():
        # Single Card Mode: directly show print preview
        show_multi_print_preview()
        return

    # Check if the number of prepared cards is 5 or more
    if len(prepared_id_cards) >= 5:
        # Already have 5 cards, skip asking and go to print
        messagebox.showinfo("Limit Reached", f"Maximum of 5 ID cards reached.\n{len(prepared_id_cards)} / 5 cards prepared.")
        show_multi_print_preview()
        return

    # Show the current card count with a counter (e.g., 3 / 5)
    card_counter = f"{len(prepared_id_cards)} / 5 cards prepared"
    add_more = messagebox.askyesno("Add Another", f"Do you want to prepare another ID card?\n{card_counter}")
    
    if add_more:
        upload_doc()
    else:
        show_multi_print_preview()

def toggle_mode():
    """Toggle between single card and multi-card mode."""
    if is_multi_card_mode.get():
        print("Multi-Card Mode Activated")
    else:
        print("Single-Card Mode Activated")
        
def show_multi_print_preview():
    if not is_multi_card_mode.get():
        return

    if not prepared_id_cards:
        messagebox.showinfo("No Cards", "No ID cards to preview.")
        return

    preview_win = tk.Toplevel(root)
    preview_win.title("Final Print Preview")
    preview_win.configure(bg="#DDEEFF")

    canvas = tk.Canvas(preview_win)
    canvas.pack()

    card_frames = []

    def redraw():
        for widget in canvas.winfo_children():
            widget.destroy()

        cols_per_row = 5  # Show 3 cards per row

        for idx, card in enumerate(prepared_id_cards):
            row = idx // cols_per_row
            col = idx % cols_per_row

            frame = tk.Frame(canvas, bd=2, relief="groove", padx=5, pady=5)
            frame.grid(row=row, column=col, padx=10, pady=10)

            tk.Label(frame, text=f"{idx + 1}. {card['name']}").pack()

            fw = card['front'].resize((204, 132), Image.LANCZOS)
            bw = card['back'].resize((204, 132), Image.LANCZOS)

            front_tk = ImageTk.PhotoImage(fw)
            back_tk = ImageTk.PhotoImage(bw)

            tk.Label(frame, image=front_tk).pack()
            tk.Label(frame, image=back_tk).pack()
            frame.front_img = front_tk
            frame.back_img = back_tk

            def delete_card(idx=idx):
                prepared_id_cards.pop(idx)
                preview_win.destroy()
                show_multi_print_preview()  # Refresh the full preview

            def add_more():
                if len(prepared_id_cards) < 5:
                    preview_win.destroy()
                    upload_doc()
                else:
                    messagebox.showinfo("Limit Reached", "You cannot add more than 5 cards.")

            btn_frame = tk.Frame(frame)
            btn_frame.pack(pady=5)

            # Create Add More button and disable if 5 cards are reached
            add_more_btn = tk.Button(btn_frame,text="➕ Add More",command=add_more,font=("Arial", 10, "bold"))
            if len(prepared_id_cards) >= 5:
                add_more_btn.config(state="disabled")
            add_more_btn.pack(side="left", padx=5)

            tk.Button(btn_frame,text="❌ Delete",command=delete_card,font=("Arial", 10, "bold")).pack(side="right", padx=5)
            card_frames.append(frame)

    redraw()

    def do_final_print():
        if not prepared_id_cards:
            messagebox.showerror("Error", "No cards to print.")
            return

        # Constants
        dpi = 300
        a4_width = int(210 / 25.4 * dpi)
        a4_height = int(297 / 25.4 * dpi)
        ID_CARD_SIZE = (975, 625)  # 85mm x 55mm at 300 DPI
        card_w, card_h = ID_CARD_SIZE

        sets_per_page = 5
        gap_between_front_and_back_mm = 8
        gap_px = int(gap_between_front_and_back_mm / 25.4 * dpi)

        total_card_set_width = (card_w * 2) + gap_px
        horizontal_margin = (a4_width - total_card_set_width) // 2

        vertical_space_available = a4_height - 10  # leave top/bottom margin
        spacing_y = (vertical_space_available - (sets_per_page * card_h)) // (sets_per_page + 1)

        # Create blank white A4 image
        canvas_img = Image.new("RGB", (a4_width, a4_height), "white")
        draw = ImageDraw.Draw(canvas_img)

        def draw_border(draw, x, y, w, h, color="black", width=5):
            draw.rectangle([x, y, x + w, y + h], outline=color, width=width)

        def draw_scissor_line(draw, x_start, x_end, y, color="gray", width=1):
            # Draw dashed line
            dash_length = 20
            gap = 10
            x = x_start
            while x < x_end:
                draw.line((x, y, min(x + dash_length, x_end), y), fill=color, width=width)
                x += dash_length + gap

            # Draw scissors icon at left (symbolic)
            scissor_x = (x_start)
            icon_size = 10
            draw.ellipse((scissor_x - icon_size, y - icon_size, scissor_x, y), outline="black", width=2)
            draw.ellipse((scissor_x, y - icon_size, scissor_x + icon_size, y), outline="black", width=2)
            draw.line((scissor_x - 5, y + 1, scissor_x - 10, y + 10), fill="black", width=2)
            draw.line((scissor_x + 5, y + 1, scissor_x + 10, y + 10), fill="black", width=2)

        # Loop through 5 cards max
        for idx, card in enumerate(prepared_id_cards[:5]):
            y = spacing_y + idx * (card_h + spacing_y)
            x1 = horizontal_margin
            x2 = x1 + card_w + gap_px

            # Resize and paste
            front = card['front'].resize(ID_CARD_SIZE, Image.LANCZOS)
            back = card['back'].resize(ID_CARD_SIZE, Image.LANCZOS)
            canvas_img.paste(front, (x1, y))
            canvas_img.paste(back, (x2, y))

            # Draw borders
            draw_border(draw, x1, y, card_w, card_h)
            draw_border(draw, x2, y, card_w, card_h)

            # Draw scissor cut line after each set except last
            if idx < sets_per_page - 1:
                cut_y = y + card_h + spacing_y // 2
                draw_scissor_line(draw, 100, a4_width - 100, cut_y)

        # Save and print
        timestamp = datetime.now().strftime("%d-%m-%Y_%H%M%S")
        os.makedirs("Print Data/Multi_ID", exist_ok=True)
        final_path = os.path.abspath(f"Print Data/Multi_ID/final_batch_{timestamp}.png")

        # Save image with DPI
        canvas_img.save(final_path, dpi=(300, 300))

        # Ensure file is fully written before printing
        canvas_img.close()
        time.sleep(0.5)  # Slight delay to ensure file system sync

        if os.path.exists(final_path):
            messagebox.showinfo("Success", "Click OK to Start Print.\nSelect Printer & Paper Size and print.")
            os.startfile(final_path, "print")
            preview_win.destroy()
        else:
            messagebox.showerror("Error", "File not found for printing.")

    redraw()
    tk.Button(preview_win,text="🖨️Print All",command=do_final_print,bg="green",fg="white",font=("Arial", 10, "bold")).pack(pady=10)

def update_images_to_boxes(front_img=None, back_img=None):
    """Update the front and/or back image boxes with the cropped images, resizing them to fixed size."""
    global front_image_box, back_image_box
    global front_cropped_img, back_cropped_img
    global current_front_image, current_back_image

    # Define fixed display size in pixels
    DISPLAY_WIDTH = 357
    DISPLAY_HEIGHT = 225

    # Update current image references if provided
    if front_img:
        current_front_image = front_img
        front_cropped_img = front_img

    if back_img:
        current_back_image = back_img
        back_cropped_img = back_img

    # Reverse images if needed
    if Reverse_var.get():
        front_img, back_img = back_img, front_img

    # Mirror images if needed
    if Mirror_var.get():
        if front_img:
            front_img = front_img.transpose(Image.FLIP_LEFT_RIGHT)
        if back_img:
            back_img = back_img.transpose(Image.FLIP_LEFT_RIGHT)

    # Resize and update front image box
    if front_img:
        front_img_resized = front_img.resize((DISPLAY_WIDTH, DISPLAY_HEIGHT), Image.LANCZOS)
        front_img_tk = ImageTk.PhotoImage(front_img_resized)
        front_image_box.config(image=front_img_tk)
        front_image_box.image = front_img_tk
 
    # Resize and update back image box
    if back_img:
        back_img_resized = back_img.resize((DISPLAY_WIDTH, DISPLAY_HEIGHT), Image.LANCZOS)
        back_img_tk = ImageTk.PhotoImage(back_img_resized)
        back_image_box.config(image=back_img_tk)
        back_image_box.image = back_img_tk

def upload_doc():
    global file_path, label, doc, attempts, password_window

    file_path = filedialog.askopenfilename(filetypes=[("Files", "*.png;*.jpg;*.jpeg;*.gif;*.pdf")])
    if not file_path:
        return

    filename = file_path.split('/')[-1]
    truncated_filename = filename[:20] + "..." if len(filename) > 20 else filename
    label.config(text=f"File Name: {truncated_filename}", font=("Arial", 10, "bold"))

    attempts = 3

    if 'password_window' in globals() and password_window.winfo_exists():
        password_window.destroy()

    if file_path.endswith(".pdf"):
        doc = fitz.open(file_path)
        if doc.is_encrypted:
            show_password_window()

def show_password_window():
    global password_window, attempts

    password_window = tk.Toplevel(root)
    password_window.title("🔓 Enter PDF Password")
    password_window.geometry("350x200")
    password_window.configure(bg="#f8f9fa")  # Light grey background
    password_window.resizable(False, False)

    # Center the window
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x_position = (screen_width // 2) - (350 // 2)
    y_position = (screen_height // 2) - (200 // 2)
    password_window.geometry(f"350x200+{x_position}+{y_position}")

    # Label
    tk.Label(password_window, text="Enter password to unlock PDF:",font=("Arial", 12, "bold"), bg="#f8f9fa", fg="#333").pack(pady=15)

    # Password Entry (Visible)
    password_entry = tk.Entry(password_window, font=("Arial", 12), width=25, bd=2, relief="solid")
    password_entry.pack(pady=10)
    password_entry.focus_set()

    def on_submit():
        global attempts
        password = password_entry.get()

        if password:
            success = doc.authenticate(password)
            if success:
                messagebox.showinfo("Success", "✅ Document unlocked successfully!")
                password_window.destroy()
                attempts = 3
                load_first_page_for_crop()
            else:
                attempts -= 1
                if attempts > 0:
                    messagebox.showerror("Error", f"❌ Incorrect password. {attempts} attempts left.")
                    password_entry.delete(0, tk.END)
                    password_window.lift()
                else:
                    messagebox.showerror("Error", "⛔ Maximum attempts reached.")
                    password_window.destroy()
                    attempts = 3
                    reopen_password_prompt()
        else:
            messagebox.showwarning("Warning", "⚠ Password is required.")

    # Submit Button with hover effect
    submit_button = tk.Button(password_window, text="Submit", font=("Arial", 12, "bold"),bg="#28a745", fg="white", padx=15, pady=5, relief="flat",command=on_submit)
    submit_button.pack(pady=15)

    # Hover effect
    def on_enter(e): submit_button.config(bg="#218838")
    def on_leave(e): submit_button.config(bg="#28a745")

    submit_button.bind("<Enter>", on_enter)
    submit_button.bind("<Leave>", on_leave)

    password_window.lift()

def reopen_password_prompt():
    """
    Function to reopen the password prompt if attempts are exceeded.
    """
    messagebox.showinfo("Info", "Please re-upload the file to try again.")
    upload_doc()  # Re-trigger file selection and reset everything

def close_preview_window():
    """ Closes the preview window and restores the main UI. """
    global preview_window
    if preview_window:
        # preview_window.destroy()
        preview_window = None  # Reset variable
    root.state("normal")  # Restore the main window
    root.lift()  # Bring it to the front
    root.focus_force()  # Ensure focus is on the main window
    
def confirm_crop_from_ui(card_name):
    global front_crop, back_crop
    if front_crop and back_crop:
        crop_and_display_images(front_crop, back_crop, card_name)
    else:
        messagebox.showwarning("Warning", "Please crop both front and back before confirming.")

def navigate_pdf(direction):
    new_index = current_pdf_page_index + direction
    if 0 <= new_index < total_pdf_pages:
        show_pdf_page(new_index)

def show_pdf_page(index):
    global img_tk, img, canvas, current_pdf_page_index

    canvas.delete("all")

    if 0 <= index < total_pdf_pages:
        current_pdf_page_index = index
        page = doc.load_page(index)
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom_level, zoom_level))
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        img_tk = ImageTk.PhotoImage(img)
        canvas.create_image(0, 0, anchor="nw", image=img_tk)
        canvas.config(scrollregion=canvas.bbox("all"))

        if total_pdf_pages > 1:
            page_label.config(text=f"📄 Page {current_pdf_page_index + 1} of {total_pdf_pages}")
        else:
            page_label.config(text="")

        # Disable buttons at edges
        if total_pdf_pages > 1:
            prev_btn.config(state="normal" if index > 0 else "disabled")
            next_btn.config(state="normal" if index < total_pdf_pages - 1 else "disabled")

def show_preview(file_path,card_name):
    global canvas, img_tk, preview_window,prev_btn, next_btn,page_label

    # If preview window already exists, don't create a new one
    if preview_window is not None:
        preview_window.lift()  # Bring existing preview window to front
        return

    # root.withdraw()  # Hide main window
    root.state("iconic")  

    if not file_path:
        messagebox.showerror("Error", "No file selected.")
        return

    preview_window = Toplevel(root)
    preview_window.title(f"{card_name} Preview")  # Update window title with card name

    # Set window size to a large default size, but make it resizable
    preview_window.resizable(True, True)  # Allow the window to be resized
    # Calculate the position for the center of the screen
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    window_width = 1400
    window_height = 700

    # Calculate the x and y position to center the window
    position_top = 20
    position_right = int((screen_width - window_width) / 2)

    # Apply the position to the geometry
    preview_window.geometry(f'{window_width}x{window_height}+{position_right}+{position_top}')

    # Create a frame to hold the left and right sections
    main_frame = Frame(preview_window)
    main_frame.pack(fill=tk.BOTH, expand=True)

    # Left frame for image or PDF preview
    preview_frame = Frame(main_frame)
    preview_frame.pack(side="left", fill=tk.BOTH, expand=True)

    # Right frame for buttons (Zoom In, Zoom Out, Crop)
    button_frame = Frame(main_frame, width=200, bg="#DDEEFF")
    button_frame.pack(side="right", fill=tk.Y)

    zoom_in_btn = tk.Button(button_frame, text="🔍➕Zoom In", command=zoom_in, font=("Arial", 12 ,"bold"), bg="#28A745", fg="white")
    zoom_in_btn.pack(side="top", padx=10, pady=10, fill="x")

    zoom_out_btn = tk.Button(button_frame, text="🔍➖Zoom Out", command=zoom_out, font=("Arial", 12, "bold"), bg="#DC3545", fg="white")
    zoom_out_btn.pack(side="top", padx=10, pady=10, fill="x")

    # Divider between Zoom and Crop Tools
    divider1 = tk.Frame(button_frame, height=2, bd=1, relief="sunken", bg="grey")
    divider1.pack(fill="x", padx=5, pady=5)

    global crop_btn  # Declare as global
    crop_btn = tk.Button(button_frame, text="✂️Crop", command=lambda: crop_image(card_name), font=("Arial", 12 ,"bold"), bg="#FFC107", fg="white")
    crop_btn.pack(side="top", padx=10, pady=10, fill="x")

    confirm_btn = tk.Button(button_frame, text="✅ Confirm Crop", font=("Arial", 12 ,"bold"), bg="green", fg="white", command=lambda: confirm_crop_from_ui(card_name))
    confirm_btn.pack(side="top", padx=10, pady=10, fill="x")

    reset_btn = tk.Button(button_frame, text="🔄 Reset Crop", font=("Arial", 12 ,"bold"), bg="orange", fg="white", command=lambda: crop_image(card_name))
    reset_btn.pack(side="top", padx=10, pady=10, fill="x")

    # Divider before Page Navigation
    divider2 = tk.Frame(button_frame, height=2, bd=1, relief="sunken", bg="grey")
    divider2.pack(fill="x", padx=5, pady=5)

    prev_btn = tk.Button(button_frame, text="<< Prev Page", font=("Arial", 12 ,"bold"), bg="#28A745", fg="white", command=lambda: navigate_pdf(-1))
    prev_btn.pack_forget()

    next_btn = tk.Button(button_frame, text="Next Page >>", font=("Arial", 12, "bold"), bg="#DC3545", fg="white", command=lambda: navigate_pdf(1))
    next_btn.pack_forget()

    page_label = tk.Label(button_frame, text="", font=("Arial", 12, "bold"), bg="#DDEEFF", fg="black")
    page_label.pack_forget()

    # Create a canvas frame to contain canvas + scrollbars properly
    canvas_container = Frame(preview_frame)
    canvas_container.pack(fill=tk.BOTH, expand=True)

    canvas = Canvas(canvas_container)
    canvas.pack(side="left", fill=tk.BOTH, expand=True)

    scrollbar_y = Scrollbar(canvas_container, orient="vertical", command=canvas.yview, width=30)
    scrollbar_y.pack(side="right", fill="y")

    scrollbar_x = Scrollbar(preview_frame, orient="horizontal", command=canvas.xview, width=30)
    scrollbar_x.pack(side="bottom", fill="x")

    canvas.config(xscrollcommand=scrollbar_x.set, yscrollcommand=scrollbar_y.set)

    update_preview()  # Make sure the preview is updated

    # Mouse Wheel Scroll Binding (For Vertical Scrolling)
    canvas.bind("<MouseWheel>", on_mouse_wheel)  # For scrolling with the mouse wheel

    # Add a close event handler to properly reset the variable
    preview_window.protocol("WM_DELETE_WINDOW", close_preview_window)

def on_mouse_wheel(event):
    """ Scroll vertically using the mouse wheel. """
    if event.delta > 0:  # Scroll up (move up)
        canvas.yview_scroll(-1, "units")  # Scroll up by 1 unit
    else:  # Scroll down (move down)
        canvas.yview_scroll(1, "units")   # Scroll down by 1 unit

def update_preview():
    """ Updates the canvas with the zoomed image or PDF pages (up to 3). """
    global canvas, img_tk, doc, zoom_level, file_path

    if not file_path:
        return

    # Clear existing content on canvas
    canvas.delete("all")

    if file_path.endswith(".pdf"):
        # Handle PDF preview (up to 3 pages)
        try:
            if doc is None:
                raise Exception("PDF not loaded or encrypted.")

            img_tk = []  # Keep a list of images to avoid garbage collection
            y_offset = 0  # Start from top

            for i in range(min(3, len(doc))):  # Show pages 1 to 3
                page = doc.load_page(i)
                pix = page.get_pixmap(matrix=fitz.Matrix(zoom_level, zoom_level))
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

                tk_img = ImageTk.PhotoImage(img)
                img_tk.append(tk_img)  # Prevent garbage collection

                canvas.create_image(0, y_offset, anchor="nw", image=tk_img)
                y_offset += img.height + 10  # Space between pages

            canvas.config(scrollregion=canvas.bbox("all"))  # Scroll support

        except Exception as e:
            messagebox.showerror("Error", f"Failed to open PDF: {str(e)}")

    else:
        # Handle single image preview
        try:
            img = Image.open(file_path)
            img = img.resize((int(img.width * zoom_level), int(img.height * zoom_level)))
            img_tk = ImageTk.PhotoImage(img)

            canvas.create_image(0, 0, anchor="nw", image=img_tk)
            canvas.config(scrollregion=canvas.bbox("all"))

        except Exception as e:
            messagebox.showerror("Error", f"Failed to open image: {str(e)}")

MIN_ZOOM = 0.5  # Minimum zoom level
MAX_ZOOM = 5    # Maximum zoom level

def zoom_in():
    global zoom_level
    if zoom_level < MAX_ZOOM:
        zoom_level *= 1.2  # Zoom In by 20%
        update_preview()
    else:
        messagebox.showinfo("Zoom Limit", f"Maximum zoom level of {MAX_ZOOM} reached.")

def zoom_out():
    global zoom_level
    if zoom_level > MIN_ZOOM:
        zoom_level *= 0.8  # Zoom Out by 20%
        update_preview()
    else:
        messagebox.showinfo("Zoom Limit", f"Minimum zoom level of {MIN_ZOOM} reached.")

def process_card_selection(card_name):
    global file_path, img, canvas, selected_document_type  # Ensure canvas and selected_document_type are included

    if not file_path:
        messagebox.showerror("Error", "No Document Uploaded. Please Upload and Then Select")
        return

    # **Ensure canvas exists**
    if 'canvas' not in globals():
        canvas = Canvas(root)  # Create a canvas if it does not exist

    # **Ensure selected_document_type is defined** (this may already exist, but ensuring it's initialized correctly)
    if 'selected_document_type' not in globals():
        selected_document_type = tk.StringVar()  # Create StringVar if it doesn't exist

    # **Set the card_name in selected_document_type**
    selected_document_type.set(card_name)  # This sets the StringVar to the value of card_name

    # **Load the image before cropping**
    load_image()

    # Load predefined coordinates
    crop_coordinates = load_crop_coordinates()

    if card_name in crop_coordinates:
        front_coords = crop_coordinates[card_name][0].get("front")
        back_coords = crop_coordinates[card_name][0].get("back")

        if front_coords and back_coords:
            crop_and_display_images(front_coords, back_coords, card_name)  # Crop without opening preview
            return  # **Exit to prevent preview window from opening**

    # If no predefined coordinates, open preview window for manual cropping
    show_preview(file_path, card_name)

def load_image():
    global img, file_path, doc

    if file_path.endswith(".pdf"):
        try:
            page = doc.load_page(0)  # Load first page
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom_level, zoom_level))
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to convert PDF to image: {str(e)}")
            return
    else:
        try:
            img = Image.open(file_path)  # Load image normally
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open image: {str(e)}")
            return
        
# Function to load crop data from JSON file
def load_crop_data():
    """Loads crop data from a JSON file."""
    if os.path.exists(CROP_DATA_FILE):
        with open(CROP_DATA_FILE, "r") as file:
            return json.load(file)
    return {}  # Return empty dictionary if file doesn't exist

# Function to save crop data to JSON file
def save_crop_data(data):
    """Saves crop data to a JSON file."""
    with open(CROP_DATA_FILE, "w") as file:
        json.dump(data, file, indent=4)

# Load crop data initially
crop_data = load_crop_data()

# Load buttons and Reverse state correctly
buttons, Reverse_state,mirror_state = load_buttons()  

def open_settings():
    """Opens a settings window with three tabs: Crop Data Management, Rename Buttons, and Reverse/Mirror Images."""
    global Reverse_var, Mirror_var  # Ensure global access to Reverse_var & Mirror_var

    root.iconify()  # Minimize main window
    settings_win = tk.Toplevel(root)
    settings_win.title("Settings")
    settings_win.configure(bg="#DDEEFF")

    win_width, win_height = 600, 600
    settings_win.geometry(f"{win_width}x{win_height}")
    x_pos = (settings_win.winfo_screenwidth() - win_width) // 2
    y_pos = (settings_win.winfo_screenheight() - win_height) // 2
    settings_win.geometry(f"{win_width}x{win_height}+{x_pos}+{y_pos}")

    def on_close():
        root.deiconify()
        settings_win.destroy()

    settings_win.protocol("WM_DELETE_WINDOW", on_close)

    style = ttk.Style()
    style.configure("TNotebook.Tab", font=("Arial", 11, "bold"), padding=[10, 5], background="#DDEEFF")
    style.map("TNotebook.Tab", background=[("selected", "Black")], foreground=[("selected", "Blue")])

    notebook = ttk.Notebook(settings_win, style="TNotebook")
    notebook.pack(expand=True, fill='both')

    # Define tabs
    tab1 = ttk.Frame(notebook)
    tab2 = ttk.Frame(notebook)
    tab3 = ttk.Frame(notebook)

    notebook.add(tab1, text="Manage Crop Data")
    notebook.add(tab2, text="Manage ID Cards")
    notebook.add(tab3, text="Image Settings")

    # ====== TAB 1: Manage Crop Data ======
    tk.Label(tab1, text="Manage Crop Data", font=("Arial", 14, "bold"), bg="#EEEEEE").pack(pady=5)

    # Sort keys alphabetically (optional)
    for card_name in sorted(crop_data.keys()):
        frame = tk.Frame(tab1, bg="#FFFFFF", bd=1, relief=tk.SOLID)
        frame.pack(pady=4, padx=12, fill="x")

        name_label = tk.Label(frame, text=card_name, font=("Arial", 12), bg="#FFFFFF")
        name_label.pack(side="left", padx=12, pady=6)

        delete_btn = tk.Button(frame,text=" 🗑️ Delete",font=("Arial", 12, "bold"),bg="#DC3545",fg="white",command=lambda name=card_name: confirm_delete(name, settings_win))
        delete_btn.pack(side="right", padx=12, pady=6)

    # ----- Simple Frame for Tab 2-----
    tab2_frame = tk.Frame(tab2, bg="#EEEEEE")
    tab2_frame.pack(fill="both", expand=True)

    # ----- Load Tab2 Content Function -----
    def load_tab2_content():
        for widget in tab2_frame.winfo_children():
            widget.destroy()

        def center_pack(widget):
            widget.pack(pady=5)
            widget.pack_configure(anchor="center")

        tk.Label(tab2_frame, text="Edit ID Card Option", font=("Arial", 14, "bold"),
                bg="#EEEEEE", anchor="center", justify="center").pack(pady=10)

        tk.Label(tab2_frame, text="Select ID Card:", font=("Arial", 11, "bold"),
                bg="#EEEEEE", anchor="center", justify="center").pack(pady=2)

        selected_button_var = tk.StringVar()
        dropdown = ttk.Combobox(tab2_frame, textvariable=selected_button_var,
                                state="readonly", font=("Arial", 11, "bold"), justify="center", width=15)
        dropdown["values"] = [btn[0] for btn in buttons]
        dropdown.pack(pady=2)

        tk.Label(tab2_frame, text="New Name:", font=("Arial", 11, "bold"),
                bg="#EEEEEE", anchor="center", justify="center").pack(pady=2)

        new_name_entry = tk.Entry(tab2_frame, font=("Arial", 11, "bold"), justify="center", width=15)
        new_name_entry.pack(pady=2)

        def rename_button():
            old_name = selected_button_var.get()
            new_name = new_name_entry.get().strip()
            if old_name and new_name:
                if new_name in [btn[0] for btn in buttons]:
                    messagebox.showerror("Error", "A ID Card with this name already exists.")
                    return
                for i, (btn_text, color) in enumerate(buttons):
                    if btn_text == old_name:
                        buttons[i] = (new_name, color)
                        break
                save_buttons(buttons, Reverse_var.get(), Mirror_var.get())
                refresh_buttons()
                load_tab2_content()
            else:
                messagebox.showerror("Error", "Please select a ID Card and enter a new name.")

        tk.Button(tab2_frame, text="Rename", font=("Arial", 12, "bold"),
                bg="#28A745", fg="white", width=10, command=rename_button).pack(pady=10)

        # Define a fixed set of 10 random colors
        random_colors = [
            "#007BFF", "#28A745", "#FFC107", "#DC3545", "#6F42C1",
            "#20C997", "#FD7E14", "#6610F2", "#17A2B8", "#E83E8C"
        ]

        # ---- Add ID Card ----
        tk.Label(tab2_frame, text="Add New ID Card", font=("Arial", 12, "bold"),
                bg="#EEEEEE", anchor="center", justify="center").pack(pady=5)

        new_button_name_entry = tk.Entry(tab2_frame, font=("Arial", 11, "bold"), justify="center", width=15)
        new_button_name_entry.pack(pady=2)

        def add_new_button():
            new_name = new_button_name_entry.get().strip()

            # Check if the number of buttons is less than 12
            if len(buttons) >= 12:
                messagebox.showerror("Limit Reached", "You can only add up to 12 ID cards.")
                return

            if new_name and new_name not in [btn[0] for btn in buttons]:
                # Assign a random color from the predefined palette
                color = random.choice(random_colors)
                buttons.append((new_name, color))  # Add new button with name and color
                save_buttons(buttons, Reverse_var.get(), Mirror_var.get())  # Save buttons
                refresh_buttons()  # Refresh button list
                load_tab2_content()  # Reload content
            else:
                messagebox.showerror("Error", "ID Card name is empty or already exists.")

        tk.Button(tab2_frame, text="Add", font=("Arial", 12, "bold"),
                bg="#007BFF", fg="white", width=10, command=add_new_button).pack(pady=10)

        # ---- Delete Button ----
        tk.Label(tab2_frame, text="Delete ID Card", font=("Arial", 12, "bold"),
                bg="#EEEEEE", anchor="center", justify="center").pack(pady=5)

        del_button_var = tk.StringVar()
        del_dropdown = ttk.Combobox(tab2_frame, textvariable=del_button_var,
                                    state="readonly", font=("Arial", 11, "bold"), justify="center", width=15)
        del_dropdown["values"] = [btn[0] for btn in buttons]
        del_dropdown.pack(pady=2)

        def delete_button():
            name = del_button_var.get()
            if name:
                confirm = messagebox.askyesno("Confirm Delete", f"Are you sure to delete '{name}'?")
                if confirm:
                    buttons[:] = [b for b in buttons if b[0] != name]
                    save_buttons(buttons, Reverse_var.get(), Mirror_var.get())
                    refresh_buttons()
                    load_tab2_content()
            else:
                messagebox.showerror("Error", "Please select a button to delete.")

        tk.Button(tab2_frame, text="Delete", font=("Arial", 12, "bold"),
                bg="#DC3545", fg="white", width=10, command=delete_button).pack(pady=10)

    # Call after all definitions
    load_tab2_content()

    # ====== TAB 3: Image Settings (Reverse & Mirror) ======
    tk.Label(tab3, text="Image Settings", font=("Arial", 14, "bold"), bg="#EEEEEE").pack(pady=5)

    def toggle_Reverse():
        """Handles toggling image Reverse before cropping."""
        if Reverse_var.get():
            Reverse_btn.config(text="Reverse: ON", bg="green")
        else:
            Reverse_btn.config(text="Reverse: OFF", bg="red")

        # Save updated state (buttons, Reverse, Mirror)
        save_buttons(buttons, Reverse_var.get(), Mirror_var.get())  

    def toggle_Mirror():
        """Handles toggling Mirror effect before cropping."""
        if Mirror_var.get():
            Mirror_btn.config(text="Mirror: ON", bg="green")  # ✅ Green for ON
        else:
            Mirror_btn.config(text="Mirror: OFF", bg="red")   # ✅ Red for OFF

        # ✅ Save the updated Mirror state
        save_buttons(buttons, Reverse_var.get(), Mirror_var.get())  
    
    # Reverse Button (Reflects saved state)
    Reverse_btn = tk.Button(tab3, text="Reverse: ON" if Reverse_var.get() else "Reverse: OFF",font=("Arial", 12, "bold"),bg="green" if Reverse_var.get() else "red",
                            fg="white",command=lambda: Reverse_var.set(not Reverse_var.get()) or toggle_Reverse())
    Reverse_btn.pack(pady=10)
    tk.Label(tab3, text="Reverse: Flips image upside-down", bg="#DDEEFF", font=("Arial", 9, "italic")).pack()

    # Mirror Button (Updated Style: Green ON, Red OFF)
    Mirror_btn = tk.Button(tab3, text="Mirror: ON" if Mirror_var.get() else "Mirror: OFF",font=("Arial", 12, "bold"),bg="green" if Mirror_var.get() else "red",
                        fg="white",command=lambda: Mirror_var.set(not Mirror_var.get()) or toggle_Mirror())
    Mirror_btn.pack(pady=10)
    tk.Label(tab3, text="Mirror: Flips image left to right", bg="#DDEEFF", font=("Arial", 9, "italic")).pack()

# Load buttons and Reverse state correctly
buttons, Reverse_state ,mirror_state = load_buttons()

def refresh_buttons():
    """Refresh button panel dynamically."""
    for widget in button_frame.winfo_children():
        widget.destroy()

    row, col = 0, 0
    for btn_text, color in buttons:  # Unpacking now works correctly!
        btn = tk.Button(button_frame, text=btn_text, font=("Arial", 12, "bold"), bg=color, fg="white",
                        command=lambda name=btn_text: process_card_selection(name))
        btn.grid(row=row, column=col, pady=5, padx=5, sticky="ew")
        col += 1
        if col == 2:
            col = 0
            row += 1

def confirm_delete(card_name, settings_win):
    confirm = messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete {card_name}?")
    if confirm:
        delete_crop_data(card_name, settings_win)

def delete_crop_data(card_name, settings_win):
    if card_name in crop_data:
        del crop_data[card_name]
        save_crop_data(crop_data)
        messagebox.showinfo("Success", f"Crop data for {card_name} deleted!")
        settings_win.destroy()
        open_settings()

def resize_and_add_border(image):
    """Resizes the image and adds a 5-pixel border."""
    try:
        if not isinstance(image, Image.Image):  
            raise ValueError("Expected a PIL Image object, but got:", type(image))

        # Resize the image to 53x83mm (208x312 pixels at 300 DPI)
        target_size = (208, 312)  
        resized_img = image.resize(target_size, Image.LANCZOS)

        # Create new image with border
        bordered_img = Image.new("RGB", (target_size[0] + 2 * border_size, target_size[1] + 2 * border_size), "black")
        bordered_img.paste(resized_img, (border_size, border_size))

        return bordered_img

    except Exception as e:
        return None
    
def show_print_preview():
    try:
        global front_cropped_img, back_cropped_img

        if not selected_document_type.get().strip():
            messagebox.showerror("Error", "Please select an ID type before previewing.")
            return

        if ('front_cropped_img' not in globals() or front_cropped_img is None) and \
           ('back_cropped_img' not in globals() or back_cropped_img is None):
            messagebox.showerror("Error", "Please upload at least one document before previewing.")
            return

        paper_size = selected_paper_size.get().strip()

        if paper_size == "4x6 Paper":
            canvas_width, canvas_height = 1200, 1800
            img_width, img_height = ID_CARD_SIZE
            x_offset = (canvas_width - img_width) // 2
            y_offsets = [(canvas_height - 2 * img_height) // 3, (canvas_height - img_height) - (canvas_height - 2 * img_height) // 3]
            add_border = True 

        elif paper_size == "A4 Paper":
            canvas_width, canvas_height = 2480, 3508
            img_width, img_height = ID_CARD_SIZE
            front_pos = (218, 47)
            back_pos  = (1287, 47)
            add_border = True

        elif paper_size == "A4 Paper U+D":
            canvas_width, canvas_height = 2480, 3508
            img_width, img_height = 1772, 1181
            front_pos = (300, 200)
            back_pos = (300, 500 + img_height + 20)
            add_border = False

        elif paper_size == "A4 Paper L+R":
            canvas_width, canvas_height = 2480, 3508
            img_width, img_height = 937, 1402
            front_pos = (150, 150)
            back_pos = (400 + img_width, 150)
            add_border = False

        else:
            messagebox.showerror("Error", "Invalid Paper Size selected.")
            return

        preview_img = Image.new("RGB", (canvas_width, canvas_height), "white")
        draw = ImageDraw.Draw(preview_img)

        images = []
        if front_cropped_img is not None:
            images.append(('front', front_cropped_img))
        if back_cropped_img is not None:
            images.append(('back', back_cropped_img))

        for img_type, img in images:
            if img is not None:
                resized_img = img.resize((img_width, img_height), Image.LANCZOS)
                bordered_img = resized_img if not add_border else Image.new("RGB", (img_width + 2 * border_size, img_height + 2 * border_size), "black")
                if add_border:
                    bordered_img.paste(resized_img, (border_size, border_size))

                if img_type == 'front':
                    if paper_size == "4x6 Paper":
                        preview_img.paste(bordered_img, (x_offset, y_offsets[0]))
                    else:
                        preview_img.paste(bordered_img, front_pos)
                elif img_type == 'back':
                    if paper_size == "4x6 Paper":
                        preview_img.paste(bordered_img, (x_offset, y_offsets[1]))
                    else:
                        preview_img.paste(bordered_img, back_pos)

        preview_resized = preview_img.resize((400, 600), Image.LANCZOS)
        preview_img_tk = ImageTk.PhotoImage(preview_resized)

        preview_win = tk.Toplevel(root)
        preview_win.title("Print Preview")
        label = tk.Label(preview_win, image=preview_img_tk)
        label.photo = preview_img_tk
        label.pack()

    except Exception as e:
        messagebox.showerror("Preview Error", f"An unexpected error occurred: {str(e)}")

def wait_for_program():
    def update_timer():
        nonlocal seconds_left
        if seconds_left > 0:
            label.config(text=f"Waiting For Program to Load... {seconds_left} sec")
            seconds_left -= 1
            root.after(1000, update_timer)
        else:
            root.quit()  # Close the popup and exit the event loop
            root.destroy()
 
    seconds_left = 15
    root = tk.Tk()
    root.overrideredirect(1)  # No title bar
    root.attributes("-topmost", True)  # Always on top
    
    # Define width and height of the popup
    width = 400
    height = 80
    
    # Get screen width and height
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    
    # Calculate x, y to center the window
    x = (screen_width // 2) - (width // 2)
    y = (screen_height // 2) - (height // 2)
    
    # Set geometry with center position
    root.geometry(f"{width}x{height}+{x}+{y}")
    
    label = tk.Label(root, text=f"Waiting For Program to Open... {seconds_left} sec", font=("Arial", 12,"bold"))
    label.pack(expand=True)
    
    root.after(1000, update_timer)
    root.mainloop()
 
def open_epson_photo_plus():
    import pyautogui
    global epson_photo_plus_path
    # 1. Open Epson Photo+ without minimizing
    subprocess.Popen([epson_photo_plus_path])
 
    # Wait and show the popup for the program
    wait_for_program()
 
    # 2. Find Epson Photo+ window and bring it to the front
    windows = gw.getWindowsWithTitle("Epson Photo+")  # Replace with actual window title
    if windows:
        ep_window = windows[0]
        if ep_window.isMinimized:
            ep_window.restore()  # Restore if minimized
        ep_window.activate()  # Bring the window to the front
        ep_window.maximize()  # Maximize the window
    else:
        print("Epson Photo+ window not found!")

    # 1. Click inside the program (adjust coordinates if needed)
    time.sleep(1)
    pyautogui.click(1143, 156) # ID card Select
    time.sleep(1)
    pyautogui.click(767, 243) # landscape
    time.sleep(1)
    pyautogui.click(881, 558) # Create new  
    time.sleep(1)
    pyautogui.click(26, 54) # select photo 

    # 3. Wait for file dialog to open
    time.sleep(2)
    # 4. Type the folder path
    pyautogui.typewrite(Print_Data_Folder, interval=0.05)
    time.sleep(0.5)
    pyautogui.press('enter')
    # 5. Wait for folder to load
    time.sleep(2)
    # 6. Find the latest folder inside "Print Data"
    subfolders = [os.path.join(Print_Data_Folder, d) for d in os.listdir(Print_Data_Folder) if os.path.isdir(os.path.join(Print_Data_Folder, d))]
    latest_folder = max(subfolders, key=os.path.getmtime)
    # 7. Get folder name only
    latest_folder_name = os.path.basename(latest_folder)
    # 8. Type the latest folder name
    pyautogui.typewrite(latest_folder_name, interval=0.05)
    time.sleep(0.5)
    pyautogui.press('enter')
    # 9. Wait for folder to open
    time.sleep(2)
    # 10. Find all files inside that folder and sort by modification time
    files = [os.path.join(latest_folder, f) for f in os.listdir(latest_folder) if os.path.isfile(os.path.join(latest_folder, f))]
    sorted_files = sorted(files, key=os.path.getmtime, reverse=True)  # Sort by most recently modified
    if len(sorted_files) < 2:
        raise Exception("Not enough files to select front and back images!")
    # 11. Select the second most recently modified image (front image)
    front_image = sorted_files[1]  # Second most recently modified image
    front_image_name = os.path.basename(front_image)
    # 12. Type the front image file name and open it
    pyautogui.typewrite(front_image_name, interval=0.05)
    time.sleep(0.5)
    pyautogui.press('enter')
    time.sleep(2)  # Wait for the front image to load
    pyautogui.click(865,576) # OK to insert image 
    time.sleep(1)
    pyautogui.click(80,139) #enlarge
    time.sleep(1)
    pyautogui.click(80,139) #enlarge
    time.sleep(1)    
    pyautogui.click(80,139) #enlarge
    time.sleep(1)    
    pyautogui.click(80,139) #enlarge
    time.sleep(1)    
    pyautogui.click(80,139) #enlarge
    time.sleep(1)    
    pyautogui.click(80,139) #enlarge
    time.sleep(1)
    pyautogui.click(80,139) #enlarge
    time.sleep(1)

    # 13. Ask user to load back image
    user_response = pyautogui.confirm(text='Do you want to start the back image Print ?', buttons=['Yes', 'No'])
    if user_response == 'Yes':
 
        # 14. Bring the target program window to front
        windows = gw.getWindowsWithTitle("Epson Photo+")
        if windows:
            ep_window = windows[0]
            if ep_window.isMinimized:
                ep_window.restore()
            ep_window.activate()
            ep_window.maximize()
            time.sleep(2)
 
        time.sleep(1)
        pyautogui.click(21, 695) # Back
        time.sleep(1)
        pyautogui.click(674, 405) # Don't Save
        time.sleep(1)
        pyautogui.click(881, 558) # Create new  
        time.sleep(1)
        pyautogui.click(1143, 156) # ID card Select
        time.sleep(1)
        pyautogui.click(767, 243) # landscape
        time.sleep(1)
        pyautogui.click(881, 558) # Create new  
        time.sleep(1)
        pyautogui.click(26, 54) # select photo 

        # 16. Wait for file dialog to open again
        time.sleep(2)
        # 17. Type the folder path again (same folder as before)
        pyautogui.typewrite(Print_Data_Folder, interval=0.05)
        time.sleep(0.5)
        pyautogui.press('enter')
        # 18. Wait for folder to load
        time.sleep(2)
        # 19. Type the latest folder name again
        pyautogui.typewrite(latest_folder_name, interval=0.05)
        time.sleep(0.5)
        pyautogui.press('enter')
        # 20. Wait for folder to open
        time.sleep(2)
        # 21. Re-sort files and select the most recently modified file (back image)
        back_image = sorted_files[0]  # Most recently modified image
        back_image_name = os.path.basename(back_image)
        # 22. Type the back image file name and open it
        pyautogui.typewrite(back_image_name, interval=0.05)
        time.sleep(0.5)
        pyautogui.press('enter')
        time.sleep(2)  # Wait for the front image to load
        pyautogui.click(865,576) # OK to insert image 
        time.sleep(1)
        pyautogui.click(80,139) #enlarge
        time.sleep(1)
        pyautogui.click(80,139) #enlarge
        time.sleep(1)    
        pyautogui.click(80,139) #enlarge
        time.sleep(1)    
        pyautogui.click(80,139) #enlarge
        time.sleep(1)    
        pyautogui.click(80,139) #enlarge
        time.sleep(1)    
        pyautogui.click(80,139) #enlarge
        time.sleep(1)
        pyautogui.click(80,139) #enlarge
        time.sleep(1)
    else:
        print("Back image selection skipped.")
    return

def print_id_card():
    try:
        global front_cropped_img, back_cropped_img
 
        if not selected_document_type.get().strip():
            messagebox.showerror("Error", "Please select an ID CARD type before printing.")
            return
 
        if front_cropped_img is None and back_cropped_img is None:
            messagebox.showerror("Error", "No cropped images found. Please crop and preview the ID card before printing.")
            return
 
        paper_size = selected_paper_size.get().strip()

        # PVC Card Special Flow
        if paper_size == "PVC Card":
            # Ask user if they want border
            user_response = messagebox.askyesno("PVC Card Border", "Do you want to add a black border around the PVC card?")
            add_border = user_response
            border_size = 5 if add_border else 0
        
            saved_images = []  # Collect saved images to open later
        
            for side, img in [('Front', front_cropped_img), ('Back', back_cropped_img)]:
                if img is None:
                    continue
        
                img_width, img_height = (1011, 638)  # Standard ID card size in pixels
                dpi = 300  # Standard DPI for PVC card printing
        
                resized_img = img.resize((img_width, img_height), Image.LANCZOS)
        
                # 🛠️ ✨ ADD proper border logic here
                if add_border and border_size > 0:
                    bordered_img = Image.new("RGB", (img_width + 2 * border_size, img_height + 2 * border_size), "black")
                    bordered_img.paste(resized_img, (border_size, border_size))
                else:
                    bordered_img = resized_img
        
                # Save front/back PVC images inside selected document type folder
                if selected_document_type.get().strip():
                    save_dir = f"Print Data/{selected_document_type.get().strip()}"
                else:
                    messagebox.showerror("Error", "Please select a Document Type before printing.")
                    return
        
                os.makedirs(save_dir, exist_ok=True)
                timestamp = datetime.now().strftime("%d-%m-%Y_%H%M%S")
                save_path = os.path.abspath(f"{save_dir}/{side.lower()}_print_{timestamp}.png")
                bordered_img.save(save_path, dpi=(dpi, dpi))
        
                saved_images.append(save_path)  # Store path for later opening
        
            # Now open Epson Photo+ software
            open_epson_photo_plus()
        
            return  # Exit after saving and opening Photo+
        # Regular A4 / 4x6 Flow
        if paper_size == "4x6 Paper":
            canvas_width, canvas_height = 1200, 1800
            img_width, img_height = ID_CARD_SIZE
            x_offset = (canvas_width - img_width) // 2
            y_offsets = [
                (canvas_height - 2 * img_height) // 3,
                (canvas_height - img_height) - (canvas_height - 2 * img_height) // 3
            ]
            add_border = True
            border_size = 5
 
        elif paper_size == "A4 Paper":
            canvas_width, canvas_height = 2480, 3508
            img_width, img_height = ID_CARD_SIZE
            front_pos = (218, 47)
            back_pos  = (1287, 47)
            add_border = True
            border_size = 5
 
        elif paper_size == "A4 Paper U+D":
            canvas_width, canvas_height = 2480, 3508
            img_width, img_height = 1772, 1181
            front_pos = (300, 200)
            back_pos = (300, 500 + img_height + 20)
            add_border = False
            border_size = 0
 
        elif paper_size == "A4 Paper L+R":
            canvas_width, canvas_height = 2480, 3508
            img_width, img_height = 937, 1402
            front_pos = (150, 150)
            back_pos = (400 + img_width, 150)
            add_border = False
            border_size = 0
 
        else:
            messagebox.showerror("Error", "Invalid Paper Size selected.")
            return
 
        # Create blank canvas
        print_img = Image.new("RGB", (canvas_width, canvas_height), "white")
 
        images = []
        if front_cropped_img is not None:
            images.append(('front', front_cropped_img))
        if back_cropped_img is not None:
            images.append(('back', back_cropped_img))
 
        for img_type, img in images:
            if img is not None:
                resized_img = img.resize((img_width, img_height), Image.LANCZOS)
 
                if add_border and border_size > 0:
                    bordered_img = Image.new("RGB", (img_width + 2 * border_size, img_height + 2 * border_size), "black")
                    bordered_img.paste(resized_img, (border_size, border_size))
                else:
                    bordered_img = resized_img
 
                if img_type == 'front':
                    if paper_size == "4x6 Paper":
                        print_img.paste(bordered_img, (x_offset, y_offsets[0]))
                    else:
                        print_img.paste(bordered_img, front_pos)
                elif img_type == 'back':
                    if paper_size == "4x6 Paper":
                        print_img.paste(bordered_img, (x_offset, y_offsets[1]))
                    else:
                        print_img.paste(bordered_img, back_pos)
 
        # Save combined image
        if selected_document_type.get():
            save_dir = f"Print Data/{selected_document_type.get()}"
        else:
            save_dir = "Print and Crop"
 
        os.makedirs(save_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%d-%m-%Y_%H%M%S")
        save_path = os.path.abspath(f"{save_dir}/print_output_{timestamp}.png")
        print_img.save(save_path, dpi=(300, 300))
 
        messagebox.showinfo("Success", "Click OK to Start Print.\nSelect Printer & Paper Size and Print.")
        os.startfile(save_path, "print")
 
    except Exception as e:
        messagebox.showerror("Printing Error", f"An error occurred: {str(e)}")

def restart_ui():
    """Restarts the UI with a sleek, quick loading animation."""
    loading_win = tk.Toplevel(root)
    loading_win.title("Restarting...")
    loading_win.geometry("280x120")
    loading_win.configure(bg="#262626")  # Dark Grey Background
    loading_win.overrideredirect(True)  # Hide window frame

    # Center the window
    loading_win.update_idletasks()
    x = (loading_win.winfo_screenwidth() - 280) // 2
    y = (loading_win.winfo_screenheight() - 120) // 2
    loading_win.geometry(f"280x120+{x}+{y}")

    # Title Label
    label = tk.Label(loading_win, text="Restarting...", font=("Arial", 13, "bold"), fg="#00FFAA", bg="#262626")
    label.pack(pady=10)

    # Progress Bar
    progress = ttk.Progressbar(loading_win, mode="determinate", length=250, maximum=100)
    progress.pack(pady=10)

    # Animate Progress Bar (in thread to avoid UI freezing)
    def animate_and_restart():
        for i in range(101):
            progress["value"] = i
            loading_win.update_idletasks()
            time.sleep(0.02)  # ~2 seconds animation
        time.sleep(0.3)
        os.execl(sys.executable, sys.executable, *sys.argv)

    threading.Thread(target=animate_and_restart, daemon=True).start()

def open_image_viewer():
    """Opens a window to first select a folder, then browse images inside it with navigation & print/delete options."""
    image_folder = "Print Data"
    root.iconify()

    viewer_win = tk.Toplevel(root)
    viewer_win.title("Saved Images")
    viewer_win.configure(bg="#DDEEFF")

    win_width, win_height = 550, 730
    screen_width = viewer_win.winfo_screenwidth()
    screen_height = viewer_win.winfo_screenheight()
    x_pos = (screen_width - win_width) // 2
    y_pos = 10
    viewer_win.geometry(f"{win_width}x{win_height}+{x_pos}+{y_pos}")

    # Check if "Print Data" folder exists
    if not os.path.exists(image_folder):
        messagebox.showerror("Missing Folder", "'Print Data' folder was not found!")
        root.deiconify()
        viewer_win.destroy()
        return

    folders = [f for f in os.listdir(image_folder) if os.path.isdir(os.path.join(image_folder, f))]

    if not folders:
        messagebox.showinfo("No Folders", "No saved folders found in 'Print Data'.")
        root.deiconify()
        viewer_win.destroy()
        return

    index = 0
    image_files = []
    current_folder = None
    warning_shown_next = False
    warning_shown_prev = False

    img_label = None
    file_name_label = None

    def show_folder_list():
        """Display all folders inside 'Print Data' with image counts."""
        for widget in viewer_win.winfo_children():
            widget.destroy()

        tk.Label(viewer_win, text="Select a Folder", font=("Arial", 14, "bold"), bg="#DDEEFF").pack(pady=10)

        for folder in folders:
            folder_path = os.path.join(image_folder, folder)
            image_count = sum(
                1 for file in os.listdir(folder_path)
                if file.lower().endswith((".png", ".jpg", ".jpeg"))
            )
            folder_display_name = f"{folder} ({image_count} image{'s' if image_count != 1 else ''})"

            folder_btn = tk.Button(
                viewer_win, text=folder_display_name, font=("Arial", 12), bg="white", width=35,
                command=lambda f=folder: show_images_in_folder(f)
            )
            folder_btn.pack(pady=5)

        # 🔽 Add this at the end to show Open Folder button for base folder
        open_folder_btn = tk.Button(
            viewer_win, text="📂 Open Print Data Folder", font=("Arial", 12, "bold"),
            bg="#6C63FF", fg="white", width=30,
            command=lambda: os.startfile(image_folder)
        )
        open_folder_btn.pack(pady=20)

    def show_images_in_folder(folder):
        nonlocal image_files, index, current_folder
        current_folder = folder
        index = 0
        image_files = []
        folder_path = os.path.join(image_folder, folder)
    
        for file in os.listdir(folder_path):
            if file.lower().endswith((".png", ".jpg", ".jpeg")):
                full_path = os.path.join(folder_path, file)
                image_files.append(full_path)
    
        # Sort image_files by modified time (newest first)
        image_files.sort(key=os.path.getmtime, reverse=True)
    
        if not image_files:
            messagebox.showinfo("No Images", f"No images found in '{folder}'.")
            return
    
        show_image_view()

    def show_image_view():
        """Build image viewer UI."""
        for widget in viewer_win.winfo_children():
            widget.destroy()

        nonlocal img_label, file_name_label

        img_label = tk.Label(viewer_win, bg="#FFFFFF")
        img_label.pack(pady=10)

        file_name_label = tk.Label(viewer_win, text="", font=("Arial", 12, "bold"), bg="#DDEEFF", fg="black")
        file_name_label.pack(pady=5)

        show_image(index)

        button_frame = tk.Frame(viewer_win, bg="#DDEEFF")
        button_frame.pack(pady=10, fill="x")

        for i in range(5):
            button_frame.columnconfigure(i, weight=1)

        tk.Button(button_frame, text="⬅ Previous", font=("Arial", 12, "bold"), bg="#007BFF",fg="black", command=prev_image).grid(row=0, column=0, padx=5, pady=10, sticky="ew")

        tk.Button(button_frame, text="🖨 Print", font=("Arial", 12, "bold"), bg="#28A745",fg="black", command=print_current_image).grid(row=0, column=1, padx=5, pady=10, sticky="ew")

        tk.Button(button_frame, text="🗑 Delete", font=("Arial", 12, "bold"), bg="#DC3545",fg="black", command=delete_current_image).grid(row=0, column=2, padx=5, pady=10, sticky="ew")
        
        tk.Button(button_frame, text="🗑 Delete all ", font=("Arial", 12, "bold"), bg="#DC3545",fg="black", command=delete_all_images).grid(row=0, column=3, padx=5, pady=10, sticky="ew")

        tk.Button(button_frame, text="Next ➡", font=("Arial", 12, "bold"), bg="#007BFF",fg="black", command=next_image).grid(row=0, column=4, padx=5, pady=10, sticky="ew")

        tk.Button(button_frame, text="🔙 Back", font=("Arial", 12, "bold"), bg="orange",fg="black", command=show_folder_list).grid(row=0, column=5, padx=5, pady=10, sticky="ew")

        viewer_win.bind("<Left>", prev_image)
        viewer_win.bind("<Right>", next_image)

    def delete_all_images():
        nonlocal image_files, index
        if not image_files:
            return
        if messagebox.askyesno("Delete All", "Are you sure you want to delete ALL images in this folder?"):
            for img_path in image_files:
                try:
                    os.remove(img_path)
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to delete {os.path.basename(img_path)}:\n{e}")
            image_files.clear()
            show_folder_list()
            messagebox.showinfo("Done", "All images deleted successfully.")   

    def show_image(idx):
        """Display image at given index along with the file name."""
        if not image_files:
            messagebox.showinfo("No Images", "No more images.")
            viewer_win.destroy()
            root.deiconify()
            return
    
        img_path = image_files[idx]
        try:
            img = Image.open(img_path)
            file_name = os.path.basename(img_path)
    
            # Check if filename contains "_print_"
            if "_print_" in file_name:
                img = img.resize((400, 250))  # Smaller size for PVC prints
            else:
                img = img.resize((400, 600))  # Default size for other images
    
            img = ImageTk.PhotoImage(img)
            img_label.config(image=img)
            img_label.image = img
            file_name_label.config(text=f"File: {file_name}")
    
        except Exception as e:
            messagebox.showerror("Error", f"Unable to open image:\n{e}")

    def next_image(event=None):
        nonlocal index, warning_shown_next
        if index < len(image_files) - 1:
            index += 1
            show_image(index)
            warning_shown_next = False
        elif not warning_shown_next:
            messagebox.showwarning("End", "This is the last image.")
            warning_shown_next = True

    def prev_image(event=None):
        nonlocal index, warning_shown_prev
        if index > 0:
            index -= 1
            show_image(index)
            warning_shown_prev = False
        elif not warning_shown_prev:
            messagebox.showwarning("Start", "This is the first image.")
            warning_shown_prev = True

    def print_current_image():
        img_path = image_files[index]
        os.startfile(img_path, "print")

    def delete_current_image():
        nonlocal index
        if not image_files:
            return
        img_path = image_files[index]
        if messagebox.askyesno("Delete", f"Delete {os.path.basename(img_path)}?"):
            os.remove(img_path)
            del image_files[index]
            if index >= len(image_files):
                index = max(0, len(image_files) - 1)
            if image_files:
                show_image(index)
            else:
                show_folder_list()
                messagebox.showinfo("No Images", "All images deleted.")

    def on_close():
        root.deiconify()
        viewer_win.destroy()

    viewer_win.protocol("WM_DELETE_WINDOW", on_close)

    show_folder_list()

def open_edit_image_window(front_img, back_img, callback=None):
    if front_img is None:
        messagebox.showerror("Error", "No document uploaded! Please upload and Select Card Type.")
        return

    global edited_front_image, edited_back_image, selection_area, rect_id, start_x, start_y, edit_history, current_image, canvas, edit_win,mode_label,inverse_mask_id  
    global original_front_image, original_back_image

    selection_area = None
    rect_id = None
    start_x, start_y = 0, 0
    edit_history = []
    current_image = "front"

    edit_win = tk.Toplevel(root)
    edit_win.title("Edit Image")

    screen_width = edit_win.winfo_screenwidth()
    screen_height = edit_win.winfo_screenheight()
    window_width, window_height = 700, 720
    x_pos = (screen_width - window_width) // 2
    y_pos = 20
    edit_win.geometry(f"{window_width}x{window_height}+{x_pos}+{y_pos}")
    edit_win.configure(bg="#DDEEFF")
    # edit_win.resizable(False, False)

    instruction_text = """ Edit Image"""

    instruction_label = tk.Label(edit_win, text=instruction_text, bg="#DDEEFF", fg="black", font=("Arial", 10, "bold"), justify="left")
    instruction_label.pack(pady=10)

    root.iconify()

    def on_close():
        root.deiconify()
        edit_win.destroy()

    edit_win.protocol("WM_DELETE_WINDOW", on_close)

    edited_front_image = front_img.copy()
    edited_back_image = back_img.copy() if back_img else None

    original_front_image = front_img.copy()
    original_back_image = back_img.copy() if back_img else None

    tk_front_img = ImageTk.PhotoImage(edited_front_image)
    tk_back_img = ImageTk.PhotoImage(edited_back_image) if edited_back_image else None

    canvas = tk.Canvas(edit_win, width=front_img.width, height=front_img.height)
    canvas.pack()
    img_id = canvas.create_image(0, 0, anchor=tk.NW, image=tk_front_img)
    canvas.image = tk_front_img

    def toggle_image():
        nonlocal img_id
        global current_image

        if current_image == "front" and edited_back_image:
            current_image = "back"
            canvas.itemconfig(img_id, image=tk_back_img)
            canvas.image = tk_back_img
            toggle_btn.config(text="Show Front Image")
        else:
            current_image = "front"
            canvas.itemconfig(img_id, image=tk_front_img)
            canvas.image = tk_front_img
            toggle_btn.config(text="Show Back Image")

    def draw_selection(mode="normal"):
        global selection_area, rect_id, start_x, start_y, apply_mode, inverse_mask_id

        selection_area = None
        rect_id = None
        apply_mode = mode

        # Update mode label
        mode_label.config(text=f"Selection Mode: {'Inside Area' if mode == 'normal' else 'Outside Area'}")

        if inverse_mask_id:
            for rid in inverse_mask_id:
                canvas.delete(rid)
            inverse_mask_id = None

        def on_press(event):
            global start_x, start_y
            start_x, start_y = event.x, event.y

            if rect_id:
                canvas.delete(rect_id)

        def on_drag(event):
            global rect_id
            x1, y1 = start_x, start_y
            x2, y2 = event.x, event.y

            if rect_id:
                canvas.coords(rect_id, x1, y1, x2, y2)
            else:
                rect_id = canvas.create_rectangle(x1, y1, x2, y2, outline="red", width=2)

        def on_release(event):
            global selection_area, inverse_mask_id
            x1, y1 = start_x, start_y
            x2, y2 = event.x, event.y
            selection_area = (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))

            if apply_mode == "inverted":
                draw_inverse_mask()

            canvas.unbind("<ButtonPress-1>")
            canvas.unbind("<B1-Motion>")
            canvas.unbind("<ButtonRelease-1>")

        canvas.bind("<ButtonPress-1>", on_press)
        canvas.bind("<B1-Motion>", on_drag)
        canvas.bind("<ButtonRelease-1>", on_release)

    def draw_inverse_mask():
        global selection_area, inverse_mask_id

        if selection_area is None:
            return

        inverse_mask_id = []
        x1, y1, x2, y2 = map(int, selection_area)

        # Show mask only inside selection
        inverse_mask_id.append(canvas.create_rectangle(x1, y1, x2, y2, fill="black", stipple="gray25", outline="red"))

    def apply_adjustment():
        global edited_front_image, edited_back_image, selection_area, edit_history, already_warned_no_selection
        
        if selection_area is None:
            return

        if current_image == "front":
            edit_history.append(edited_front_image.copy())
        else:
            edit_history.append(edited_back_image.copy())

        brightness_factor = brightness_slider.get()
        contrast_factor = contrast_slider.get()
        x1, y1, x2, y2 = selection_area

        image_to_edit = edited_front_image if current_image == "front" else edited_back_image
        modified_image = image_to_edit.copy()

        if apply_mode == "normal":
            selected = modified_image.crop((x1, y1, x2, y2))
            selected = ImageEnhance.Brightness(selected).enhance(brightness_factor)
            selected = ImageEnhance.Contrast(selected).enhance(contrast_factor)
            modified_image.paste(selected, (x1, y1))
        elif apply_mode == "inverted":
            modified_image = ImageEnhance.Brightness(modified_image).enhance(brightness_factor)
            modified_image = ImageEnhance.Contrast(modified_image).enhance(contrast_factor)
            safe_area = image_to_edit.crop((x1, y1, x2, y2))
            modified_image.paste(safe_area, (x1, y1))

        tk_new_img = ImageTk.PhotoImage(modified_image)
        canvas.itemconfig(img_id, image=tk_new_img)
        canvas.image = tk_new_img

        if current_image == "front":
            edited_front_image = modified_image
        else:
            edited_back_image = modified_image

        if inverse_mask_id:
            for rid in inverse_mask_id:
                canvas.delete(rid)
            inverse_mask_id.clear()

    def convert_to_bw():
        global edited_front_image, edited_back_image, edit_history

        if current_image == "front":
            edit_history.append(edited_front_image.copy())
            bw_img = edited_front_image.convert("L").convert("RGB")
            edited_front_image = bw_img
            tk_img = ImageTk.PhotoImage(bw_img)
        else:
            if not edited_back_image:
                messagebox.showerror("Error", "No back image to convert.")
                return
            edit_history.append(edited_back_image.copy())
            bw_img = edited_back_image.convert("L").convert("RGB")
            edited_back_image = bw_img
            tk_img = ImageTk.PhotoImage(bw_img)

        canvas.itemconfig(img_id, image=tk_img)
        canvas.image = tk_img

    def undo_last_adjustment():
        global edited_front_image, edited_back_image, edit_history
        if edit_history:
            if current_image == "front":
                edited_front_image = edit_history.pop()
                tk_new_img = ImageTk.PhotoImage(edited_front_image)
            else:
                edited_back_image = edit_history.pop()
                tk_new_img = ImageTk.PhotoImage(edited_back_image)

            canvas.itemconfig(img_id, image=tk_new_img)
            canvas.image = tk_new_img
        else:
            messagebox.showerror("Error", "No previous adjustment to undo.")

    def save_image():
        global inverse_mask_id
        front_image_data = BytesIO()
        edited_front_image.save(front_image_data, format="PNG")

        if edited_back_image:
            back_image_data = BytesIO()
            edited_back_image.save(back_image_data, format="PNG")
        else:
            back_image_data = None

        global selection_area, rect_id
        selection_area = None

        if rect_id:
            canvas.delete(rect_id)
            rect_id = None
        
        # Clear inverse mask if exists
        if inverse_mask_id:
            for mask in inverse_mask_id:
                canvas.delete(mask)
            inverse_mask_id = None

        brightness_slider.set(1.0)
        contrast_slider.set(1.0)
        mode_label.config(text="Selection Mode: ")

        return front_image_data, back_image_data
    
    def undo_all_adjustments():
        global edited_front_image, edited_back_image, edit_history

        if current_image == "front":
            edited_front_image = original_front_image.copy()
            tk_img = ImageTk.PhotoImage(edited_front_image)
        else:
            if not original_back_image:
                messagebox.showerror("Error", "No back image to reset.")
                return
            edited_back_image = original_back_image.copy()
            tk_img = ImageTk.PhotoImage(edited_back_image)

        edit_history.clear()

        canvas.itemconfig(img_id, image=tk_img)
        canvas.image = tk_img

    def update_and_close():
        front_image_data, back_image_data = save_image()

        front_image = Image.open(front_image_data)
        back_image = Image.open(back_image_data) if back_image_data else None

        update_images_to_boxes(front_image, back_image)
        root.deiconify()
        edit_win.destroy()
        if callback:
            callback(front_image, back_image)


    mode_label = tk.Label(edit_win, text="Selection Mode:   ", bg="#DDEEFF", fg="blue", font=("Arial", 10, "bold"))
    mode_label.pack()

    button_frame = tk.Frame(edit_win, bg="#DDEEFF")
    button_frame.pack(pady=5)

    selection_btn = tk.Button(button_frame, text="Inside Area", command=lambda: draw_selection("normal"), bg="#4CAF50", fg="white", font=("Arial", 12, "bold"))
    selection_btn.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

    apply_inverted_btn = tk.Button(button_frame, text="Outside Area", command=lambda: draw_selection("inverted"), bg="#FF5722", fg="white", font=("Arial", 12, "bold"))
    apply_inverted_btn.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

    undo_btn = tk.Button(button_frame, text="Undo", command=undo_last_adjustment, bg="#FF9800", fg="white", font=("Arial", 12, "bold"))
    undo_btn.grid(row=0, column=2, padx=5, pady=5, sticky="ew")

    undo_all_btn = tk.Button(button_frame, text="Undo All", command=undo_all_adjustments, bg="#607D8B", fg="white", font=("Arial", 12, "bold"))
    undo_all_btn.grid(row=0, column=3, padx=5, pady=5, sticky="ew")

    toggle_btn = tk.Button(button_frame, text="Show Back Image", command=toggle_image, bg="#FFC107", fg="white", font=("Arial", 12, "bold"))
    toggle_btn.grid(row=1, column=0, padx=5, pady=5, sticky="ew")

    bw_btn = tk.Button(button_frame, text="B&W for Print", command=convert_to_bw, bg="#9C27B0", fg="white", font=("Arial", 12, "bold"))
    bw_btn.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

    save_btn = tk.Button(button_frame, text="Save", command=save_image, bg="#4CAF50", fg="white", font=("Arial", 12, "bold"))
    save_btn.grid(row=1, column=2, padx=5, pady=5, sticky="ew")

    update_btn = tk.Button(button_frame, text="Update & Close", command=update_and_close, bg="#2196F3", fg="white", font=("Arial", 12, "bold"))
    update_btn.grid(row=1, column=3, padx=5, pady=5, sticky="ew")

    brightness_slider = tk.Scale(edit_win, from_=0.8, to=1.2, resolution=0.02, orient='horizontal', label='Brightness', length=300, command=lambda v: update_adjustments(), bg="lightblue", fg="black", font=("Arial", 10, "bold")); brightness_slider.set(1.0); brightness_slider.pack(pady=5)
    brightness_slider.set(1.0)
    brightness_slider.pack(pady=5)

    contrast_slider = tk.Scale(edit_win, from_=0.8, to=1.2, resolution=0.02, orient='horizontal', label='Contrast', length=300, command=lambda v: update_adjustments(), bg="lightcoral", fg="black", font=("Arial", 10, "bold")); contrast_slider.set(1.0); contrast_slider.pack(pady=5)
    contrast_slider.set(1.0)
    contrast_slider.pack(pady=5)

    def update_adjustments():
        apply_adjustment()

def initialize_image_boxes():
    """Initialize front and back image boxes with a placeholder image and 'No Image' text."""
    global front_image_box, back_image_box

    DISPLAY_WIDTH = 357
    DISPLAY_HEIGHT = 225

    # Create a white placeholder image
    placeholder_img = Image.new("RGB", (DISPLAY_WIDTH, DISPLAY_HEIGHT), color="white")
    draw = ImageDraw.Draw(placeholder_img)

    # Load font
    try:
        font = ImageFont.truetype("arial.ttf", 24)
    except:
        font = ImageFont.load_default()

    # Calculate bounding box of the text
    text = "No Image"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (DISPLAY_WIDTH - text_width) // 2
    y = (DISPLAY_HEIGHT - text_height) // 2

    # Draw text in the center
    draw.text((x, y), text, fill="gray", font=font)

    # Convert to PhotoImage and update labels
    placeholder_tk = ImageTk.PhotoImage(placeholder_img)
    front_image_box.config(image=placeholder_tk)
    front_image_box.image = placeholder_tk
    back_image_box.config(image=placeholder_tk)
    back_image_box.image = placeholder_tk

def upload_document_for_crop(card_side):
    global file_path, doc, attempts, password_window, crop_card_side,current_crop_step
    crop_card_side = card_side  # Save side so cropping can continue after password

    file_path = filedialog.askopenfilename(filetypes=[("Image or PDF", "*.jpg *.jpeg *.png *.pdf")])
    if not file_path:
        if crop_card_side == "back":
            current_crop_step = 0  # Reset the flow if user cancels during back side upload
        return
    
    filename = file_path.split('/')[-1]
    truncated_filename = filename[:20] + "..." if len(filename) > 20 else filename
    label.config(text=f"File Name: {truncated_filename}", font=("Arial", 10, "bold"))
    
    attempts = 3

    if 'password_window' in globals() and password_window.winfo_exists():
        password_window.destroy()

    if file_path.lower().endswith(".pdf"):
        doc = fitz.open(file_path)
        if doc.is_encrypted:
            show_password_window()
        else:
            load_first_page_for_crop()
    else:
        img = Image.open(file_path)
        show_crop_preview(img, card_side)
        
def load_first_page_for_crop():
    try:
        first_page = doc.load_page(0)
        pix = first_page.get_pixmap(dpi=300)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        show_crop_preview(img, crop_card_side)
    except Exception as e:
        pass

def show_crop_preview(original_image, card_side):
    if original_image is None:
        return

    image_width, image_height = original_image.size
    if image_width <= 0 or image_height <= 0:
        return

    global crop_window
    root.iconify()  # Minimize root window

    crop_window = tk.Toplevel(root)
    crop_window.title(f"Crop and Rotate - {card_side.capitalize()}")
    crop_window.resizable(True, True)

    # Center the crop window
    screen_width = crop_window.winfo_screenwidth()
    screen_height = crop_window.winfo_screenheight()
    crop_window.geometry(f'1400x700+{int((screen_width - 1400) / 2)}+20')

    def on_crop_window_close():
        root.deiconify()  # Restore root window
        crop_window.destroy()

    crop_window.protocol("WM_DELETE_WINDOW", on_crop_window_close)

    main_frame = Frame(crop_window)
    main_frame.pack(fill=tk.BOTH, expand=True)

    preview_frame = Frame(main_frame)
    preview_frame.pack(side="left", fill=tk.BOTH, expand=True)

    button_frame = Frame(main_frame, width=200, bg="#DDEEFF")
    button_frame.pack(side="right", fill=tk.Y)

    canvas_container = Frame(preview_frame)
    canvas_container.pack(fill=tk.BOTH, expand=True)

    canvas = Canvas(canvas_container, cursor="cross")
    canvas.pack(side="left", fill=tk.BOTH, expand=True)

    scrollbar_y = Scrollbar(canvas_container, orient="vertical", command=canvas.yview, width=20)
    scrollbar_y.pack(side="right", fill="y")

    scrollbar_x = Scrollbar(preview_frame, orient="horizontal", command=canvas.xview, width=20)
    scrollbar_x.pack(side="bottom", fill="x")

    canvas.config(xscrollcommand=scrollbar_x.set, yscrollcommand=scrollbar_y.set)

    def on_mouse_wheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    canvas.bind("<MouseWheel>", on_mouse_wheel)
    canvas.bind("<Configure>", lambda e: canvas.config(scrollregion=canvas.bbox("all")))

    zoom_factor = 1.0
    angle_var = tk.DoubleVar(value=0)
    tk_img = None
    points = []

    def update_canvas_image(pil_img):
        nonlocal tk_img
        tk_img = ImageTk.PhotoImage(pil_img)
        canvas.delete("all")
        canvas.create_image(0, 0, anchor="nw", image=tk_img)
        canvas.config(scrollregion=(0, 0, pil_img.width, pil_img.height))
        canvas.image = tk_img

    def get_transformed_image():
        rotated = original_image.rotate(angle_var.get(), expand=True)
        zoomed = rotated.resize(
            (int(rotated.width * zoom_factor), int(rotated.height * zoom_factor)),
            Image.LANCZOS
        )
        return zoomed

    def rotate_image(delta):
        angle_var.set(angle_var.get() + delta)
        update_canvas_image(get_transformed_image())

    def zoom_in():
        nonlocal zoom_factor
        zoom_factor *= 1.1
        update_canvas_image(get_transformed_image())

    def zoom_out():
        nonlocal zoom_factor
        zoom_factor /= 1.1
        update_canvas_image(get_transformed_image())

    def reset_crop():
        nonlocal zoom_factor
        angle_var.set(0)
        update_canvas_image(get_transformed_image())
        points.clear()

    def start_crop():
        points.clear()
        canvas.delete("all")
        update_canvas_image(get_transformed_image())
        canvas.bind("<Button-1>", select_point)

    def select_point(event):
        if len(points) < 4:
            canvas_x = canvas.canvasx(event.x)
            canvas_y = canvas.canvasy(event.y)
            points.append((canvas_x, canvas_y))
            canvas.create_oval(canvas_x - 5, canvas_y - 5, canvas_x + 5, canvas_y + 5, fill='red')

        if len(points) == 4:
            # Draw polygon (box) connecting the 4 points
            canvas.create_polygon(points, outline='Red', fill='', width=3)

    def confirm_crop():
        if len(points) != 4:
            messagebox.showwarning("Incomplete Selection", "Please select exactly 4 points before confirming.")
            return
        apply_perspective_crop()
        root.deiconify()
        
    def apply_perspective_crop():
        rotated = original_image.rotate(angle_var.get(), expand=True)
        zoomed = rotated.resize((int(rotated.width * zoom_factor), int(rotated.height * zoom_factor)),Image.LANCZOS)
        canvas_display_width = zoomed.width
        canvas_display_height = zoomed.height
        actual_width = rotated.width
        actual_height = rotated.height

        ratio_x = actual_width / canvas_display_width
        ratio_y = actual_height / canvas_display_height

        mapped_points = [(x * ratio_x, y * ratio_y) for (x, y) in points]

        dst_size = (600, 400)
        dst_points = [(0, 0), (dst_size[0], 0), (dst_size[0], dst_size[1]), (0, dst_size[1])]

        matrix = cv2.getPerspectiveTransform(np.float32(mapped_points), np.float32(dst_points))
        rotated_np = np.array(rotated)
        warped = cv2.warpPerspective(rotated_np, matrix, dst_size)
        cropped_pil = Image.fromarray(warped)

        global current_crop_step
        if card_side == "front":
            update_images_to_boxes(cropped_pil, None)
            messagebox.showinfo("Next Step", "✅ Front image cropped.\n\n📄 Now please upload the second document for the back image.")
            current_crop_step = 1
            crop_window.destroy()
            root.deiconify()
            # Delay 1 seconds before triggering next document upload
            root.after(500, lambda: upload_document_for_crop("back"))
        else:
            update_images_to_boxes(None, cropped_pil)
            current_crop_step = 0
            crop_window.destroy()

    # Init image
    zoom_factor = min(preview_frame.winfo_width() / image_width, preview_frame.winfo_height() / image_height)
    if zoom_factor < 0.5:
        zoom_factor = 0.5
    update_canvas_image(get_transformed_image())

    # BUTTONS PANEL
    rotate_left_btn = tk.Button(button_frame, text="⟲ Rotate Left", command=lambda: rotate_image(-10),font=("Arial", 12, "bold"), bg="#007BFF", fg="white")
    rotate_left_btn.pack(side="top", padx=10, pady=5, fill="x")

    rotate_right_btn = tk.Button(button_frame, text="⟳ Rotate Right", command=lambda: rotate_image(10),font=("Arial", 12, "bold"), bg="#007BFF", fg="white")
    rotate_right_btn.pack(side="top", padx=10, pady=5, fill="x")

    divider0 = tk.Frame(button_frame, height=2, bd=1, relief="sunken", bg="grey")
    divider0.pack(fill="x", padx=5, pady=5)

    zoom_in_btn = tk.Button(button_frame, text="🔍➕ Zoom In", command=zoom_in,font=("Arial", 12, "bold"), bg="#28A745", fg="white")
    zoom_in_btn.pack(side="top", padx=10, pady=5, fill="x")

    zoom_out_btn = tk.Button(button_frame, text="🔍➖ Zoom Out", command=zoom_out,font=("Arial", 12, "bold"), bg="#DC3545", fg="white")
    zoom_out_btn.pack(side="top", padx=10, pady=5, fill="x")

    divider1 = tk.Frame(button_frame, height=2, bd=1, relief="sunken", bg="grey")
    divider1.pack(fill="x", padx=5, pady=5)

    crop_btn = tk.Button(button_frame, text="✂️ Crop", command=start_crop,font=("Arial", 12, "bold"), bg="#FFC107", fg="white")
    crop_btn.pack(side="top", padx=10, pady=5, fill="x")

    confirm_btn = tk.Button(button_frame, text="✅ Confirm Crop", command=confirm_crop,font=("Arial", 12, "bold"), bg="green", fg="white")
    confirm_btn.pack(side="top", padx=10, pady=5, fill="x")

    reset_btn = tk.Button(button_frame, text="🔄 Reset Crop", command=reset_crop,font=("Arial", 12, "bold"), bg="orange", fg="white")
    reset_btn.pack(side="top", padx=10, pady=5, fill="x")

    crop_window.mainloop()

def handle_crop_and_print():
    refresh_all(show_message=False)
    messagebox.showinfo("Upload Front", "Please upload the first document for the front image.")
    global current_crop_step
    if current_crop_step == 0:
        upload_document_for_crop("front")
    elif current_crop_step == 1:
        upload_document_for_crop("back")

def toggle_mode():
    current = is_multi_card_mode.get()
    is_multi_card_mode.set(not current)  # Flip the boolean

    if is_multi_card_mode.get():
        toggle_button.config(text="Multi Card Mode: ON", bg="green", fg="white")
    else:
        toggle_button.config(text="Multi Card Mode: OFF", bg="red", fg="white")

def refresh_all(show_message=True):
    global file_path, doc, crop_card_side, current_crop_step
    global password_window, crop_window, edit_win, preview_window
    global selected_card_name, front_img_global, back_img_global
    global images, current_pdf_page_index
    global edited_front_image, edited_back_image, original_front_image, original_back_image

    # Reset core variables
    file_path = None
    doc = None
    crop_card_side = None
    current_crop_step = 0
    selected_card_name = None
    front_img_global = None
    back_img_global = None
    images = []
    current_pdf_page_index = 0
    edited_front_image = None
    edited_back_image = None
    original_front_image = None
    original_back_image = None

    # Destroy Edit Window if open
    try:
        if edit_win and edit_win.winfo_exists():
            edit_win.destroy()
    except:
        pass

    # Reset image boxes
    update_images_to_boxes(None, None)
    initialize_image_boxes()

    # UI reset
    try:
        label.config(text="No File Uploaded", font=("Arial", 10, "bold"))
    except:
        pass

    if show_message:
        messagebox.showinfo("Reset", "Application has been refreshed.")

# GUI Setup
root = tk.Tk()
root.title("Multi Print ID Card Tool")
# Centering the main window on the screen
width = 760
height = 730

screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()

root.resizable(False, False)  # Disable resizing of the main window

selected_document_type = tk.StringVar(value="Crop and print")  # Ensure this is initialized
Reverse_var = tk.BooleanVar(value=Reverse_state) 
Mirror_var = tk.BooleanVar(value=mirror_state)

# Calculate the position to center the window
x_position = (screen_width // 2) - (width // 2)
y_position = 0

root.geometry(f"{width}x{height}+{x_position}+{y_position}")

root.configure(bg="#DDEEFF")

file_path = None  # Global variable to store uploaded file path

# Create a frame for the buttons on the left
frame = Frame(root, bd=2, relief=tk.RIDGE, bg="#FFFFFF")
frame.grid(row=1, column=0, padx=20, pady=5, sticky="nsw")  # Ensures it stays on the left

# Upload Document Button
upload_btn = tk.Button(frame, text="🖼 Upload Document", command=upload_doc, font=("Arial", 12, "bold"), bg="#007BFF", fg="white")
upload_btn.grid(row=0, column=0, pady=(6,2), padx=10, sticky="ew")

# Label to show the file status
label = tk.Label(frame, text="No file uploaded", bg="#FFFFFF", font=("Arial", 10, "bold"))
label.grid(row=1, column=0, pady=(1,1))

button_frame = Frame(frame, bg="#FFFFFF")  # Removed height to allow auto-fit
button_frame.grid(row=2, column=0, pady=(1,1), padx=5, sticky="w")  # Align left
refresh_buttons()  # Load buttons dynamically

# Frame to hold both buttons side by side
button_frame3 = tk.Frame(frame)
button_frame3.grid(row=7, column=0, columnspan=2, pady=10, padx=10, sticky="ew")

# Configure columns for equal spacing
button_frame3.grid_columnconfigure(0, weight=1)
button_frame3.grid_columnconfigure(1, weight=1)

# Edit Image Button
edit_image_btn = tk.Button(button_frame3, text="🛠 Edit Image", font=("Arial", 12, "bold"),bg="#1b4ce3", fg="white",command=lambda: open_edit_image_window(current_front_image, current_back_image))
edit_image_btn.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

# Crop and Print Button
crop_and_print_btn = tk.Button(button_frame3, text="Crop and Print", font=("Arial", 12, "bold"),bg="#e803fc", fg="white",command=handle_crop_and_print)
crop_and_print_btn.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

# Main Layout (2 columns: Left for Buttons, Right for Images)
root.grid_columnconfigure(0, weight=0)  # Left Panel
root.grid_columnconfigure(1, weight=1)  # Right Panel (Image Frame should NOT expand infinitely)

# Frame for displaying front and back images (Right Side)
image_frame = Frame(root, width=400, height=650, bd=2, relief=tk.RIDGE, bg="#FFFFFF")
image_frame.grid(row=1, column=1, padx=0, pady=5, sticky="nw")
image_frame.grid_propagate(False)  # Prevent the frame from resizing based on content

# Label for the front image
front_label_text = tk.Label(image_frame, text="Front Image", bg="#D9F9D8", relief="solid",width=35, height=2, font=("Arial", 12, "bold"))
front_label_text.grid(row=0, column=0, padx=10, pady=(10, 2))

# Image box for front image
front_image_box = tk.Label(image_frame, bg="#FFFFFF", relief="solid")
front_image_box.grid(row=1, column=0, padx=20, pady=(15, 10))

# Label for the back image
back_label_text = tk.Label(image_frame, text="Back Image", bg="#F9D8D8", relief="solid",width=35, height=2, font=("Arial", 12, "bold"))
back_label_text.grid(row=2, column=0, padx=10, pady=(10, 2))

# Image box for back image
back_image_box = tk.Label(image_frame, bg="#FFFFFF", relief="solid")
back_image_box.grid(row=3, column=0, padx=10, pady=(15, 10))

initialize_image_boxes()
check_for_updates(silent=True)

top_right_frame = tk.Frame(root, bg="#DDEEFF")
top_right_frame.grid(row=0, column=0, columnspan=2, sticky="ne", padx=10, pady=5)

# # Multi Card Mode Toggle Button (placed next to Restart)
is_multi_card_mode = tk.BooleanVar(value=False)
# Custom Toggle Button
toggle_button = tk.Button(top_right_frame,text="Multi Card Mode: OFF",font=("Arial", 10, "bold"),bg="red", fg="white",width=20, height=1,command=toggle_mode)
toggle_button.grid(row=0, column=0, sticky="ne", padx=10, pady=5)

# Settings Button
settings_btn = tk.Button(top_right_frame, text="⚙ Settings", font=("Arial", 10, "bold"), bg="#007BFF", fg="white", command=open_settings)
settings_btn.grid(row=0, column=1, sticky="ne", padx=10, pady=5)

#Refresh all
refresh_btn = tk.Button(top_right_frame, text="🔄 Refresh All", command=refresh_all, bg="#FF5733", fg="white", font=("Arial", 10, "bold"))
refresh_btn.grid(row=0, column=2, sticky="ne", padx=10, pady=5)

#Restart Button
restart_btn = tk.Button(top_right_frame, text="🔄 Restart", font=("Arial", 10, "bold"), bg="#DC3545", fg="white", command=restart_ui)
restart_btn.grid(row=0, column=3, sticky="ne", padx=10, pady=5)

# New Frame for Left Side
top_left_frame = tk.Frame(root, bg="#DDEEFF")
top_left_frame.grid(row=0, column=0, sticky="nw", padx=10, pady=15)

# Time and Date Label (12-hour format)
time_label = tk.Label(top_left_frame, font=("Arial", 13, "bold"), bg="#DDEEFF", fg="#333")
time_label.pack(anchor="w")  # Align left inside frame

def update_time():
    current_time = time.strftime("%I:%M:%S %p")  # 12-hour format with AM/PM
    current_date = time.strftime("%d-%m-%Y")
    time_label.config(text=f"{current_time} | {current_date}")
    top_left_frame.after(1000, update_time)

update_time()

# Frame to hold the buttons
button_frame2 = tk.Frame(frame)

# Ensure frame has a fixed height
button_frame2.configure(height=40)
button_frame2.grid_propagate(False)

# Configure columns for equal space distribution
button_frame2.grid_columnconfigure(0, weight=1)
button_frame2.grid_columnconfigure(1, weight=1)

# Print Preview + Print buttons grouped
button_frame2 = tk.LabelFrame(frame, text="Print Options", bg="#FFFFFF", font=("Arial", 10, "bold"), bd=2, relief="groove")
button_frame2.grid(row=10, column=0, columnspan=2, pady=5, padx=10, sticky="ew")
button_frame2.grid_columnconfigure(0, weight=1)
button_frame2.grid_columnconfigure(1, weight=1)

# Paper Size Selection (moved inside button_frame2)
selected_paper_size = tk.StringVar(value="4x6")  # Default to 4x6 paper
tk.Label(button_frame2, text="Select Paper Size:", font=("Arial", 10, "bold"), bg="#FFFFFF").grid(row=0, column=0, padx=10, pady=5, sticky="w", columnspan=2)
paper_dropdown = ttk.Combobox(button_frame2, textvariable=selected_paper_size, state="readonly", width=12, font=("Arial", 10, "bold"))
paper_dropdown["values"] = ["PVC Card","4x6 Paper", "A4 Paper","A4 Paper U+D","A4 Paper L+R"]#"A4 Paper Full"
paper_dropdown.current(0)
paper_dropdown.grid(row=0, column=1, columnspan=2, padx=5, pady=5, sticky="ew")

preview_button = tk.Button(button_frame2, text="🔍Print Preview", font=("Arial", 12, "bold"), bg="#6F42C1", fg="white", command=show_print_preview)
preview_button.grid(row=1, column=0, padx=10, pady=5, sticky="ew")

print_btn = tk.Button(button_frame2, text="🖨 Print", font=("Arial", 12, "bold"), bg="#6F42C1", fg="white", command=print_id_card)
print_btn.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

# View Saved Images Button
view_images_btn = tk.Button(frame, text="🖼 View Saved Images", font=("Arial", 12, "bold"), bg="#28A745", fg="white", command=open_image_viewer)
view_images_btn.grid(row=11, column=0, pady=10, padx=10, sticky="ew")

# Button to check for updates
update_btn = tk.Button(frame, text="🔄 Check for Updates",font=("Arial", 12, "bold"), bg="#007BFF", fg="white", command=lambda: check_for_updates(silent=False))
update_btn.grid(row=12, column=0, pady=10, padx=10, sticky="ew")

# Label to show current version
current_version = tk.StringVar()
current_version.set(f"Current Version: {get_current_version()}")
version_label = tk.Label(frame, textvariable=current_version, font=("Arial", 10, "bold"))
version_label.grid(row=13, column=0, columnspan=2, pady=5)

progress_bar = ttk.Progressbar(frame, orient="horizontal", length=200, mode="determinate")
progress_label = tk.Label(frame, text="", font=("Arial", 9))
progress_bar.grid(pady=5)
progress_label.grid()
progress_bar.grid_remove()
progress_label.grid_remove()

root.mainloop()

# PDF IMAGE ZOOM update images PASSWORD crop multi cordinates + overwrite + load & crop same WORKING TILL HERE ...!!
# setting menu in centre, 3 tabs delete crop data, Buttons Rename ,Image Setting (Reverse,mirror) + fixed preview window close issue ...!
# Print Window Default Print & Preview A4,4x6 ,auto Card name in print output folder.
# Restart & in crop Front and Back Popup added  
# crop button hide after 1st crop.
# image Viewer updated with Print Option , fixed image resize to boxes, folder name now image number too + open image folder location+Sort image(New to old)+Delete All
# image editer also added. Image Quality Improved,select inverse fixed.
# Github Auto update feature added + silent update 
# multi page crop page number , confirm crop , scroll bar fixed
# UI change + add/Delete ID Added 
# New_crop_and_print_with_new_2_new_A4_Paper,output folder as Crop and print set.
# New_multi_ID_card_Print_on_A4_sheet+edit_image 
# PVC Card Print One by One Print Open EPson Photo+