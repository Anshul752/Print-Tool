import tkinter as tk
import fitz,json,os,sys,threading,requests,os,sys,shutil,subprocess,time
from tkinter import filedialog, Toplevel, Canvas, Scrollbar, Frame, messagebox,ttk
from PIL import Image, ImageTk,ImageDraw,ImageEnhance,ImageFont
from datetime import datetime
from io import BytesIO

doc = None  # Global variable to store the loaded document
file_path = None  # Global variable to store the file path
zoom_level = 2.0  # Default zoom level
attempts = 3  # Global variable to track the number of attempts
crop_coordinates = {}
preview_window = None  # Initialize globally
Settings = "Settings.json"  # Store all settings in this file
crop_btn = None  # Initialize crop_btn as None
current_front_image = None
current_back_image = None
front_cropped_img=None
back_cropped_img=None
apply_mode = "normal"         # "normal" or "inverted"
inverse_mask_id = None        # list of canvas rect IDs
selection_area = None
rect_id = None

# URLs for update files
VERSION_URL = "https://raw.githubusercontent.com/Anshul752/Print-Tool/main/version.txt"
EXE_URL = "https://raw.githubusercontent.com/Anshul752/Print-Tool/main/latest.exe"
LOCAL_VERSION_FILE = "version.txt"
NEW_EXE_NAME = "update.exe"  # Temporary update file
OLD_EXE_NAME = "ID_Print_tool.exe"  # Current running EXE name

def get_latest_version():
    """Fetch the latest version from GitHub."""
    try:
        response = requests.get(VERSION_URL)
        response.raise_for_status()
        return response.text.strip()
    except Exception as e:
        messagebox.showerror("Error", f"Update check failed: {e}")
        return None

def get_current_version():
    """Read the local version of the program."""
    if os.path.exists(LOCAL_VERSION_FILE):
        with open(LOCAL_VERSION_FILE, "r") as f:
            return f.read().strip()
    return "1.0"  # Default version

def download_update():
    """Download the updated exe file."""
    try:
        response = requests.get(EXE_URL, stream=True)
        response.raise_for_status()

        with open(NEW_EXE_NAME, "wb") as f:
            shutil.copyfileobj(response.raw, f)

        if os.path.exists(NEW_EXE_NAME) and os.path.getsize(NEW_EXE_NAME) > 10000:  # Check size to prevent corruption
            messagebox.showinfo("Update", "Update downloaded successfully! Restarting...")
            return True
        else:
            messagebox.showerror("Error", "Update download failed. File is incomplete.")
            return False

    except Exception as e:
        messagebox.showerror("Error", f"Update download failed: {e}")
        return False

def apply_update():
    """Replace the old exe with the new one and restart."""
    new_exe_path = os.path.join(os.getcwd(), NEW_EXE_NAME)  # update.exe
    old_exe_path = os.path.join(os.getcwd(), OLD_EXE_NAME)  # ID_Print_tool.exe

    if os.path.exists(new_exe_path):
        messagebox.showinfo("Update", "Restarting to apply update...")

        # ✅ Save new version number before restarting
        new_version = get_latest_version()
        with open(LOCAL_VERSION_FILE, "w") as f:
            f.write(new_version)

        # ✅ Create update script that:
        # 1. Waits
        # 2. Overwrites EXE using `copy /y`
        # 3. Deletes update.exe and .bat file
        # 4. Restarts the EXE
        update_script = f"""
        @echo off
        timeout /t 2 >nul
        copy /y "{NEW_EXE_NAME}" "{OLD_EXE_NAME}"
        del "{NEW_EXE_NAME}"
        start "" "{OLD_EXE_NAME}"
        del "%~f0"
        """

        # Save the script as a .bat file and run it
        bat_file = "update_script.bat"
        with open(bat_file, "w") as f:
            f.write(update_script)

        subprocess.Popen(bat_file, shell=True)
        sys.exit()  # Close the old app to allow update
    else:
        messagebox.showerror("Update Error", "Update file not found! Please rename manually")


def update_version_label():
    """Update the version label dynamically after update."""
    current_version.set(f"Current Version: {get_current_version()}")

def check_for_updates():
    """Check and apply updates if available."""
    latest_version = get_latest_version()
    current_version_value = get_current_version()  # Get actual value

    if latest_version and latest_version > current_version_value:
        if messagebox.askyesno("Update Available", f"A new version ({latest_version}) is available.\nDo you want to update?"):
            if download_update():
                apply_update()
                update_version_label()  # ✅ Update the UI version after update!
    else:
        messagebox.showinfo("No Updates", "You already have the latest version.")

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
    global front_crop, back_crop, img, img_tk, canvas, front_crop_selected, file_path, doc, crop_btn
    global instructions

    # Reset initial states
    front_crop = None
    back_crop = None
    front_crop_selected = True

    # Check if the file is loaded
    if not file_path:
        messagebox.showerror("Error", "No file selected.")
        return

    try:
        images = []  # Make sure it's always a list

        if file_path.endswith(".pdf"):
            doc = fitz.open(file_path)
            for i in range(min(3, len(doc))):  # Load up to 3 pages
                page = doc.load_page(i)
                pix = page.get_pixmap(matrix=fitz.Matrix(zoom_level, zoom_level))
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                images.append(img)
        else:
            img = Image.open(file_path)
            images.append(img)  # Make it consistent — always a list

    except Exception as e:
        messagebox.showerror("Error", f"Failed to load image: {str(e)}")
        return

    img_tk = ImageTk.PhotoImage(img)
    canvas.delete("all")
    canvas.create_image(0, 0, anchor="nw", image=img_tk)
    canvas.config(scrollregion=canvas.bbox("all"))

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
                crop_and_display_images(front_crop, back_crop, card_name)

            canvas.unbind("<ButtonRelease-1>")
            canvas.unbind("<B1-Motion>")

        canvas.bind("<B1-Motion>", on_drag)
        canvas.bind("<ButtonRelease-1>", on_release)

    canvas.bind("<Button-1>", on_canvas_click)

def crop_and_display_images(front_crop, back_crop,card_name):
    """ Crop the selected areas (front and back) and display both cropped images on the canvas without converting or resizing. """
    global img, canvas, front_image_box, back_image_box,preview_window

    if img is None:
        messagebox.showerror("Error", "No image loaded.")
        return

    if not front_crop or not back_crop:
        messagebox.showerror("Error", "Both front and back areas must be selected.")
        return

    front_img = img.crop(tuple(front_crop))
    back_img = img.crop(tuple(back_crop))

    # Show cropped images directly in the UI without opening a preview window
    update_images_to_boxes(front_img, back_img)

    # Restore the main UI (if hidden)
    root.deiconify()

    # Convert the cropped images to PhotoImage objects for Tkinter, ensuring no resizing or quality loss
    front_img_tk = ImageTk.PhotoImage(front_img)
    back_img_tk = ImageTk.PhotoImage(back_img)

    # Clear the canvas to remove previous content
    canvas.delete("all")  # This removes all items from the canvas (including previous images and labels)

    # Display the cropped front image at position (0, 0) on the canvas
    canvas.create_image(0, 0, anchor="nw", image=front_img_tk)

    # Display the cropped back image next to the front image (on the right side)
    canvas.create_image(front_img.width + 10, 0, anchor="nw", image=back_img_tk)

    # Keep references to the images to prevent garbage collection
    canvas.front_img_tk = front_img_tk
    canvas.back_img_tk = back_img_tk

    # Save the crop coordinates to the JSON file (ID CARD Type)
    save_coordinates_to_json(card_name, {"front": front_crop, "back": back_crop})

    # Update front and back image boxes with the cropped images
    front_image_box.config(image=front_img_tk)  # Assign front image correctly
    back_image_box.config(image=back_img_tk)  # Assign back image correctly
    update_images_to_boxes(front_img, back_img)
    
    # Close preview window automatically
    if preview_window:
        preview_window.destroy()
        preview_window = None  # Reset variable
    # Show main window again
    root.deiconify()
    
def update_images_to_boxes(front_img, back_img):
    """Update the front and back image boxes with the cropped images, resizing them to fixed size."""
    global front_image_box, back_image_box, front_cropped_img, back_cropped_img, current_front_image, current_back_image

    if front_img:
        current_front_image = front_img
    if back_img:
        current_back_image = back_img

    # Reverse images before resizing if needed
    if Reverse_var.get():
        front_img, back_img = back_img, front_img

    # Mirror images if needed
    if Mirror_var.get():
        front_img = front_img.transpose(Image.FLIP_LEFT_RIGHT)
        back_img = back_img.transpose(Image.FLIP_LEFT_RIGHT)

    # Define fixed display size in pixels
    DISPLAY_WIDTH = 357
    DISPLAY_HEIGHT = 225

    # Resize images to fit fixed box size
    front_img_resized = front_img.resize((DISPLAY_WIDTH, DISPLAY_HEIGHT), Image.LANCZOS)
    back_img_resized = back_img.resize((DISPLAY_WIDTH, DISPLAY_HEIGHT), Image.LANCZOS)

    # Convert to PhotoImage
    front_img_tk = ImageTk.PhotoImage(front_img_resized)
    back_img_tk = ImageTk.PhotoImage(back_img_resized)

    # Update image boxes
    front_image_box.config(image=front_img_tk)
    back_image_box.config(image=back_img_tk)

    # Store references to prevent garbage collection
    front_image_box.image = front_img_tk
    back_image_box.image = back_img_tk

    # Save cropped originals
    front_cropped_img = front_img
    back_cropped_img = back_img


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
    tk.Label(password_window, text="Enter password to unlock PDF:", 
             font=("Arial", 12, "bold"), bg="#f8f9fa", fg="#333").pack(pady=15)

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
    submit_button = tk.Button(password_window, text="Submit", font=("Arial", 12, "bold"),
                              bg="#28a745", fg="white", padx=15, pady=5, relief="flat",
                              command=on_submit)
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
        preview_window.destroy()
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

def show_preview(file_path,card_name):
    global canvas, img_tk, preview_window

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
    window_height = 600

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
    button_frame = Frame(main_frame, width=200, bg="#f4f4f4")
    button_frame.pack(side="right", fill=tk.Y)

    # Zoom In Button
    zoom_in_btn = tk.Button(button_frame, text="🔍➕Zoom In", command=zoom_in, font=("Arial", 12), bg="#28A745", fg="white")
    zoom_in_btn.pack(side="top", padx=10, pady=10, fill="x")

    # Zoom Out Button
    zoom_out_btn = tk.Button(button_frame, text="🔍➖Zoom Out", command=zoom_out, font=("Arial", 12), bg="#DC3545", fg="white")
    zoom_out_btn.pack(side="top", padx=10, pady=10, fill="x")

    global crop_btn  # Declare as global
    crop_btn = tk.Button(button_frame, text="✂️Crop", command=lambda: crop_image(card_name),font=("Arial", 12), bg="#FFC107", fg="black")
    crop_btn.pack(side="top", padx=10, pady=10, fill="x")
    
    # Confirm Crop Button
    confirm_btn = tk.Button(button_frame, text="✅ Confirm Crop", font=("Arial", 12),bg="green", fg="white", command=lambda: confirm_crop_from_ui(card_name))
    confirm_btn.pack(side="top", padx=10, pady=5, fill="x")

    # Reset Crop Button
    reset_btn = tk.Button(button_frame, text="🔄 Reset Crop", font=("Arial", 12),bg="orange", fg="black", command=lambda: crop_image(card_name))
    reset_btn.pack(side="top", padx=10, pady=5, fill="x")

    # Canvas for displaying image or PDF preview
    canvas = Canvas(preview_frame)
    canvas.pack(fill=tk.BOTH, expand=True)  # Make the canvas fill the window

    # Scrollbars for canvas with custom width and color

    scrollbar_x = Scrollbar(preview_frame, orient="horizontal", command=canvas.xview, width=30, relief="raised")
    scrollbar_x.pack(side="bottom", fill="x")

    scrollbar_y = Scrollbar(preview_frame, orient="vertical", command=canvas.yview, width=30, relief="raised")
    scrollbar_y.pack(side="right", fill="y")

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
        
# File path for storing crop coordinates
CROP_DATA_FILE = "crop_coordinates.json"

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

    # Set window size
    win_width, win_height = 480, 500
    settings_win.geometry(f"{win_width}x{win_height}")

    # Center window on screen
    screen_width = settings_win.winfo_screenwidth()
    screen_height = settings_win.winfo_screenheight()
    
    x_pos = (screen_width - win_width) // 2
    y_pos = (screen_height - win_height) // 2

    settings_win.geometry(f"{win_width}x{win_height}+{x_pos}+{y_pos}")

    def on_close():
        """Restore main window when settings are closed."""
        root.deiconify()
        settings_win.destroy()

    settings_win.protocol("WM_DELETE_WINDOW", on_close)

    style = ttk.Style()
    style.configure("TNotebook.Tab", font=("Arial", 11, "bold"), padding=[10, 5], background="#DDEEFF")  # Normal tab
    style.map("TNotebook.Tab", background=[("selected", "#007BFF")], foreground=[("selected", "Green")])  # Highlight selected

    notebook = ttk.Notebook(settings_win, style="TNotebook")
    notebook.pack(expand=True, fill='both')

    tab1 = ttk.Frame(notebook)
    tab2 = ttk.Frame(notebook)
    tab3 = ttk.Frame(notebook)

    notebook.add(tab1, text="Manage Crop Data")
    notebook.add(tab2, text="Rename Buttons")
    notebook.add(tab3, text="Image Settings")

    # ====== TAB 1: Manage Crop Data ======
    tk.Label(tab1, text="Manage Crop Data", font=("Arial", 14, "bold"), bg="#EEEEEE").pack(pady=5)

    for card_name in list(crop_data.keys()):
        frame = tk.Frame(tab1, bg="#FFFFFF", bd=1, relief=tk.SOLID)
        frame.pack(pady=3, padx=10, fill="x")

        tk.Label(frame, text=card_name, font=("Arial", 12), bg="#FFFFFF").pack(side="left", padx=10)

        delete_btn = tk.Button(frame, text="Delete", font=("Arial", 10, "bold"), bg="#DC3545", fg="white",
                               command=lambda name=card_name: confirm_delete(name, settings_win))
        delete_btn.pack(side="right", padx=10)

    # ====== TAB 2: Rename Buttons ======
    tk.Label(tab2, text="Rename Buttons", font=("Arial", 14, "bold"), bg="#EEEEEE").pack(pady=5)
    tk.Label(tab2, text="Select Button:", font=("Arial", 11, "bold"), bg="#EEEEEE").pack(pady=2)

    selected_button_var = tk.StringVar(tab2)

    # Dropdown for selecting buttons
    selected_button_dropdown = ttk.Combobox(tab2, textvariable=selected_button_var, state="readonly",
                                            font=("Arial", 11, "bold"))
    selected_button_dropdown["values"] = [btn[0] for btn in buttons]
    selected_button_dropdown.pack(pady=2)

    tk.Label(tab2, text="New Name:", font=("Arial", 11, "bold"), bg="#EEEEEE").pack(pady=2)
    new_name_entry = tk.Entry(tab2, font=("Arial", 11, "bold"))
    new_name_entry.pack(pady=2)

    def rename_button():
        """Renames the selected button and updates the UI."""
        old_name = selected_button_var.get()
        new_name = new_name_entry.get().strip()

        if old_name and new_name:
            # ✅ Check for duplicate button names
            if new_name in [btn[0] for btn in buttons]:
                messagebox.showerror("Error", "A button with this name already exists.")
                return

            for i, (btn_text, color) in enumerate(buttons):
                if btn_text == old_name:
                    buttons[i] = (new_name, color)
                    break

            save_buttons(buttons, Reverse_var.get(), Mirror_var.get())  # ✅ Save changes
            refresh_buttons()  # ✅ Refresh UI
            settings_win.destroy()  # ✅ Close settings
            root.deiconify()

        else:
            messagebox.showerror("Error", "Please select a button and enter a new name.")

    rename_btn = tk.Button(tab2, text="Rename", font=("Arial", 12, "bold"), bg="#28A745", fg="white",
                           command=rename_button)
    rename_btn.pack(pady=10)
    

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
    Reverse_btn = tk.Button(tab3, text="Reverse: ON" if Reverse_var.get() else "Reverse: OFF",
                            font=("Arial", 12, "bold"),
                            bg="green" if Reverse_var.get() else "red",
                            fg="white",
                            command=lambda: Reverse_var.set(not Reverse_var.get()) or toggle_Reverse())
    Reverse_btn.pack(pady=10)

    # Mirror Button (Updated Style: Green ON, Red OFF)
    Mirror_btn = tk.Button(tab3, text="Mirror: ON" if Mirror_var.get() else "Mirror: OFF",
                        font=("Arial", 12, "bold"),
                        bg="green" if Mirror_var.get() else "red",
                        fg="white",
                        command=lambda: Mirror_var.set(not Mirror_var.get()) or toggle_Mirror())
    Mirror_btn.pack(pady=10)

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
        border_size = 5
        bordered_img = Image.new("RGB", (target_size[0] + 2 * border_size, target_size[1] + 2 * border_size), "black")
        bordered_img.paste(resized_img, (border_size, border_size))

        return bordered_img

    except Exception as e:
        return None
    
def show_print_preview():
    """Displays a preview of the ID card layout before printing."""
    try:
        global front_cropped_img, back_cropped_img

        # Ensure an ID type is selected before proceeding
        if not selected_document_type.get().strip():
            messagebox.showerror("Error", "Please select an ID type before previewing.")
            return

        # Ensure images are loaded before previewing
        if 'front_cropped_img' not in globals() or front_cropped_img is None:
            messagebox.showerror("Error", "Please Upload Document select an ID type before previewing.")
            return
        if 'back_cropped_img' not in globals() or back_cropped_img is None:
            messagebox.showerror("Error", "Please Upload Document select an ID type before previewing.")
            return

        # Get the selected paper size
        paper_size = selected_paper_size.get().strip()

        if paper_size == "4x6 Paper":
            canvas_width, canvas_height = 1200, 1800  # 4x6 inches at 300 DPI
            img_width, img_height = 975, 625  # 53x83mm at 300 DPI
            border_thickness = 5

            x_offset = (canvas_width - img_width) // 2  # Centered horizontally
            y_offsets = [(canvas_height - 2 * img_height) // 3, (canvas_height - img_height) - (canvas_height - 2 * img_height) // 3]
        
        elif paper_size == "A4 Paper":
            canvas_width, canvas_height = 2480, 3508  # A4 size at 300 DPI
            img_width, img_height = 975, 625  # 53x83mm at 300 DPI
            front_pos = (200, 80)  # Move front image to absolute top-left
            back_pos = (1340, 80)  # Move back image to absolute top-right

        else:
            messagebox.showerror("Error", "Invalid Paper Size selected.")
            return

        # Create the blank canvas for preview
        preview_img = Image.new("RGB", (canvas_width, canvas_height), "white")
        draw = ImageDraw.Draw(preview_img)

        if paper_size == "4x6 Paper":
            images = [front_cropped_img, back_cropped_img]
            for i, img in enumerate(images):
                resized_img = img.resize((img_width - 2 * border_thickness, img_height - 2 * border_thickness), Image.LANCZOS)
                bordered_img = Image.new("RGB", (img_width, img_height), "black")
                bordered_img.paste(resized_img, (border_thickness, border_thickness))
                preview_img.paste(bordered_img, (x_offset, y_offsets[i]))
                draw.rectangle([x_offset, y_offsets[i], x_offset + img_width, y_offsets[i] + img_height], outline="black", width=border_thickness)
        else:
            border_thickness = 5  # Define border thickness at the start
            images = [front_cropped_img, back_cropped_img]
            positions = [front_pos, back_pos]

            for i, img in enumerate(images):
                resized_img = img.resize((img_width, img_height), Image.LANCZOS)
                bordered_img = Image.new("RGB", (img_width + 2 * border_thickness, img_height + 2 * border_thickness), "black")
                bordered_img.paste(resized_img, (border_thickness, border_thickness))
                preview_img.paste(bordered_img, (positions[i][0] - border_thickness, positions[i][1] - border_thickness))

        # Resize for preview window
        preview_resized = preview_img.resize((400, 600), Image.LANCZOS)
        preview_img_tk = ImageTk.PhotoImage(preview_resized)

        # Show preview in a new window
        preview_win = tk.Toplevel(root)
        preview_win.title("Print Preview")
        label = tk.Label(preview_win, image=preview_img_tk)
        label.photo = preview_img_tk  # Prevent garbage collection
        label.pack()

    except Exception as e:
        messagebox.showerror("Preview Error", f"An unexpected error occurred: {str(e)}")

def print_id_card():
    """Saves the ID card image and opens the Windows Print Dialog."""
    try:
        global front_cropped_img, back_cropped_img

        if not selected_document_type.get().strip():
            messagebox.showerror("Error", "Please Select ID CARD Type before Printing.")
            return

        if front_cropped_img is None or back_cropped_img is None:
            messagebox.showerror("Error", "No cropped images found. Please crop and preview the ID card before printing.")
            return

        # Select canvas size based on paper size
        paper_size = selected_paper_size.get().strip()
        if paper_size == "4x6 Paper":
            canvas_width, canvas_height = 1200, 1800
            img_width, img_height = 975, 625
            border_thickness = 5
            x_offset = (canvas_width - img_width) // 2
            y_offsets = [(canvas_height - 2 * img_height) // 3, 
                         (canvas_height - img_height) - (canvas_height - 2 * img_height) // 3]

        elif paper_size == "A4 Paper":
            canvas_width, canvas_height = 2480, 3508
            img_width, img_height = 975, 625
            border_thickness = 5
            front_pos = (200, 80)
            back_pos = (1340, 80)

        else:
            messagebox.showerror("Error", "Invalid Paper Size selected.")
            return

        # Create the blank canvas
        print_img = Image.new("RGB", (canvas_width, canvas_height), "white")
        draw = ImageDraw.Draw(print_img)

        # Resize & add border
        images = [front_cropped_img, back_cropped_img]
        if paper_size == "4x6 Paper":
            for i, img in enumerate(images):
                resized_img = img.resize((img_width - 2 * border_thickness, img_height - 2 * border_thickness), Image.LANCZOS)
                bordered_img = Image.new("RGB", (img_width, img_height), "black")
                bordered_img.paste(resized_img, (border_thickness, border_thickness))
                print_img.paste(bordered_img, (x_offset, y_offsets[i]))
                draw.rectangle([x_offset, y_offsets[i], x_offset + img_width, y_offsets[i] + img_height], outline="black", width=border_thickness)
        else:
            positions = [front_pos, back_pos]
            for i, img in enumerate(images):
                resized_img = img.resize((img_width, img_height), Image.LANCZOS)
                bordered_img = Image.new("RGB", (img_width + 2 * border_thickness, img_height + 2 * border_thickness), "black")
                bordered_img.paste(resized_img, (border_thickness, border_thickness))
                print_img.paste(bordered_img, (positions[i][0] - border_thickness, positions[i][1] - border_thickness))

        # Save the print file
        save_dir = f"Print Data/{selected_document_type.get()}"
        os.makedirs(save_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = os.path.abspath(f"{save_dir}/print_output_{timestamp}.png")
        print_img.save(save_path, dpi=(300, 300))
        
        messagebox.showinfo("Success", "Click OK to Start Print.\nSelect Printer & Paper Size and print.")

        
        # Open Windows Print Dialog (after preferences are applied)
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
    """Opens a separate window to browse saved images with Previous, Print, Next, and Delete buttons."""
    image_folder = "Print Data"
    
    # Recursively scan all subdirectories and gather image files
    image_files = []
    for root_dir, dirs, files in os.walk(image_folder):
        for file in files:
            if file.endswith((".png", ".jpg", ".jpeg")):
                image_files.append(os.path.join(root_dir, file))  # Store the full path
    
    if not image_files:
        messagebox.showinfo("No Images", "No saved images found.")
        return

    root.iconify()

    viewer_win = tk.Toplevel(root)
    viewer_win.title("Saved Images")
    viewer_win.configure(bg="#DDEEFF")

    win_width, win_height = 450, 730  
    screen_width = viewer_win.winfo_screenwidth()
    screen_height = viewer_win.winfo_screenheight()

    x_pos = (screen_width - win_width) // 2
    y_pos = 10

    viewer_win.geometry(f"{win_width}x{win_height}+{x_pos}+{y_pos}")

    img_label = tk.Label(viewer_win, bg="#FFFFFF")
    img_label.pack(pady=10)

    file_name_label = tk.Label(viewer_win, text="", font=("Arial", 12, "bold"), bg="#DDEEFF", fg="black")
    file_name_label.pack(pady=5)

    index = 0  

    def show_image(idx):
        """Display image at given index along with the file name."""
        if not image_files:
            messagebox.showinfo("No Images", "No more images left.")
            viewer_win.destroy()
            root.deiconify()
            return

        img_path = image_files[idx]
        img = Image.open(img_path)
        img = img.resize((400, 600))  
        img = ImageTk.PhotoImage(img)
        img_label.config(image=img)
        img_label.image = img  # Keep a reference to the image
        file_name_label.config(text=f"File: {os.path.basename(img_path)}")  # Display file name

    warning_shown_next = False
    warning_shown_prev = False

    def next_image(event=None):
        """Show next image or display an error if none left."""
        nonlocal index, warning_shown_next
        if index < len(image_files) - 1:
            index += 1
            show_image(index)
            warning_shown_next = False  # Reset the flag when user moves forward
        elif not warning_shown_next:
            # Show only once
            messagebox.showwarning("No More Images", "This is the last image.")
            warning_shown_next = True  # Set flag so it won't show again

    def prev_image(event=None):
        """Show previous image or display an error if none left."""
        nonlocal index, warning_shown_prev
        if index > 0:
            index -= 1
            show_image(index)
            warning_shown_prev = False  # Reset the flag when user moves back
        elif not warning_shown_prev:
            messagebox.showwarning("No More Images", "This is the first image.")
            warning_shown_prev = True

    def print_current_image():
        """Prints the currently displayed image."""
        img_path = image_files[index]
        os.startfile(img_path, "print")

    def delete_current_image():
        """Deletes the currently displayed image and updates the viewer."""
        nonlocal index
        if not image_files:
            return
        
        img_path = image_files[index]
        if messagebox.askyesno("Delete Image", f"Are you sure you want to delete {os.path.basename(img_path)}?"):
            os.remove(img_path)
            del image_files[index]
            
            # Adjust the index to ensure it doesn't go out of range
            if index >= len(image_files):
                index = max(0, len(image_files) - 1)
            
            # Update the viewer
            if image_files:
                show_image(index)
            else:
                viewer_win.destroy()
                root.deiconify()
                messagebox.showinfo("No Images", "No images left.")

    button_frame = tk.Frame(viewer_win, bg="#DDEEFF")
    button_frame.pack(pady=10, fill="x")

    button_frame.columnconfigure(0, weight=1)
    button_frame.columnconfigure(1, weight=1)
    button_frame.columnconfigure(2, weight=1)
    button_frame.columnconfigure(3, weight=1)

    prev_btn = tk.Button(button_frame, text="⬅ Previous", font=("Arial", 12, "bold"), bg="#007BFF", fg="black", width=10, height=1, command=prev_image)
    prev_btn.grid(row=0, column=0, padx=5, pady=10, sticky="ew")

    print_btn = tk.Button(button_frame, text="🖨 Print", font=("Arial", 12, "bold"), bg="#28A745", fg="black", width=10, height=1, command=print_current_image)
    print_btn.grid(row=0, column=1, padx=5, pady=10, sticky="ew")

    delete_btn = tk.Button(button_frame, text="🗑 Delete", font=("Arial", 12, "bold"), bg="#DC3545", fg="black", width=10, height=1, command=delete_current_image)
    delete_btn.grid(row=0, column=2, padx=5, pady=10, sticky="ew")

    next_btn = tk.Button(button_frame, text="Next ➡", font=("Arial", 12, "bold"), bg="#007BFF", fg="black", width=10, height=1, command=next_image)
    next_btn.grid(row=0, column=3, padx=5, pady=10, sticky="ew")

    def on_close():
        """Restore the main UI when closing the viewer."""
        root.deiconify()  
        viewer_win.destroy()

    viewer_win.protocol("WM_DELETE_WINDOW", on_close)  # Close the window properly

    show_image(index)  # Initially show the first image
    # Key bindings for left and right arrow keys

    # Key bindings for left and right arrow keys to navigate images
    viewer_win.bind("<Left>", prev_image)  # Left arrow key for previous image
    viewer_win.bind("<Right>", next_image)  # Right arrow key for next image
    
def open_edit_image_window(front_img, back_img):
    if front_img is None:
        messagebox.showerror("Error", "No document uploaded! Please upload and Select Card Type.")
        return

    global edited_front_image, edited_back_image, selection_area, rect_id, start_x, start_y, edit_history, current_image, canvas, edit_win

    selection_area = None
    rect_id = None
    start_x, start_y = 0, 0
    edit_history = []
    current_image = "front"

    edit_win = tk.Toplevel(root)
    edit_win.title("Edit Image")

    screen_width = edit_win.winfo_screenwidth()
    screen_height = edit_win.winfo_screenheight()
    window_width, window_height = 700, 650
    x_pos = (screen_width - window_width) // 2
    y_pos = 30
    edit_win.geometry(f"{window_width}x{window_height}+{x_pos}+{y_pos}")
    edit_win.configure(bg="#DDEEFF")
    edit_win.resizable(False, False)

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

        brightness_slider.set(1.0)
        contrast_slider.set(1.0)

        return front_image_data, back_image_data

    def update_and_close():
        front_image_data, back_image_data = save_image()

        front_image = Image.open(front_image_data)
        back_image = Image.open(back_image_data) if back_image_data else None

        update_images_to_boxes(front_image, back_image)

        root.deiconify()
        edit_win.destroy()

    button_frame = tk.Frame(edit_win, bg="#DDEEFF")
    button_frame.pack(pady=5)

    selection_btn = tk.Button(button_frame, text="Select Area", command=lambda: draw_selection("normal"), bg="#4CAF50", fg="white", font=("Arial", 12, "bold"))
    selection_btn.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

    apply_inverted_btn = tk.Button(button_frame, text="Select Inverse", command=lambda: draw_selection("inverted"), bg="#FF5722", fg="white", font=("Arial", 12, "bold"))
    apply_inverted_btn.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

    undo_btn = tk.Button(button_frame, text="Undo", command=undo_last_adjustment, bg="#FF9800", fg="white", font=("Arial", 12, "bold"))
    undo_btn.grid(row=0, column=2, padx=5, pady=5, sticky="ew")

    toggle_btn = tk.Button(button_frame, text="Show Back Image", command=toggle_image, bg="#FFC107", fg="white", font=("Arial", 12, "bold"))
    toggle_btn.grid(row=1, column=0, padx=5, pady=5, sticky="ew")

    save_btn = tk.Button(button_frame, text="Save", command=save_image, bg="#4CAF50", fg="white", font=("Arial", 12, "bold"))
    save_btn.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

    update_btn = tk.Button(button_frame, text="Update & Close", command=update_and_close, bg="#2196F3", fg="white", font=("Arial", 12, "bold"))
    update_btn.grid(row=1, column=2, padx=5, pady=5, sticky="ew")

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

# GUI Setup
root = tk.Tk()
root.title("Multi Print ID Card Tool")
# Centering the main window on the screen
width = 750
height = 700

screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()

root.resizable(False, False)  # Disable resizing of the main window

selected_paper_size = tk.StringVar(value="4x6")  # Default to 4x6 paper
selected_document_type = tk.StringVar(value="ID Card")  # Ensure this is initialized
Reverse_var = tk.BooleanVar(value=Reverse_state) 
Mirror_var = tk.BooleanVar(value=mirror_state)

# Calculate the position to center the window
x_position = (screen_width // 2) - (width // 2)
y_position = 10

root.geometry(f"{width}x{height}+{x_position}+{y_position}")

root.configure(bg="#DDEEFF")

file_path = None  # Global variable to store uploaded file path

# Create a frame for the buttons on the left
frame = Frame(root, bd=2, relief=tk.RIDGE, bg="#FFFFFF")
frame.grid(row=1, column=0, padx=20, pady=5, sticky="nsw")  # Ensures it stays on the left

# Upload Document Button
upload_btn = tk.Button(frame, text="🖼 Upload Document", command=upload_doc, font=("Arial", 12, "bold"), bg="#007BFF", fg="white")
upload_btn.grid(row=0, column=0, pady=10, padx=10, sticky="ew")

button_frame = Frame(frame, bg="#FFFFFF")  # Removed height to allow auto-fit
button_frame.grid(row=1, column=0, pady=5, padx=5, sticky="w")  # Align left
refresh_buttons()  # Load buttons dynamically

# Edit Image Button
edit_image_btn = tk.Button(frame, text="🛠 Edit Image", font=("Arial", 12, "bold"), bg="#1b4ce3", fg="white", command=lambda: open_edit_image_window(current_front_image,current_back_image))
edit_image_btn.grid(row=6, column=0, pady=10, padx=10, sticky="ew")

# Label to show the file status
label = tk.Label(frame, text="No file uploaded", bg="#FFFFFF", font=("Arial", 10, "bold"))
label.grid(row=8, column=0, pady=5)

# Paper Size Selection
tk.Label(frame, text="Select Paper Size:", font=("Arial", 12, "bold"), bg="#FFFFFF").grid(row=10, column=0, pady=5, padx=10, sticky="w")
paper_dropdown = ttk.Combobox(frame, textvariable=selected_paper_size, state="readonly", width=25, font=("Arial", 10, "bold"))
paper_dropdown["values"] = ["4x6 Paper", "A4 Paper"]
paper_dropdown.current(0)
paper_dropdown.grid(row=9, column=0, pady=5, padx=10, sticky="ew")

# Main Layout (2 columns: Left for Buttons, Right for Images)
root.grid_columnconfigure(0, weight=0)  # Left Panel
root.grid_columnconfigure(1, weight=1)  # Right Panel (Image Frame should NOT expand infinitely)

# Frame for displaying front and back images (Right Side)
image_frame = Frame(root, width=400, height=630, bd=2, relief=tk.RIDGE, bg="#FFFFFF")
image_frame.grid(row=1, column=1, padx=0, pady=5, sticky="nw")
image_frame.grid_propagate(False)  # Prevent the frame from resizing based on content

# Label for the front image
front_label_text = tk.Label(image_frame, text="Front Image", bg="#D9F9D8", relief="solid",
                            width=35, height=2, font=("Arial", 12, "bold"))
front_label_text.grid(row=0, column=0, padx=10, pady=(10, 2))

# Image box for front image
front_image_box = tk.Label(image_frame, bg="#FFFFFF", relief="solid")
front_image_box.grid(row=1, column=0, padx=20, pady=(15, 10))

# Label for the back image
back_label_text = tk.Label(image_frame, text="Back Image", bg="#F9D8D8", relief="solid",
                           width=35, height=2, font=("Arial", 12, "bold"))
back_label_text.grid(row=2, column=0, padx=10, pady=(10, 2))

# Image box for back image
back_image_box = tk.Label(image_frame, bg="#FFFFFF", relief="solid")
back_image_box.grid(row=3, column=0, padx=10, pady=(15, 10))

initialize_image_boxes()

top_right_frame = tk.Frame(root, bg="#DDEEFF")
top_right_frame.grid(row=0, column=1, columnspan=2, sticky="ne", padx=10, pady=5)

# Settings Button
settings_btn = tk.Button(top_right_frame, text="⚙ Settings", font=("Arial", 10, "bold"), bg="#007BFF", fg="white", command=open_settings)
settings_btn.grid(row=0, column=1, sticky="ne", padx=10, pady=5)

#Restart Button
restart_btn = tk.Button(top_right_frame, text="🔄 Restart", font=("Arial", 10, "bold"), bg="#DC3545", fg="white", command=restart_ui)
restart_btn.grid(row=0, column=2, sticky="ne", padx=10, pady=5)

# Frame to hold the buttons
button_frame2 = tk.Frame(frame)
button_frame2.grid(row=10, column=0, columnspan=2, pady=10, padx=5, sticky="ew")

# Ensure frame has a fixed height
button_frame2.configure(height=40)
button_frame2.grid_propagate(False)

# Configure columns for equal space distribution
button_frame2.grid_columnconfigure(0, weight=1)
button_frame2.grid_columnconfigure(1, weight=1)

# Print Preview Button
preview_button = tk.Button(button_frame2, text="🔍Print Preview", font=("Arial", 12, "bold"), bg="#6F42C1", fg="white", command=show_print_preview)
preview_button.grid(row=0, column=0, pady=0, padx=5, sticky="ew")

# Start Print Button
print_btn = tk.Button(button_frame2, text="🖨 Print", font=("Arial", 12, "bold"), bg="#6F42C1", fg="white", command=print_id_card)
print_btn.grid(row=0, column=1, pady=0, padx=5, sticky="ew")

# View Saved Images Button
view_images_btn = tk.Button(frame, text="🖼 View Saved Images", font=("Arial", 12, "bold"), bg="#28A745", fg="white", command=open_image_viewer)
view_images_btn.grid(row=11, column=0, pady=10, padx=10, sticky="ew")

# Button to check for updates
update_btn = tk.Button(frame, text="🔄 Check for Updates", font=("Arial", 12, "bold"), bg="#007BFF", fg="white", command=check_for_updates)
update_btn.grid(row=12, column=0, pady=10, padx=10, sticky="ew")

# Label to show current version
current_version = tk.StringVar()
current_version.set(f"current Version: {get_current_version()}")
version_label = tk.Label(frame, textvariable=current_version, font=("Arial", 10, "bold"))
version_label.grid(row=13, column=0, columnspan=2, pady=5)

root.mainloop()

# PDF IMAGE ZOOM update images PASSWORD crop multi cordinates + overwrite + load & crop same WORKING TILL HERE ...!!
# setting menu in centre, 3 tabs delete crop data, Buttons Rename ,Image Setting (Reverse,mirror) + fixed preview window close issue ...!
# Print Window Default Print & Preview A4,4x6 ,auto Card name in print output folder.
# Restart & in crop Front and Back Popup added  
# crop button hide after 1st crop.
# image Viewer with Print Option , fixed image resize to boxes. 
# image editer also added. Image Quality Improved,select inverse fixed.
# Github Auto update feature added

