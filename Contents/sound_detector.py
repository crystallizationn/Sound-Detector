import os
import sys
import threading
import time
import numpy as np
import sounddevice as sd
import requests
import json
import tkinter as tk
from tkinter import *
from tkinter import messagebox, ttk
from typing import Any
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv

# Sound Detector Script
# v2.1.0
    
version = "v2.1.0"
volume_bar: ttk.Progressbar | None = None


def show_fatal_error(title: str, message: str) -> None:
    """
    Display an error popup even if the main Tkinter window isn't open yet.
    """
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror(title=title, message=message)
    root.destroy()
    sys.exit(1)
    

def submit(
    noiseThreshold: Entry,
    noiseFloor: Entry,
    sampleRate: Entry,
    pingCooldown: Entry,
    volumeReportCooldown: Entry,
    alertUser: tk.BooleanVar,
    userID: Entry,
    firstWebhookUrl: Entry,
    secondWebhookUrl: Entry,
) -> None:
    """
    Get the submitted values for the settings configuration from the user.

    Args:
        noiseThreshold (Entry): The value that determines whether to mention the user ID on Discord.
        noiseFloor (Entry): Minimum sound floor that will be passed through the live volume bar.
        sampleRate (Entry): Value of the hertz rate to help with sound accuracy.
        pingCooldown (Entry): Cooldown (seconds) for when the user can be pinged in Discord.
        volumeReportCooldown (Entry): Cooldown (seconds) for when the volume report can be sent in Discord.
        alertUser (tk.BooleanVar): Boolean switch that determines whether to ping the user on exceeded thresholds or not.
        userID (Entry): The Discord user's ID for the webhook URL(s) to mention.
        firstWebhookUrl (Entry): The first Discord webhook URL for notifications.
        secondWebhookUrl (Entry): The second Discord webhook URL for volume reports.
    """
    global noise_threshold, noise_floor, hertz_rate, ping_cooldown, volume_report_cooldown, ping_user_on_alert, volume_bar, USER_ID, FIRST_DISCORD_WEBHOOK_URL, SECOND_DISCORD_WEBHOOK_URL

    try:
        noise_threshold = float(noiseThreshold.get())
        noise_floor = float(noiseFloor.get())
        hertz_rate = int(sampleRate.get())
        ping_cooldown = float(pingCooldown.get())
        volume_report_cooldown = float(volumeReportCooldown.get())
        ping_user_on_alert = bool(alertUser.get())
        USER_ID = int(userID.get().strip())
        FIRST_DISCORD_WEBHOOK_URL = str(firstWebhookUrl.get().strip())
        SECOND_DISCORD_WEBHOOK_URL = str(secondWebhookUrl.get().strip())

        if any(x < 0 for x in (noise_floor, ping_cooldown, volume_report_cooldown)):
            messagebox.showerror("Invalid Settings", "Noise Floor, Ping Cooldown and Volume Report Cooldown "
                                 "cannot be under 0 and must be at absolute value.")
            return
        elif noise_threshold <= 0:
            messagebox.showerror("Invalid Settings", "Noise Threshold cannot be under 0.")
            return
        elif hertz_rate < 24100:
            messagebox.showerror("Invalid Settings", "Hertz Rate cannot be under 24100.")
            return
        elif not isinstance(USER_ID, int) or USER_ID < 0:
            messagebox.showerror("Invalid Settings", "User ID must be positive numbers only.")
            return
        elif not FIRST_DISCORD_WEBHOOK_URL.startswith("https://discord") and not SECOND_DISCORD_WEBHOOK_URL.startswith("https://discord"):
            messagebox.showerror("Invalid Settings", "Webhook(s) must start with https://discord")
            return
        
    except Exception as e:
        messagebox.showerror("Invalid Settings", f"Invalid input entered: {e}")
        return

    config["noise_threshold"] = noise_threshold
    config["noise_floor"] = noise_floor
    config["sample_rate_hz"] = hertz_rate
    config["ping_cooldown"] = ping_cooldown
    config["volume_report_cooldown"] = volume_report_cooldown
    config["ping_user_on_alert"] = ping_user_on_alert
    config["user_id"] = USER_ID
    config["first_webhook_url"] = FIRST_DISCORD_WEBHOOK_URL
    config["second_webhook_url"] = SECOND_DISCORD_WEBHOOK_URL
    save_config(config)
    save_env(FIRST_DISCORD_WEBHOOK_URL, SECOND_DISCORD_WEBHOOK_URL, USER_ID)

    # Clear the settings form instead of destroying the window
    for widget in window.winfo_children():
        widget.destroy()

    # Resize to a compact status window
    window.geometry("420x325")
    Label(window, font=("Arial", 20, "bold"), text="Listening for Audio...").pack(pady=(25, 8))
    Label(window, font=("Arial", 14), text=f"Threshold: {noise_threshold} | Floor: {noise_floor}").pack(pady=(0, 10))
    
    volume_bar = ttk.Progressbar(window, orient="horizontal", length=300, mode="determinate", maximum=100)
    volume_bar.pack(pady=(0, 15))

    Button(window, font=("Arial", 15), text="Test Webhook", width=18, command=test_webhooks).pack(pady=5)
    Button(window, font=("Arial", 15), text="Delete Messages", width=18, command=delete_all_messages).pack(pady=5)
    Button(window, font=("Arial", 15), text="Stop & Quit", width=18, command=on_close).pack(pady=5)

    threading.Thread(target=audio_listener, daemon=True).start()


def test_webhooks() -> None:
    """
    Send a test message to all configured Discord webhooks.
    """
    def _worker() -> None:
        results = []
        delete_time = int(time.time()) + volume_auto_delete_duration

        targets = [
            ("Alert Webhook", FIRST_DISCORD_WEBHOOK_URL),
            ("Volume Webhook", SECOND_DISCORD_WEBHOOK_URL),
        ]

        for label, url in targets:
            if not url:
                continue

            embed = {
                "title": f"{label} Test",
                "description": f"Connection test from Sound Detector {version}",
                "color": 0xFF0000,
                "fields": [
                    {
                        "name": "Status",
                        "value": f"Deletes <t:{delete_time}:R>",
                        "inline": True,
                    }
                ],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            data = {
                "content": f"**Webhook Test - <@{USER_ID}>**" if ping_user_on_alert else "**Webhook Test**",
                "embeds": [embed],
                "allowed_mentions": {"parse": ["users"]},
            }

            try:
                res = requests.post(f"{url}?wait=true", json=data, timeout=(2, 5))
                if res.status_code in (200, 201):
                    msg_id = res.json().get("id")
                    threading.Thread(
                        target=auto_delete_msg,
                        args=(url, msg_id, volume_auto_delete_duration),
                        daemon=True,
                    ).start()
                    results.append(f"* {label}: Success")
                else:
                    results.append(f"* {label}: Failed (HTTP {res.status_code})")
            except requests.RequestException as e:
                results.append(f"* {label}: Error ({e})")

        summary = "\n".join(results) if results else "No webhook URLs configured."
        window.after(0, lambda: messagebox.showinfo("Test Webhook Results", summary))

    threading.Thread(target=_worker, daemon=True).start()
        

def delete_all_messages() -> None:
    """
    Immediately delete all tracked active Discord webhook messages.
    """
    def _worker() -> None:
        with messages_lock:
            to_delete = list(active_messages)
            active_messages.clear()

        if not to_delete:
            window.after(0, lambda: messagebox.showinfo("Delete Messages", "No active messages to delete."))
            return

        deleted_count = 0
        for webhook_url, msg_id in to_delete:
            try:
                res = requests.delete(f"{webhook_url}/messages/{msg_id}", timeout=5)
                if res.status_code in (200, 204):
                    deleted_count += 1
            except requests.RequestException:
                pass

        window.after(
            0,
            lambda: messagebox.showinfo(
                "Delete Messages",
                f"Deleted {deleted_count} of {len(to_delete)} active message(s)."
            )
        )

    threading.Thread(target=_worker, daemon=True).start()
    
    
def on_close() -> None:
    """
    Completely quit and destroy the window, exiting the script.
    """
    window.quit()
    window.destroy()
    sys.exit(0)
    

def setting_configuration() -> None:
    """
    Configures and displays the audio detection settings.
    """
    window.grid_columnconfigure((0, 1), weight=1)
    
    title_label = Label(window, font=("Arial", 25), text="Enter your settings in the boxes below")
    title_label.grid(row=0, column=0, columnspan=2, pady=20)
    
    
    def add_field(
        text: str, 
        row: int, 
        default_val: int | float | str, 
        mask: str = ""
        ) -> Entry:
        """
        Create a labeled Entry field in the settings grid.
        
        Args:
            text (str): The label text beside the input box.
            row (int): The grid row index where the label and input box are placed.
            default_val (int | float | str): The initial value pre-filled inside the input box.
            mask (str, optional): Character used to obscure sensitive text (e.g., "*"). Defaults to "".

        Returns:
            Entry: The main Tkinter Entry object.
        """
        label = Label(window, font=("Arial", 20), text=text)
        label.grid(row=row, column=0, sticky="e", padx=10, pady=8)
        
        entry = Entry(window, font=("Arial", 18), bg="White", fg="Black", insertbackground="Black", show=mask)
        entry.insert(0, str(default_val))
        entry.grid(row=row, column=1, sticky="w", padx=10, pady=8)
        return entry
    
    
    def show_sensitive_info(
        userID: Entry,
        firstWebhookUrl: Entry,
        secondWebhookUrl: Entry,
    ) -> None:
        """
        Toggle the visibility of sensitive fields (i.e User ID and Discord webhook URLs).

        Args:
            userID (Entry): The Entry widget containing the Discord User ID.
            firstWebhookUrl (Entry): The Entry widget containing the alert webhook URL.
            secondWebhookUrl (Entry): The Entry widget containing the volume report webhook URL.
        """
        
        entries = (userID, firstWebhookUrl, secondWebhookUrl)
        is_hidden = userID.cget("show") == "*"

        for entry in entries:
            entry.config(show="" if is_hidden else "*")

        showInfo.config(text="Hide Sensitive Info" if is_hidden else "Show Sensitive Info")
        
    noise_threshold_entry = add_field("Noise Threshold: ", 1, noise_threshold)
    noise_floor_entry = add_field("Noise Floor: ", 2, noise_floor)
    sample_rate_entry = add_field("Sample Rate: ", 3, hertz_rate)
    ping_cooldown_entry = add_field("Ping Cooldown (s): ", 4, ping_cooldown)
    volume_report_cooldown_entry = add_field("Volume Report Cooldown (s): ", 5, volume_report_cooldown)
    Label(window, font=("Arial", 20), text="Ping User on Exceeded Threshold: ").grid(row=6, column=0, sticky="e", padx=10, pady=8)
    ping_user_var = tk.BooleanVar(value=ping_user_on_alert)
    Checkbutton(window, variable=ping_user_var).grid(row=6, column=1, sticky="w", padx=10, pady=8)
    user_id_entry = add_field("User ID: ", 7, USER_ID, mask="*")
    first_webhook_url_entry = add_field("First Webhook URL: ", 8, FIRST_DISCORD_WEBHOOK_URL, mask="*")
    second_webhook_url_entry = add_field("Second Webhook URL: ", 9, SECOND_DISCORD_WEBHOOK_URL, mask="*")
    
    submitButton = Button(
        window,
        font=("Arial", 16),
        text="Submit", 
        command=lambda: submit(
            noise_threshold_entry, 
            noise_floor_entry, 
            sample_rate_entry,
            ping_cooldown_entry,
            volume_report_cooldown_entry,
            ping_user_var,
            user_id_entry,
            first_webhook_url_entry,
            second_webhook_url_entry
        )
    )
    showInfo = Button(
        window,
        font=("Arial", 16),
        text="Show Sensitive Info",
        command=lambda: show_sensitive_info(
            user_id_entry,
            first_webhook_url_entry,
            second_webhook_url_entry
        )
    )
    submitButton.grid(row=10, column=0, columnspan=2, pady=20)
    showInfo.grid(row=11, column=0, columnspan=2)
    

def get_file_path(filename: str) -> Path:
    """
    Resolve the external file(s) beside the script or executable.
    """
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent / filename
    return Path(__file__).resolve().parent / filename


def load_config() -> dict:
    """
    Loads the configuration from CONFIG_FILE, creating it with default values if missing.

    Returns:
        dict: The loaded configuration dictionary merged with DEFAULT_CONFIG.
    """
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, indent=4)
        return DEFAULT_CONFIG.copy()
    
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        saved = json.load(f)
        return {**DEFAULT_CONFIG, **saved}


def save_config(cfg: dict) -> None:
    """
    Saves the given configuration dictionary to CONFIG_FILE as formatted JSON.

    Args:
        cfg (dict): The configuration dictionary to save.
    """
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4)


def validate_env() -> None:
    """
    Checks for whether an .env file is already existing in the user's directory.
    """
    global env_path

    if not env_path.exists():
        create_env = messagebox.askyesno(
            title="Missing .env File",
            message=(
                "No .env file was found in your directory.\n\n"
                "An .env file is required for Discord pings and live volume tracking.\n\n"
                "Do you want to create a new .env file now?"
            )
        )

        if create_env:
            with open(env_path, "w", encoding="utf-8") as f:
                f.write(env_template)
            messagebox.showinfo(
                title=".env File Created",
                message=(
                    f"Created .env file at:\n{env_path}\n\n"
                    "Please fill out your Discord Webhook URL(s) and User ID in the GUI."
                )
            )
        else:
            sys.exit(0)

    else:
        load_dotenv(dotenv_path=env_path, override=True)


def save_env(notify_url: str, volume_url: str, user_id: int | str) -> None:
    """
    Saves the Discord Webhook URLs and User ID to the .env file.
    """
    content = (
        "# Atleast ONE webhook URL MUST be filled in for the script to actually"
        "\n# do something inside of just quietly detecting for noise in the background."
        "\n\n# Discord Webhook URL for loud sound alerts"
        f'\nNOTIFY_USER_URL={notify_url}'
        "\n\n# Discord Webhook URL for live volume reports"
        f'\nVOLUME_REPORT_URL={volume_url}'
        "\n\n# Your Discord User ID (numbers only, required)"
        f'\nUSER_ID={user_id}\n'
    )
    env_path.write_text(content, encoding="utf-8")
    
env_template = (
    "# Atleast ONE webhook URL MUST be filled in for the script to actually"
    "\n# do something inside of just quietly detecting for noise in the background."
    "\n\n# Discord Webhook URL for loud sound alerts"
    '\nNOTIFY_USER_URL='
    "\n\n# Discord Webhook URL for live volume reports"
    '\nVOLUME_REPORT_URL='
    "\n\n# Your Discord User ID (numbers only, required)"
    '\nUSER_ID=\n'
)

notif_auto_delete_duration = 60  # seconds
volume_auto_delete_duration = 20  # seconds

noise_threshold = 0.1
noise_floor = 0.01
hertz_rate = 44100
ping_cooldown = 5.0
volume_report_cooldown = 2.0
ping_user_on_alert = True

env_path = get_file_path(".env")
CONFIG_FILE = get_file_path("config.json")
DEFAULT_CONFIG = {  # config.json
    "noise_threshold": 0.1,
    "noise_floor": 0.01,
    "sample_rate_hz": 44100,
    "ping_cooldown": 5.0,
    "volume_report_cooldown": 2.0,
    "ping_user_on_alert": True
}

last_volume_report_time = 0
active_messages = []
messages_lock = threading.Lock()

config = load_config()
noise_threshold = config["noise_threshold"]
noise_floor = config["noise_floor"]
hertz_rate = config["sample_rate_hz"]
ping_cooldown = config["ping_cooldown"]
volume_report_cooldown = config["volume_report_cooldown"]
ping_user_on_alert = config["ping_user_on_alert"]

config["noise_threshold"] = noise_threshold
config["noise_floor"] = noise_floor
config["sample_rate_hz"] = hertz_rate
config["ping_cooldown"] = ping_cooldown
config["volume_report_cooldown"] = volume_report_cooldown
config["ping_user_on_alert"] = ping_user_on_alert


def send_discord_ping(volume: float, delete_time: int) -> None:
    """
    Send a Discord notification when a sound exceeds the threshold.

    The notification mentions the configured user and includes the
    supplied sound-detection details. Successfully sent messages are
    automatically scheduled for deletion.

    Args:
        volume (float): Current normalized audio volume level.
        delete_time (int): Time it takes for a message to auto-delete.
    """
    if not FIRST_DISCORD_WEBHOOK_URL:
        return
    
    over_pct = round(((volume - noise_threshold) / noise_threshold) * 100)
    
    embed = {
        "title": "Audio Threshold Exceeded",
        "color": 0x5865F2,  # Blurple
        "fields": [
            {
                "name": "Metric",
                "value": "Live Volume\nThreshold",
                "inline": True,
            },
            {
                "name": "Value",
                "value": f"**{volume:.3f}\n{noise_threshold}**",
                "inline": True,
            },
            {
                "name": "Status",
                "value": f"**{over_pct}%** over Threshold\nDeletes <t:{delete_time}:R>",
                "inline": True,
            },
        ],
        "footer": {"text": f"Sample Rate: {hertz_rate}Hz - Cooldown: {ping_cooldown}s"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    data = {
        "content": f"**Sound Detected - <@{USER_ID}>**" if ping_user_on_alert else "**Sound Detected**",
        "embeds": [embed],
        "allowed_mentions": {"parse": ["users"]},
    }

    try:
        response = requests.post(
            f"{FIRST_DISCORD_WEBHOOK_URL}?wait=true", json=data, timeout=(2, 5)
        )
        if response.status_code in (200, 201):
            msg_id = response.json().get("id")
            auto_delete_msg(
                FIRST_DISCORD_WEBHOOK_URL,
                msg_id,
                notif_auto_delete_duration,
            )
    except requests.RequestException:
        pass


def send_volume_report(volume: float) -> None:
    """
    Send the current live volume level to a Discord webhook.

    The report includes the configured user's mention and the amount of
    time remaining before Discord automatically removes the message.

    Args:
        volume (float): Current normalized audio volume level.
    """
    if not SECOND_DISCORD_WEBHOOK_URL:
        return

    delete_time = int(time.time()) + volume_auto_delete_duration
    status = "Loud" if volume > noise_threshold else "Normal"

    embed = {
        "title": f"**Live Volume Report**",
        "description": f"<@{USER_ID}>",
        "color": 0x57F287,  # Bright green
        "fields": [
            {"name": "Metric", "value": "Volume\nFloor", "inline": True},
            {
                "name": "Level",
                "value": f"**{volume:.3f}**\n{noise_floor}",
                "inline": True,
            },
            {
                "name": "Status",
                "value": f"{status}\nDeletes <t:{delete_time}:R>",
                "inline": True,
            },
        ],
        "footer": {"text": f"Sample Rate: {hertz_rate}Hz"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    data = {
        "embeds": [embed],
        "allowed_mentions": {"parse": ["users"]},
    }

    try:
        response = requests.post(
            f"{SECOND_DISCORD_WEBHOOK_URL}?wait=true", json=data, timeout=(1, 3)
        )
        if response.status_code in (200, 201):
            msg_id = response.json().get("id")
            auto_delete_msg(
                SECOND_DISCORD_WEBHOOK_URL,
                msg_id,
                volume_auto_delete_duration,
            )
    except requests.RequestException:
        pass


def auto_delete_msg(webhook_url: str, msg_id: str, delay: int) -> None:
    """
    Delete a Discord webhook message after a specified delay.

    The message is tracked in active_messages while waiting for
    deletion. Regardless of whether deletion succeeds, the message is
    removed from the tracking list afterward.

    Args:
        webhook_url (str): URL of the webhook that sent the message.
        msg_id (str): ID of the Discord message to delete.
        delay (int): Number of seconds to wait before deleting the
            message.
    """
    if not webhook_url or not msg_id:
        return

    with messages_lock:
        active_messages.append((webhook_url, msg_id))

    time.sleep(delay)

    try:
        requests.delete(f"{webhook_url}/messages/{msg_id}", timeout=5)
    except requests.RequestException:
        pass
    finally:
        with messages_lock:
            if (webhook_url, msg_id) in active_messages:
                active_messages.remove((webhook_url, msg_id))
                

def update_volume_bar(vol: float) -> None:
    """
    Live volume bar in the window that monitors sound.

    Args:
        vol (float): Volume
    """
    if volume_bar is not None and volume_bar.winfo_exists():
        volume_bar["value"] = min(vol * 400, 100)
        

def find_audio_device() -> tuple[int, int]:
    """
    Find a suitable audio input device for detecting system audio.

    The function first searches for devices commonly associated with
    system-audio capture, such as virtual cables and stereo-mix devices.
    If none are found, it falls back to the first available input device.

    Returns:
        tuple: A tuple containing the selected device's index and
            maximum number of input channels.

    Raises:
        SystemExit: If audio devices cannot be queried or no valid
            input device is available.
    """
    try:
        devices = sd.query_devices()
    except Exception:
        show_fatal_error("Audio Device Failure", "Cannot query audio devices")
        sys.exit(1)

    for i, dev in enumerate(devices):
        name = dev["name"].lower()
        if dev["max_input_channels"] > 0 and (
            "cable" in name
            or "stereo mix" in name
            or "what u hear" in name
            or "loopback" in name
            or "blackhole" in name
        ):
            return i, dev["max_input_channels"]

    for i, dev in enumerate(devices):
        if dev["max_input_channels"] > 0:
            return i, dev["max_input_channels"]

    show_fatal_error("Audio Device Failure", "No valid audio input device(s) found")
    sys.exit(1)


DEVICE_INDEX, INPUT_CHANNELS = find_audio_device()
last_ping_time = 0


def audio_callback(
    indata: np.ndarray,
    frames: int,
    time_info: Any,
    status: Any,
    ) -> None:
    """
    Process incoming audio and report significant volume levels.

    The callback calculates the normalized volume of the incoming audio
    data. Volume levels above the noise floor are reported
    to Discord at the configured interval. Levels above the noise
    threshold additionally trigger a Discord sound-detection
    notification, subject to the ping cooldown.

    Args:
        indata (np.ndarray): Audio samples received from the input
            stream.
        frames (int): Number of audio frames contained in indata.
        time_info (Any): Timing information provided by the
            audio stream.
        status (Any): Current status information for the audio
            stream.
    """
    global last_ping_time, last_volume_report_time
    current_time = time.time()

    volume_norm = float(np.sqrt(np.mean(indata**2)))
    window.after(0, update_volume_bar, volume_norm)
    
    if volume_norm > noise_floor:
        if current_time - last_volume_report_time > volume_report_cooldown:
            last_volume_report_time = current_time
            threading.Thread(
                target=send_volume_report,
                args=(volume_norm,),
                daemon=True,
            ).start()

    if volume_norm > noise_threshold:
        if current_time - last_ping_time > ping_cooldown:
            delete_time = int(current_time) + notif_auto_delete_duration
            last_ping_time = current_time
            threading.Thread(
                target=send_discord_ping,
                args=(volume_norm, delete_time),
                daemon=True,
            ).start()


def audio_listener() -> None:
    """
    Actively listen for incoming device audio to check for
    exceeded thresholds and/or track live volume.
    """
    with sd.InputStream(
        device=DEVICE_INDEX,
        callback=audio_callback,
        channels=INPUT_CHANNELS,
        samplerate=hertz_rate,
    ):
        while True:
            time.sleep(1)
                    
                    
def main() -> None:  # Initilization
    """
    Initialize the environment, configure the GUI window, and start the main event loop.
    """
    global window, FIRST_DISCORD_WEBHOOK_URL, SECOND_DISCORD_WEBHOOK_URL, USER_ID

    window = tk.Tk()
    window.withdraw()
    validate_env()

    FIRST_DISCORD_WEBHOOK_URL = os.getenv("NOTIFY_USER_URL") or ""
    SECOND_DISCORD_WEBHOOK_URL = os.getenv("VOLUME_REPORT_URL") or ""
    USER_ID = os.getenv("USER_ID") or ""

    width = 800
    height = 800
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x = int((screen_width / 2) - (width / 2))
    y = int((screen_height / 2) - (height / 2))
    window.title(f"Sound Detector {version}")
    window.geometry(f"{width}x{height}+{x}+{y}")

    # Exit the entire script if the user clicks the window's 'X' button
    window.protocol("WM_DELETE_WINDOW", on_close)

    setting_configuration()
    window.deiconify()
    window.mainloop()

if __name__ == "__main__":
    main()
