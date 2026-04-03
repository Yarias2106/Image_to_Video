# Image to Video Converter

A desktop application that combines a still image and an audio track into a
downloadable MP4 video. Built with Python and a CustomTkinter GUI.

---

## Features

- Load any common image format (JPEG, PNG, BMP, TIFF, WEBP)
- Load any common audio format (MP3, WAV, OGG, FLAC, M4A, AAC, WMA)
- Trim the audio clip with precise start and end sliders
- Preview the selected audio slice before exporting
- Apply fade-in and fade-out effects to the audio
- Choose output resolution: original image size, 1080p, or 720p
- Export as MP4 with H.264 video and AAC audio

---

## Requirements

- Python 3.10 or later
- ffmpeg installed and available on your PATH (required by pydub and moviepy)

### Installing ffmpeg

**Windows:** Download from https://ffmpeg.org/download.html and add the `bin`
folder to your system PATH.

**macOS:**
```
brew install ffmpeg
```

**Linux (Debian/Ubuntu):**
```
sudo apt install ffmpeg
```

---

## Installation

1. Clone the repository:

```
git clone https://github.com/your-username/image-to-video.git
cd image-to-video
```

2. Create and activate a virtual environment (recommended):

```
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

3. Install dependencies:

```
pip install -r requirements.txt
```

---

## Usage

```
python main.py
```

The application window will open. The general workflow is:

1. Click **Load Image** and select your source image.
2. Click **Load Audio** and select your audio file.
3. Use the **Start** and **End** sliders to trim the audio to the desired range.
4. Click **Play** to preview the selected clip.
5. Optionally set **Fade in** and **Fade out** durations in seconds.
6. Choose the output resolution from the **Output quality** menu.
7. Click **Export MP4**, choose a save location, and wait for the progress bar to complete.

---

## Project Structure

```
image-to-video/
├── main.py               Entry point. Run this to start the app.
├── requirements.txt      Python dependencies.
├── README.md
└── src/
    ├── __init__.py
    ├── app.py            Main application window (CustomTkinter).
    ├── audio_handler.py  Audio loading, playback, and trimming (pydub + pygame).
    └── video_exporter.py Video rendering (MoviePy).
```

---

## Dependencies

| Library | Purpose |
|---|---|
| customtkinter | Modern dark-themed GUI widgets |
| moviepy | Combining image and audio into an MP4 |
| pydub | Audio trimming and fade effects |
| pygame | In-app audio playback preview |
| Pillow | Loading and displaying the image preview |

---

## Known Limitations

- The video contains a single static frame for the full duration of the audio.
  There is no animation or Ken Burns effect.
- Progress reporting during the MoviePy render step is approximate. The bar
  jumps from 25% to 100% because MoviePy does not expose per-frame callbacks
  in version 1.x without patching internals.
- Very large images (above 4K) may take significant time to process depending
  on your hardware.

---

## License

MIT License. See LICENSE for details.
