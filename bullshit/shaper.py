import tkinter as tk
from tkinter import ttk, messagebox
import os
import subprocess
import psutil
import shutil

class TrafficShaperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Traffic Shaper")
        self.root.geometry("600x600")

        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TNotebook", background="#f0f0f0", borderwidth=0)
        style.configure("TNotebook.Tab", background="#d0d0d0", padding=[10, 5])
        style.map("TNotebook.Tab", background=[("selected", "#f0f0f0")])
        style.configure("TFrame", background="#f0f0f0")
        style.configure("TLabel", background="#f0f0f0")
        style.configure("TButton", padding=6)
        style.configure("TEntry", padding=5)
        style.configure("Treeview.Heading", font=(None, 10, 'bold'))

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(expand=True, fill="both", padx=10, pady=10)

        self.device_tab = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(self.device_tab, text="Device Shaping")
        self.create_device_shaping_tab()

        self.process_tab = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(self.process_tab, text="Process Shaping")
        self.create_process_shaping_tab()

        self.status_var = tk.StringVar(value="Ready")
        self.status_bar = ttk.Label(root, textvariable=self.status_var, anchor=tk.W, padding=5)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.active_process_rules = {}

        self.populate_devices()
        self.populate_processes()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_device_shaping_tab(self):
        self.device_var = tk.StringVar()
        self.vpn_interface_var = tk.StringVar(value="nordlynx")
        self.device_upload_var = tk.StringVar(value="10")
        self.device_download_var = tk.StringVar(value="10")

        device_frame = ttk.LabelFrame(self.device_tab, text="Target Devices", padding=10)
        device_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(device_frame, text="Physical Device:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.device_menu = ttk.OptionMenu(device_frame, self.device_var, "Select a device")
        self.device_menu.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=2)

        ttk.Label(device_frame, text="VPN Device:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Entry(device_frame, textvariable=self.vpn_interface_var).grid(row=1, column=1, sticky=tk.EW, padx=5, pady=2)
        device_frame.grid_columnconfigure(1, weight=1)

        limits_frame = ttk.LabelFrame(self.device_tab, text="Bandwidth Limits", padding=10)
        limits_frame.pack(fill=tk.X, pady=5)
        ttk.Label(limits_frame, text="Upload (Mbps):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(limits_frame, textvariable=self.device_upload_var, width=10).grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(limits_frame, text="Download (Mbps):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(limits_frame, textvariable=self.device_download_var, width=10).grid(row=1, column=1, padx=5, pady=5)

        button_frame = ttk.Frame(self.device_tab)
        button_frame.pack(fill=tk.X, pady=20)
        ttk.Button(button_frame, text="Apply Device Limit", command=self.apply_device_shaping).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Stop Device Limit", command=self.stop_device_shaping).pack(side=tk.LEFT, padx=5)

    def create_process_shaping_tab(self):
        # ... (omitted for brevity, no changes from previous version)
        pass

    def _run_command(self, command, description):
        # ... (omitted for brevity, no changes from previous version)
        pass

    def apply_device_shaping(self):
        physical_device = self.device_var.get()
        vpn_device = self.vpn_interface_var.get()
        if not physical_device or physical_device == "Select a device" or not vpn_device:
            messagebox.showerror("Error", "Please select a physical device and specify a VPN device.")
            return
        try:
            upload_kbit = int(float(self.device_upload_var.get()) * 1000)
            download_kbit = int(float(self.device_download_var.get()) * 1000)
        except ValueError:
            messagebox.showerror("Error", "Invalid speed value.")
            return

        self.stop_device_shaping(show_status=False)
        ifb_device = "ifb0"

        # --- Download Shaping (on Physical Device) ---
        self._run_command(["modprobe", "ifb", "numifbs=1"], "Loaded ifb module.")
        self._run_command(["ip", "link", "set", "dev", ifb_device, "up"], f"Interface {ifb_device} is up.")
        self._run_command(["tc", "qdisc", "add", "dev", physical_device, "handle", "ffff:", "ingress"], "Added ingress qdisc to physical device.")
        # This is a simplification. A real implementation would need to find the VPN port.
        # For now, we assume all traffic on the physical interface is VPN traffic when the VPN is active.
        self._run_command(["tc", "filter", "add", "dev", physical_device, "parent", "ffff:", "protocol", "all", "u32", "match", "u32", "0", "0", "action", "mirred", "egress", "redirect", "dev", ifb_device], "Redirecting ingress to ifb.")
        self._run_command(["tc", "qdisc", "add", "dev", ifb_device, "root", "handle", "1:", "htb", "default", "10"], "Added HTB qdisc to ifb.")
        self._run_command(["tc", "class", "add", "dev", ifb_device, "parent", "1:", "classid", "1:1", "htb", "rate", f"{download_kbit}kbit"], f"Set download limit.")

        # --- Upload Shaping (on VPN Device) ---
        self._run_command(["tc", "qdisc", "add", "dev", vpn_device, "root", "handle", "2:", "htb", "default", "10"], "Added HTB qdisc to VPN device.")
        self._run_command(["tc", "class", "add", "dev", vpn_device, "parent", "2:", "classid", "2:1", "htb", "rate", f"{upload_kbit}kbit"], f"Set upload limit.")

        self.status_var.set(f"Shaping active on {physical_device} and {vpn_device}.")
        messagebox.showinfo("Success", f"Limits applied.\nUpload on {vpn_device}: {upload_kbit} kbit/s\nDownload on {physical_device}: {download_kbit} kbit/s")

    def stop_device_shaping(self, show_status=True):
        physical_device = self.device_var.get()
        vpn_device = self.vpn_interface_var.get()
        ifb_device = "ifb0"
        
        # Clean up physical device
        self._run_command(["tc", "qdisc", "del", "dev", physical_device, "ingress"], "Cleared ingress qdisc.")
        # Clean up VPN device
        self._run_command(["tc", "qdisc", "del", "dev", vpn_device, "root"], "Cleared VPN root qdisc.")
        # Clean up IFB device
        self._run_command(["tc", "qdisc", "del", "dev", ifb_device, "root"], "Cleared ifb qdisc.")

        if show_status:
            self.status_var.set("Device shaping stopped.")

    # ... (rest of the methods are omitted for brevity, they are the same as the last full version) ...
    def apply_process_shaping(self):
        # This will be re-enabled in the next step
        messagebox.showinfo("Info", "Apply device-wide limits first. Process shaping will be enabled soon.")

    def stop_process_shaping(self, pid=None, show_status=True):
        pass # To be re-enabled

    def populate_devices(self):
        try:
            # We list all devices, user should pick the physical one.
            devices = [dev for dev in os.listdir('/sys/class/net')]
            self.device_menu['menu'].delete(0, 'end')
            for device in devices:
                self.device_menu['menu'].add_command(label=device, command=tk._setit(self.device_var, device))
            # Try to guess the physical device
            for dev in devices:
                if dev.startswith('e') or dev.startswith('w'): # enp, eth, wlan, etc.
                    self.device_var.set(dev)
                    break
        except FileNotFoundError:
            messagebox.showerror("Error", "Could not find network devices.")

    def on_closing(self):
        if messagebox.askokcancel("Quit", "Do you want to remove all shaping rules before quitting?"):
            self.stop_device_shaping(show_status=False)
            self.root.destroy()

# The rest of the class and the main execution block are here...
# I have omitted them to keep the response focused on the changes.
