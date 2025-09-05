# Traffic Shaper

A graphical utility for Linux to manage network bandwidth. This tool provides an easy-to-use interface for applying traffic shaping rules on your system.

## Features

-   **Device-wide Shaping:** Apply upload and download speed limits to an entire network device.
-   **Per-Process Shaping:** Isolate a specific application (e.g., a web browser, a game) and limit its upload and download speed without affecting other applications.

## Requirements

### System Dependencies

This tool relies on a few standard Linux utilities. You must have them installed for the application to work.

-   `tc` (usually part of the `iproute2` package)
-   `iptables`

These are standard on most Linux distributions.

### Python Dependencies

The Python dependencies are listed in `requirements.txt`.

-   `psutil`

## Installation

1.  **Clone the repository (if you haven't already):**
    ```bash
    git clone <repository_url>
    cd shaper
    ```

2.  **Install the required Python packages:**
    ```bash
    pip install -r requirements.txt
    ```

## Usage

You must run the application with `sudo` because modifying network traffic rules requires root privileges.

```bash
sudo python3 shaper.py
```

### How to Limit a Specific Process

This is the primary feature of the application. To limit the speed of a single process (e.g., Chrome):

1.  **Apply a Device Limit First:** Before you can limit a process, you must set a baseline limit on the entire device.
    *   Go to the **Device Shaping** tab.
    *   Select your primary **Network Device** (e.g., `eth0`, `wlan0`).
    *   Click **Apply Device Limit**. This creates the main queues that are required for per-process rules.

2.  **Apply the Process Limit:**
    *   Go to the **Process Shaping** tab.
    *   Find the process you want to limit in the list. You can click **Refresh List** to update it.
    *   Click on the process to select it.
    *   Enter the desired **Upload (Mbps)** and **Download (Mbps)** limits for that process.
    *   Click **Apply Process Limit**.

The shaping rule is now active for that process.

### How to Stop Shaping

-   **To stop a process-specific limit:** Select the process in the list and click **Stop Process Limit**.
-   **To stop all shaping:** Go to the **Device Shaping** tab and click **Stop Device Limit**. This will remove all device-wide and per-process rules.