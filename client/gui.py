import os
import sys
import time
from pystray import Icon, MenuItem, Menu
from PIL import Image
from tkinter import Tk, Button, Label, StringVar


def create_tray_icon(self, root):
    def on_quit():
        self.cleanup()
        sys.exit(0)

    def open_gui():
        root.deiconify()

    # Create tray icon
    install_dir = os.path.dirname(os.path.realpath(__file__))
    icon_path = os.path.join(install_dir, 'assets', 'rfastream.ico')
    icon_image = Image.open(icon_path)

    menu = Menu(MenuItem('Open', open_gui), MenuItem('Quit', on_quit))

    tray_icon = Icon("RFAStream Client", icon_image, "RFAStream", menu)

    return tray_icon


def create_gui(self):
    root = Tk()
    root.title("RFAStream Client")
    root.resizable(False, False)

    root.iconbitmap("..\\assets\\rfastream.ico")

    # Calculate the position for the bottom-right corner
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    window_width = 300
    window_height = 215
    position_x = screen_width - window_width - 10  # 10px margin from the edge
    position_y = screen_height - window_height - 100  # 100px margin from the taskbar

    # Set the position
    root.geometry(f"{window_width}x{window_height}+{position_x}+{position_y}")

    self.connection_status = StringVar()
    self.connection_status.set("Disconnected")

    self.broadcast_status = StringVar()
    self.broadcast_status.set("Finding Broadcast Status...")

    title_label = Label(root, text="RFAStream Client", font=("Arial", 16))
    title_label.pack(pady=(5, 0))

    status_label = Label(root, textvariable=self.connection_status, font=("Arial", 12), fg="green")
    status_label.pack(pady=(0, 10))

    broadcast_status_label = Label(root, textvariable=self.broadcast_status, font=("Arial", 10), fg="black")
    broadcast_status_label.pack(pady=(0, 15))

    self.pause_button = Button(root, text="Pause Notifications", command=self.toggle_broadcast_pause)
    self.pause_button.pack(pady=5)

    mute_button_text = "Unmute Client" if self.is_muted else "Mute Client"
    self.mute_button = Button(root, text=mute_button_text, command=self.toggle_client_mute)
    self.mute_button.pack(pady=5)

    exit_button = Button(root, text="Hide", command=root.withdraw)
    exit_button.pack(pady=5)

    root.withdraw()
    return root





def update_pause_button(self, text):
    self.pause_button.config(text=text)
