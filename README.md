<p align="center">
  <img src="https://github.com/user-attachments/assets/524a21bc-4520-4f7a-8129-a84b6ac04326" alt="Sound Detector Icon" width="128" height="128" />
  <br />
</p>

# Sound Detector

Sound Detector application that listens for your device audio and sends alerts to Discord  
when the detected volume passes a configurable threshold.

The bot can mention your Discord user, include the detected volume and a timestamp,  
and automatically delete alert messages after a set interval. An optional second webhook can report live volume levels.

**(Available on macOS and Windows)**

https://github.com/user-attachments/assets/2d4a51c3-b0a8-41b5-b2ab-c73317d9f6e9

*Music: "Ruder Buster" by Toby Fox*

## Features

* **Sound Detection:** Monitor audio input and trigger alerts above a configurable threshold.
* **Discord Notifications:** Send a message to a Discord channel and mention a user.
* **Live Volume (Optional):** Post volume readings through a second webhook, with readings above the threshold highlighted.
* **Automatic Cleanup:** Delete alert messages after 60 seconds and live volume messages after 20 seconds by default.
* **Customizable Settings:** Be able to change the noise threshold, noise floor, and etc through a GUI.  

<img width="383" height="177" alt="ExceededThreshold" src="https://github.com/user-attachments/assets/afbfd510-637f-4ca1-ac10-4d0416357cbd" />
<img width="310" height="210" alt="VolumeReport" src="https://github.com/user-attachments/assets/6faa9bd0-9f92-4eef-a307-4daad60a8e02" />

---

## Installation & Setup

### Requirements

* A macOS or Windows computer
* The Sound Detector executable for your operating system
* A Discord server, user ID, and webhook
* An audio input device that receives the sound you want to monitor
* A configured `.env` file (required for Discord notifications)
* A configured `config.json` file (to save sound detection settings)  

### Download and Run

Download the correct executable, depending on your OS from the project's Releases page.

#### macOS

Open the `.dmg` file and drag the Sound Detector app into the Applications folder.  
If macOS blocks you from opening the app, open **System Settings > Privacy & Security** and allow the app to run.  
Grant any requested microphone or audio input access so it can listen to the selected device.

#### Windows

Open the `.exe` file and double-click it.
If Windows SmartScreen displays a warning, confirm that the file came from the project's Releases page before choosing **More info > Run anyway**.  
Allow audio input access if Windows requests it.

Ensure your desktop session and selected audio input allow the program to capture the audio you want to monitor.

### Audio Device Setup

The program listens to an audio input device.  
To capture internal desktop or game audio, you may need a virtual audio device and must route the audio output to it.

On macOS, a virtual device such as BlackHole 2ch can route system audio to the program.  
On Windows, options can include VB-Cable or Stereo Mix / “What U Hear,” depending on the device and setup.  

Select and verify the appropriate input device in your system's audio settings.

---

## Configuration

Create a plain-text file named `.env` in the project directory (with no `.txt` extension).  
Running the script will check if you have one in your directory and ask if you would like to see its data.  
Add your webhook URL and Discord user ID data:  

```dotenv
NOTIFY_USER_URL=your_webhook_url
USER_ID=your_discord_user_id
```

For optional live volume reports, add a second webhook:

```dotenv
VOLUME_REPORT_URL=your_second_webhook_url
```

Keep webhook URLs private. You can configure additional user IDs in the script if you want other accounts to be mentioned.

To edit your settings, you can also change the values inside of the `config.json` file to your prefrences;  
though they automatically save to whatever you chose through the GUI that opens when using the application.

---

## Running the Program

Before starting the executable, make sure the `.env` file is in the same user directory  
you're running the application through, and contains a valid Discord webhook URL and user ID.  

Without this file, Discord notification data will not be available and alerts will not work.

Launch the downloaded executable for your operating system:

* **macOS:** Double-click the Sound Detector executable.
* **Windows:** Double-click the Sound Detector `.exe` file.

The program sends a Discord alert when the monitored audio exceeds the configured threshold.  
Successful alerts include the detected volume and a timestamp in America/New_York time.  
If enabled, live volume readings are posted to the second webhook.

## Troubleshooting

| Error | Common cause | What to check |
| --- | --- | --- |
| `requests.exceptions.MissingSchema` or `InvalidURL` | Missing or malformed webhook URL | Confirm `.env` exists and `NOTIFY_USER_URL` begins with `https://discord.com/api/webhooks/`. |
| `requests.exceptions.RequestException` | Network connection or Discord service issue | Check your connection and Discord availability, then retry. |
| `requests.exceptions.JSONDecodeError` | Discord returned a non-JSON error response | Check the connection and response handling in `send_discord_ping()`. |
| `sounddevice.PortAudioError` | Input device disconnected, unavailable, or busy | Check that the selected input or virtual audio device is connected and active. |
| `zoneinfo.ZoneInfoNotFoundError` | Time zone database is unavailable | Install system time zone data; on some Windows Python setups, install `tzdata`. |
| `ModuleNotFoundError` | Required Python package is missing | Install the packages listed under **Requirements**. |

---

## Developer Notes

Made with love by @Crystallization (@crystallizationn).

Package Versions:

* `requests==2.34.2`
* `numpy==2.5.2`
* `sounddevice==0.5.6`
* `python-dotenv==1.2.3`
* `tzdata==2026.6`
* `pytz==2026.3.post1` (for non-released version of v0.31)
* `pillow==13.0.0`  

Discord Color Values:

* Red: `0xFF0000`
* Green: `0x57F287`
* Yellow: `0xFEE75C`
* Blurple: `0x5865F2`
