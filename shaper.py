import tkinter as tk
from tkinter import ttk, messagebox
import os
import subprocess
import random
import shutil

class TrafficShaperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Traffic Shaper")

        # --- Get Script Directory ---
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.shaper_script_path = os.path.join(self.script_dir, "traffic_shaper.sh")

        # --- Font Configuration ---
        self.font = ("DejaVu Sans Mono", 10)

        # --- Style Configuration ---
        style = ttk.Style()
        style.configure(".", font=self.font, background="#00008B", foreground="white")
        style.configure("TLabel", background="#00008B", foreground="white")
        style.configure("TButton", background="#00008B", foreground="white")
        style.configure("TEntry", fieldbackground="black", foreground="#00FF00", insertbackground="#00FF00")
        style.configure("TMenubutton", background="#00008B", foreground="white")
        style.configure("TCheckbutton", background="#00008B", foreground="white")
        style.map("TCheckbutton", background=[("active", "black")])
        style.configure("Active.TFrame", background="green")
        style.configure("Terminal.TFrame", background="#00008B")
        style.configure("Terminal.Title.TLabel", background="#00008B", foreground="white")
        style.configure("Terminal.TLabel", background="#00008B", foreground="#00FF00") # Green Text
        self.root.configure(background="#00008B")
        self.debounce_job = None

        # --- Model Variables ---
        self.device_var = tk.StringVar()
        self.upload_var = tk.StringVar(value="10") # Default in MB/s
        self.download_var = tk.StringVar(value="10") # Default in MB/s
        self.shaping_on = tk.BooleanVar()
        self.filter_type_var = tk.StringVar(value="Device")
        self.port_var = tk.StringVar()
        self.protocol_var = tk.StringVar(value="TCP")


        # --- Connect model to controller ---
        self.upload_var.trace_add("write", self.schedule_update)
        self.download_var.trace_add("write", self.schedule_update)

        self.create_widgets()
        self.populate_devices()
        self.update_speed_display(None, None) # Initial call to set labels to N/A
        self.toggle_port_fields() # Set initial state for port fields

    def toggle_port_fields(self):
        if self.filter_type_var.get() == "Port":
            self.port_frame.grid(row=5, column=0, columnspan=2, pady=5, sticky=tk.W)
            self.port_label.pack(side=tk.LEFT, padx=(0, 5))
            self.port_entry.pack(side=tk.LEFT, padx=(0, 10))
            self.protocol_label.pack(side=tk.LEFT, padx=(0, 5))
            self.protocol_menu.pack(side=tk.LEFT)
        else:
            self.port_frame.grid_remove()

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10", style="Terminal.TFrame")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        logo_label = ttk.Label(main_frame, text="", font=("monospace", 10))
        logo_label.grid(row=0, column=0, columnspan=2, pady=10)
        self.generate_logo(logo_label)

        # --- Input Widgets ---
        ttk.Label(main_frame, text="Device:", style="Terminal.TLabel").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.device_menu = ttk.OptionMenu(main_frame, self.device_var, "Select a device")
        self.device_menu.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=2)
        self.device_menu.config(style="TMenubutton")

        ttk.Label(main_frame, text="Upload Speed (MB/s):", style="Terminal.TLabel").grid(row=2, column=0, sticky=tk.W, pady=2)
        ttk.Entry(main_frame, textvariable=self.upload_var, style="TEntry").grid(row=2, column=1, sticky=(tk.W, tk.E), pady=2)

        ttk.Label(main_frame, text="Download Speed (MB/s):", style="Terminal.TLabel").grid(row=3, column=0, sticky=tk.W, pady=2)
        ttk.Entry(main_frame, textvariable=self.download_var, style="TEntry").grid(row=3, column=1, sticky=(tk.W, tk.E), pady=2)

        # --- Filter Selection ---
        filter_frame = ttk.Frame(main_frame, style="Terminal.TFrame")
        filter_frame.grid(row=4, column=0, columnspan=2, pady=5, sticky=tk.W)
        ttk.Label(filter_frame, text="Filter by:", style="Terminal.TLabel").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Radiobutton(filter_frame, text="Entire Device", variable=self.filter_type_var, value="Device", command=self.toggle_port_fields, style="TCheckbutton").pack(side=tk.LEFT)
        ttk.Radiobutton(filter_frame, text="Specific Port", variable=self.filter_type_var, value="Port", command=self.toggle_port_fields, style="TCheckbutton").pack(side=tk.LEFT)

        # --- Port/Protocol Frame (Initially Hidden) ---
        self.port_frame = ttk.Frame(main_frame, style="Terminal.TFrame")
        # self.port_frame.grid(row=5, column=0, columnspan=2, pady=5, sticky=tk.W) # Managed by toggle_port_fields

        self.port_label = ttk.Label(self.port_frame, text="Port:", style="Terminal.TLabel")
        self.port_entry = ttk.Entry(self.port_frame, textvariable=self.port_var, style="TEntry", width=8)
        self.protocol_label = ttk.Label(self.port_frame, text="Protocol:", style="Terminal.TLabel")
        self.protocol_menu = ttk.OptionMenu(self.port_frame, self.protocol_var, "TCP", "TCP", "UDP")
        self.protocol_menu.config(style="TMenubutton")


        self.toggle_frame = ttk.Frame(main_frame, padding=2)
        self.toggle_frame.grid(row=6, column=0, columnspan=2, pady=10)
        self.toggle_button = ttk.Checkbutton(self.toggle_frame, text="Enable Shaping", variable=self.shaping_on, command=self.toggle_shaping, style="TCheckbutton")
        self.toggle_button.pack()

        self.status_label = ttk.Label(main_frame, text="Shaping is inactive.", style="Terminal.TLabel")
        self.status_label.grid(row=7, column=0, columnspan=2)

        # --- Speed Display Widgets ---
        display_container = ttk.Frame(main_frame, style="Terminal.TFrame", padding=10)
        display_container.grid(row=8, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        display_container.grid_propagate(False)
        display_container.config(width=400, height=100)

        title_label = ttk.Label(display_container, text="Current Speed Limit", style="Terminal.Title.TLabel")
        title_label.pack()

        upload_frame = ttk.Frame(display_container, style="Terminal.TFrame")
        upload_frame.pack()
        ttk.Label(upload_frame, text="Upload:", style="Terminal.TLabel").pack(side=tk.LEFT)
        self.upload_display_label = ttk.Label(upload_frame, text="N/A", style="Terminal.TLabel")
        self.upload_display_label.pack(side=tk.LEFT)

        download_frame = ttk.Frame(display_container, style="Terminal.TFrame")
        download_frame.pack()
        ttk.Label(download_frame, text="Download:", style="Terminal.TLabel").pack(side=tk.LEFT)
        self.download_display_label = ttk.Label(download_frame, text="N/A", style="Terminal.TLabel")
        self.download_display_label.pack(side=tk.LEFT)

    def generate_logo(self, label):
        def run_in_thread():
            print("Generating logo...")
            try:
                npx_path = shutil.which("npx")
                if not npx_path:
                    print("npx not found in PATH")
                    self.root.after(0, lambda: label.config(text="Shaper"))
                    return

                color1 = f"#{random.randint(0, 0xFFFFFF):06x}"
                color2 = f"#{random.randint(0, 0xFFFFFF):06x}"
                process = subprocess.Popen(
                    [npx_path, "gradient-figlet", "--from", color1, "--to", color2, "Shaper"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
                stdout, stderr = process.communicate()
                print("stdout:", stdout)
                print("stderr:", stderr)
                if process.returncode == 0:
                    self.root.after(0, lambda: label.config(text=stdout))
                else:
                    self.root.after(0, lambda: label.config(text="Shaper"))
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                self.root.after(0, lambda: label.config(text="Shaper"))

        import threading
        thread = threading.Thread(target=run_in_thread)
        thread.daemon = True
        thread.start()

    def populate_devices(self):
        try:
            devices = os.listdir('/sys/class/net')
            self.device_menu['menu'].delete(0, 'end')
            for device in devices:
                self.device_menu['menu'].add_command(label=device, command=tk._setit(self.device_var, device))
            if devices:
                self.device_var.set(devices[0])
        except FileNotFoundError:
            messagebox.showerror("Error", "Could not find network devices.")

    def format_speed(self, speed_kbps):
        if speed_kbps is None:
            return "N/A"
        try:
            kbps_float = float(speed_kbps)
            k_bytes_s = kbps_float / 8
            mbps = kbps_float / 1000
            m_bytes_s = k_bytes_s / 1000
            return f"{kbps_float:,.2f} kbps | {k_bytes_s:,.2f} KB/s | {mbps:,.2f} mbps | {m_bytes_s:,.2f} MB/s"
        except (ValueError, TypeError):
            return "Invalid Input"

    def update_speed_display(self, upload_kbps, download_kbps):
        self.upload_display_label.config(text=self.format_speed(upload_kbps))
        self.download_display_label.config(text=self.format_speed(download_kbps))

    def schedule_update(self, *args):
        if self.debounce_job:
            self.root.after_cancel(self.debounce_job)
        self.debounce_job = self.root.after(500, self.real_time_update)

    def real_time_update(self):
        if self.shaping_on.get():
            self.apply_shaping("start")

    def toggle_shaping(self):
        if self.shaping_on.get():
            self.apply_shaping("start")
            self.toggle_frame.config(style="Active.TFrame")
        else:
            self.apply_shaping("stop")
            self.toggle_frame.config(style="TFrame")

    def apply_shaping(self, action):
        device = self.device_var.get()
        if not device or device == "Select a device":
            messagebox.showerror("Error", "Please select a device.")
            self.shaping_on.set(False)
            return

        # --- Use 'pkexec' for graphical sudo prompt, falling back to 'sudo' ---
        sudo_cmd = shutil.which("pkexec") or shutil.which("gksudo") or "sudo"

        base_command = [sudo_cmd, self.shaper_script_path]

        if action == "stop":
            try:
                subprocess.run(base_command + ["stop", device], check=True)
                self.status_label.config(text="Shaping is inactive.")
                self.update_speed_display(None, None)
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                messagebox.showerror("Error", f"Failed to stop shaping: {e}")
            return

        try:
            upload_mbs = float(self.upload_var.get())
            download_mbs = float(self.download_var.get())

            upload_kbps = upload_mbs * 8000
            download_kbps = download_mbs * 8000

            command = base_command + ["start", device, str(upload_kbps), str(download_kbps)]

            # --- Add port and protocol if specified ---
            if self.filter_type_var.get() == "Port":
                port = self.port_var.get()
                protocol = self.protocol_var.get()
                if not port.isdigit() or not 1 <= int(port) <= 65535:
                    messagebox.showerror("Error", "Invalid Port. Please enter a number between 1 and 65535.")
                    self.shaping_on.set(False)
                    return
                command.extend([port, protocol])
                status_msg = f"Shaping active on {device} for {protocol} port {port}."
            else:
                status_msg = f"Shaping active on {device}."


            subprocess.run(
                command,
                capture_output=True, text=True, check=True
            )
            self.status_label.config(text=status_msg)
            self.update_speed_display(upload_kbps, download_kbps)

        except ValueError:
            messagebox.showerror("Error", "Invalid speed value. Please enter a number.")
            self.shaping_on.set(False)
            self.update_speed_display(None, None)
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            error_message = e.stderr if isinstance(e, subprocess.CalledProcessError) else str(e)
            messagebox.showerror("Error", f"Failed to apply shaping rules:\n\n{error_message}")
            self.shaping_on.set(False)
            self.update_speed_display(None, None)

if __name__ == "__main__":
    root = tk.Tk()
    app = TrafficShaperApp(root)
    root.mainloop()
