# ArcPath

ArcPath is a Flask web app that turns geotagged photos into an interactive travel map. Upload JPG, TIFF, HEIC, or HEIF images with GPS metadata, and ArcPath builds a route with photo markers, trip stats, a timeline panel, animated trace playback, QR-based phone upload, and export tools for HTML, GeoJSON, and GPX.

## Features

- Upload multiple geotagged photos at once
- Extract GPS coordinates and capture timestamps from EXIF metadata
- Sort photos into a timeline by capture time
- Generate an interactive Folium/Leaflet map
- Draw a routed path between photo locations using OSRM
- Play an animated trace of the trip
- View trip stats such as photo count, distance, duration, and average gap
- Open photo cards, timeline entries, and lightbox-style previews
- Upload from a phone by scanning a local QR code
- Export the route as HTML, GeoJSON, or GPX
- Use a built-in random map generator for development/demo testing

## Tech Stack

- Python
- Flask
- Folium / Leaflet
- Pillow
- pillow-heif
- qrcode
- OpenStreetMap tiles
- OSRM public routing API

## Requirements

Before you start, install:

- Python 3.10 or newer
- Git
- A modern browser

Recommended Python version: Python 3.11 or 3.12.

ArcPath can run locally on Windows, macOS, or Linux. The examples below use PowerShell because this project was developed on Windows.

## Quick Start

Clone the repo:

```powershell
git clone https://github.com/redstonejh/ArcPath.git
cd ArcPath
```

Create a virtual environment:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

Run the app:

```powershell
python app.py
```

Open the app in your browser:

```text
http://127.0.0.1:5000
```

## Full Setup Tutorial

### 1. Install Python

Download Python from:

```text
https://www.python.org/downloads/
```

During installation on Windows, check:

```text
Add python.exe to PATH
```

Verify Python is installed:

```powershell
python --version
```

You should see Python 3.10 or newer.

### 2. Install Git

Download Git from:

```text
https://git-scm.com/downloads
```

Verify Git is installed:

```powershell
git --version
```

### 3. Clone ArcPath

Choose a folder where you want the project to live, then run:

```powershell
git clone https://github.com/redstonejh/ArcPath.git
cd ArcPath
```

### 4. Create a Virtual Environment

A virtual environment keeps this project's Python packages separate from the rest of your computer.

```powershell
python -m venv .venv
```

### 5. Activate the Virtual Environment

On Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

On macOS/Linux:

```bash
source .venv/bin/activate
```

When it is active, your terminal usually shows `(.venv)` at the beginning of the prompt.

### 6. Install Project Dependencies

```powershell
pip install -r requirements.txt
```

This installs Flask, Folium, Pillow, HEIF image support, QR generation, and other required packages.

### 7. Start the Server

```powershell
python app.py
```

Flask will start a local server. Visit:

```text
http://127.0.0.1:5000
```

The app also binds to `0.0.0.0`, which means other devices on your local network can access it using your computer's local IP address.

## How to Use ArcPath

### Upload Photos from Your Computer

1. Open `http://127.0.0.1:5000`.
2. Click `Choose Files`.
3. Select multiple photos that contain GPS metadata.
4. Wait for ArcPath to process them.
5. Explore the generated map, route, timeline, and trace controls.

### Upload Photos from Your Phone

1. Start ArcPath on your computer with `python app.py`.
2. Make sure your phone and computer are on the same Wi-Fi network.
3. Open ArcPath in your desktop browser.
4. Click `Upload From Phone`.
5. Scan the QR code with your phone.
6. Upload photos from your phone through the page that opens.

If the QR code does not work, your computer's firewall may be blocking local network access, or your phone may be on a different network.

### Try the Demo Map

If you do not have geotagged photos ready, use the development demo:

1. Start the app.
2. Open the home page.
3. Click `DEV: Random Map`.

This creates a fake trip so you can test the map, timeline, and trace controls.

### Export Your Route

After generating a map:

1. Open the settings menu.
2. Choose `Export / Share`.
3. Select one of the export formats:

- `HTML Map` for a standalone map file
- `GeoJSON` for GIS/web mapping tools
- `GPX` for GPS and route tools
- `Copy Link` for the current local app URL

## Photo Requirements

ArcPath needs GPS metadata embedded in the image file.

Supported file types:

- `.jpg`
- `.jpeg`
- `.tif`
- `.tiff`
- `.heic`
- `.heif`

Photos must include latitude and longitude EXIF tags. Many phones include this automatically if location services are enabled for the camera app.

If ArcPath says no GPS coordinates were found:

- Check that location access is enabled for your camera app
- Avoid screenshots, edited exports, or compressed social media images
- Try the original photo file directly from the phone
- Make sure you did not strip metadata while transferring the image

## Project Structure

```text
ArcPath/
|-- app.py
|-- gen_cloud.py
|-- requirements.txt
|-- templates/
|   `-- index.html
|-- static/
|   |-- styles.css
|   |-- fog-cloud.png
|   |-- title-background.jpg
|   |-- title-background.png
|   `-- title-background.README.txt
|-- uploads/
|-- logs/
`-- README.md
```

Important files:

- `app.py` contains the Flask server, upload handling, EXIF parsing, route building, QR code endpoint, and app routes.
- `templates/index.html` contains the main interface and most client-side map interactions.
- `static/styles.css` contains the app styling.
- `requirements.txt` lists the Python packages needed to run the app.
- `uploads/` stores uploaded photos locally while the app is running.
- `logs/` is for local runtime logs if you choose to use them.

The `uploads/`, `logs/`, `.venv/`, and `__pycache__/` folders are ignored by Git so private photos and generated files are not accidentally committed.

## Configuration

ArcPath works with no required environment variables.

Optional environment variable:

```powershell
$env:SECRET_KEY="replace-this-with-a-random-secret"
```

Then run:

```powershell
python app.py
```

If `SECRET_KEY` is not set, the app uses a local development fallback.

## Networking Notes

ArcPath uses your local network for phone uploads. The QR code points to your computer's local IP address and the active Flask port.

For phone upload to work:

- Computer and phone should be on the same Wi-Fi network
- The Flask server must be running
- Your firewall must allow Python/Flask local network access
- The URL should look similar to `http://192.168.x.x:5000`

ArcPath also requests route geometry from the public OSRM demo API:

```text
http://router.project-osrm.org
```

If OSRM is unavailable or the request fails, ArcPath falls back to drawing a simpler direct path between photo points.

## Troubleshooting

### PowerShell Will Not Activate the Virtual Environment

If this command fails:

```powershell
.\.venv\Scripts\Activate.ps1
```

Run PowerShell as your user and allow local scripts:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Then try activating again.

### `python` Is Not Recognized

Install Python and make sure `Add python.exe to PATH` was selected. You can also try:

```powershell
py --version
py -m venv .venv
```

### HEIC or HEIF Photos Do Not Load

Make sure dependencies installed successfully:

```powershell
pip install -r requirements.txt
```

HEIC/HEIF support comes from `pillow-heif`.

### No GPS Coordinates Found

ArcPath can only map photos with embedded GPS metadata. Some apps remove metadata when exporting or sharing images. Use original photo files when possible.

### Phone Cannot Open the QR Link

Check that:

- Phone and computer are on the same network
- VPNs are disabled temporarily
- Windows Firewall allows Python through private networks
- You can open the local IP URL manually from your phone browser

### Port 5000 Is Already in Use

Stop the other server or run ArcPath from Python with a different port:

```powershell
python -c "from app import app; app.run(host='0.0.0.0', port=5001, debug=False)"
```

Then open:

```text
http://127.0.0.1:5001
```

## Development Workflow

Activate your virtual environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

Run the app:

```powershell
python app.py
```

Check Git status:

```powershell
git status
```

Commit changes:

```powershell
git add .
git commit -m "Describe your change"
git push
```

## Security and Privacy

Uploaded photos are stored locally in the `uploads/` folder. They are not committed to Git because `uploads/` is ignored.

Be careful before deploying ArcPath publicly. The current app is designed for local use and does not include user accounts, production authentication, or cloud storage controls.

## License

No license has been added yet. Add a license before distributing or accepting outside contributions.
