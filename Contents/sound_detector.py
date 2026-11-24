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
from typing import Any
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv

# Sound Detector Script
# v1.3.1

version = "v1.3.1"

def submit(
    soundThresholdEntry: Entry,
    noiseFloorEntry: Entry,
    sampleRateEntry: Entry,
    pingCooldownEntry: Entry,
    volumeReportCooldownEntry: Entry,
    ):
    """
    Get the submitted values for the settings configuration from the user.

    Args:
        soundThresholdEntry (Entry): The sound threshold value from the user.
        noiseFloorEntry (Entry): The noise floor value from the user.
        sampleRateEntry (Entry): The hertz rate value from the user.
        pingCooldownEntry (Entry): The ping cooldown (seconds) from the user.
        volumeReportCooldownEntry (Entry): The volume report cooldown (seconds) from the user.
    """
    global noise_threshold, noise_floor, hertz_rate, ping_cooldown, volume_report_cooldown

    try:
        noise_threshold = float(soundThresholdEntry.get())
        noise_floor = float(noiseFloorEntry.get())
        hertz_rate = int(sampleRateEntry.get())
        ping_cooldown = float(pingCooldownEntry.get())
        volume_report_cooldown = float(volumeReportCooldownEntry.get())
        
        if any(x < 0 for x in (noise_floor, ping_cooldown, volume_report_cooldown)):
            raise ValueError
        elif noise_threshold <= 0:
            raise ValueError
        elif hertz_rate < 44100:
            raise ValueError
        
    except ValueError:
        print("[ERROR] Invalid values, enter your settings again.")
        return

    config["noise_threshold"] = noise_threshold
    config["noise_floor"] = noise_floor
    config["sample_rate_hz"] = hertz_rate
    config["ping_cooldown"] = ping_cooldown
    config["volume_report_cooldown"] = volume_report_cooldown
    save_config(config)

    print(f"Sound Threshold: {noise_threshold}")
    print(f"Noise Floor: {noise_floor}")
    print(f"Sample Rate: {hertz_rate}")
    print(f"Ping Cooldown: {ping_cooldown}")
    print(f"Volume Report Cooldown: {volume_report_cooldown}")

    window.withdraw()
    window.update()
    window.destroy()


def setting_configuration():
    """
    Configures and displays the audio detection settings.
    """
    
    window.grid_columnconfigure((0, 1), weight=1)
    
    title_label = Label(window, font=("Arial", 25), text="Enter your settings in the boxes below")
    title_label.grid(row=0, column=0, columnspan=2, pady=20)
    
    def add_field(text, row, default_val):
        label = Label(window, font=("Arial", 20), text=text)
        label.grid(row=row, column=0, sticky="e", padx=10, pady=8)
        
        entry = Entry(window, font=("Arial", 18), bg="White", fg="Black", insertbackground="Black")
        entry.insert(0, str(default_val))
        entry.grid(row=row, column=1, sticky="w", padx=10, pady=8)
        return label, entry

    sound_threshold_label, sound_threshold_entry = add_field("Sound Threshold: ", 1, noise_threshold)
    noise_floor_label, noise_floor_entry = add_field("Noise Floor: ", 2, noise_floor)
    sample_rate_label, sample_rate_entry = add_field("Sample Rate: ", 3, hertz_rate)
    ping_cooldown_label, ping_cooldown_entry = add_field("Ping Cooldown (s): ", 4, ping_cooldown)
    volume_report_cooldown_label, volume_report_cooldown_entry = add_field("Volume Report Cooldown (s): ", 5, volume_report_cooldown)

    submitButton = Button(
        window,
        font=("Arial", 16),
        text="Submit", 
        command=lambda: submit(
            sound_threshold_entry, 
            noise_floor_entry, 
            sample_rate_entry,
            ping_cooldown_entry,
            volume_report_cooldown_entry,
        )
    )
    submitButton.grid(row=6, column=0, columnspan=2, pady=20)


def get_file_path(filename: str) -> Path:
    """
    Resolve the external config.json file beside the script or executable.
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
        
env_template = (
    "# Discord Webhook URL for loud sound alerts (required)\n"
    'NOTIFY_USER_URL=\n\n'
    "# Discord Webhook URL for live volume reports (optional)\n"
    'VOLUME_REPORT_URL=\n\n'
    "# Your Discord User ID (numbers only, required)\n"
    'FIRST_USER_ID=\n'
)

env_path = get_file_path(".env")
    

def validate_env():
    """
    Checks for whether an .env file is already existing in the user's directory.
    """
    global env_path
    
    if not env_path.exists():
        print("[WARNING] No .env file was created in the user directory")
        print("A .env file is required to recieve Discord pings and live volume tracking.")
        create_env = input("Do you want to create a new .env file "
                           "with all required details inside? (Y/N) ").upper().strip()
    
        if create_env == "Y":
            print("237 INFO: Creating file for user because .env is non-existent")

            with open(env_path, "w", encoding="utf-8") as f:
                f.write(env_template)
                time.sleep(0.5)
                print("288 INFO: Created local .env file in user workspace directory")
                print("[INSTRUCTIONS] Fill out the details inside of the .env file "
                      "in order to be mentioned through Discord.")
            sys.exit(1)
        
    elif env_path.exists():
        load_dotenv(dotenv_path=env_path, override=True)
        view_env = input("Do you want to view your .env data? (Y/N) ").upper().strip()
    
        if view_env == "Y":
            print()
            print('=' * 79)
            print("\n" + env_path.read_text(encoding="utf-8"))
            print("Double check that your .env data is up to date and meets utf-8 standards.\n")
            print('=' * 79)
            print()
            time.sleep(1)

notif_auto_delete_duration = 60  # seconds
volume_auto_delete_duration = 20  # seconds

noise_threshold = 0.1
noise_floor = 0.01
hertz_rate = 44100
ping_cooldown = 5.0
volume_report_cooldown = 2.0
ping_user_on_alert = True

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
config["volume_report_cooldown"] = volume_report_cooldown
config["ping_cooldown"] = ping_cooldown


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
        print("[ERROR] Cannot query audio devices")
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

    print("[ERROR] No valid audio input device(s) found")
    sys.exit(1)


DEVICE_INDEX, INPUT_CHANNELS = find_audio_device()
last_ping_time = 0


def auto_delete_msg(webhook_url: str, msg_id: str, delay: int):
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


def send_discord_ping(volume: float, delete_time: int):
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
        "content": f"**Sound Detected - <@{FIRST_USER_ID}>**" if ping_user_on_alert else "**Sound Detected**",
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
    except requests.RequestException as e:
        print(f"[WARNING] Failed to send notification: {e}")


def send_volume_report(volume: float):
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
        "description": f"<@{FIRST_USER_ID}>",
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
    except requests.RequestException as e:
        print(f"[WARNING] Failed to send volume report: {e}")
        

def audio_callback(
    indata: np.ndarray,
    frames: int,
    time_info: Any,
    status: Any,
):
    """
    Process incoming audio and report significant volume levels.

    The callback calculates the normalized volume of the incoming audio
    data. Volume levels above the noise floor are printed and reported
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

    if volume_norm > noise_floor:
        print(f"Volume: {volume_norm:.3f}")

        if current_time - last_volume_report_time > volume_report_cooldown:
            last_volume_report_time = current_time
            threading.Thread(
                target=send_volume_report,
                args=(volume_norm,),
                daemon=True,
            ).start()

    if volume_norm > noise_threshold:
        if current_time - last_ping_time > ping_cooldown:
            print(f"*** Noise Detected! Volume Level: {volume_norm:.3f} ***")
            delete_time = int(current_time) + notif_auto_delete_duration
            last_ping_time = current_time
            threading.Thread(
                target=send_discord_ping,
                args=(volume_norm, delete_time),
                daemon=True,
            ).start()


def main():  # Initilization
    global window, FIRST_DISCORD_WEBHOOK_URL, SECOND_DISCORD_WEBHOOK_URL, FIRST_USER_ID

    validate_env()

    FIRST_DISCORD_WEBHOOK_URL = os.getenv("NOTIFY_USER_URL")
    SECOND_DISCORD_WEBHOOK_URL = os.getenv("VOLUME_REPORT_URL")
    FIRST_USER_ID = os.getenv("FIRST_USER_ID")

    window = tk.Tk()
    width = 700
    height = 500
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x = int((screen_width / 2) - (width / 2))
    y = int((screen_height / 2) - (height / 2))
    window.title(f"Sound Detector {version}")
    window.geometry(f"{width}x{height}+{x}+{y}")

    # Exit the entire script if the user clicks the window's 'X' button
    window.protocol("WM_DELETE_WINDOW", lambda: sys.exit(0))

    setting_configuration()
    window.mainloop()

    try:
        print("\n" + "=" * 79 + "\n")
        print(
            f"Listening on device index {DEVICE_INDEX} "
            f"(Channels: {INPUT_CHANNELS} | Sample Rate: {hertz_rate}Hz)"
        )
        print(f"Noise Threshold: {noise_threshold} | Noise Floor: {noise_floor}\n")

        with sd.InputStream(
            device=DEVICE_INDEX,
            callback=audio_callback,
            channels=INPUT_CHANNELS,
            samplerate=hertz_rate,
        ):
            while True:
                time.sleep(1)

    except KeyboardInterrupt:
        print("\nExiting...")

if __name__ == "__main__":
    main()
