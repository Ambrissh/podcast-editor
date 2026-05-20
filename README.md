# 🌌 Metaverse Entangled — Podcast Editor

Welcome! **Metaverse Entangled** is my podcast, and I built this custom local editing studio to automate the tedious parts of my post-production workflow and dramatically speed up how I edit my episodes. 

Whether you need to generate quick, vertical **9:16 portrait shorts** (for Reels, TikTok, or YouTube Shorts) with stacked speakers and caption spaces, or you want to render a full landscape **16:9 episode** overlaying a beautiful animated background, this tool does it all locally on your machine.

---

## 🎨 Local Studio Web Interface

Here is a look at the custom-built, futuristic, starfield dark-themed web interface that processes everything locally—ensuring maximum privacy and zero latency.

![Metaverse Entangled Studio UI](assets/ui.png)

---

## ✨ Features

- **✦ Portrait Shorts Mode (9:16 vertical reels)**
  - Automatically crops and slices custom timestamps from a Zoom recording.
  - Stacks the speaker panel (right side of the recording) on top and the host panel (left side) on the bottom.
  - Generates an elegant center gap reserved specifically for captions.
  - Supports uploading custom video background loops or falls back to a sleek dark background.
  - Renders ready-to-publish vertical `1080x1920` clips.

- **◈ Landscape Full Episode Mode (16:9 side-by-side)**
  - Places host and guest side-by-side inside matching square panels (`880x880`).
  - Seamlessly blends both feeds over a beautiful, looped background animation.
  - Automatically stretches/loops the background to match the exact duration of the podcast.
  - Renders a clean `1920x1080` master episode.

---

## 🛠️ Core Files & Dependencies

This project is built to be simple and lightweight:

* **[app.py](app.py)**: The FastAPI local server that handles uploads, processes jobs asynchronously, and manages the editing pipeline.
* **[index.html](index.html)**: The modern, starfield-themed dashboard UI that lets you upload recordings and manage rendering progress.
* **[podcast_editor.py](podcast_editor.py)**: The underlying core command-line utility powered by FFmpeg for crop/scale/composition processing.
* **[requirements.txt](requirements.txt)**: List of Python packages required for the project.

### Prerequisites

This tool relies on **FFmpeg** and **FFprobe** to handle heavy-duty video cropping and compositing. They must be installed on your machine and available in your environment path:

#### On macOS:
```bash
brew install ffmpeg
```

#### On Linux:
```bash
sudo apt update
sudo apt install ffmpeg
```

---

## 🚀 Getting Started

### 1. Installation

Clone the repository and jump right in:

```bash
git clone https://github.com/Ambrissh/podcast-editor.git
cd podcast-editor
```

If you prefer using a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

Install the light dependencies:
```bash
pip install -r requirements.txt
```

---

## 🖥️ How to Use It

### Option A: The Local Web Studio (Easiest)

To spin up the web dashboard, simply run:

```bash
python app.py
```

This will automatically open the browser to `http://localhost:8000`. 
1. **For Shorts**: Drag-and-drop your Zoom recording, add your clip start/end timestamps, enter an optional caption, and click **Export Shorts**.
2. **For Full Episodes**: Upload your Zoom recording alongside your custom background loop video, and click **Export Full Episode**.
3. Download the final output directly from the page (or as a `.zip` file if exporting multiple clips)!

---

### Option B: The Command Line (Headless)

If you prefer using the terminal, you can call **[podcast_editor.py](podcast_editor.py)** directly:

#### 1. Generate Portrait Shorts:
Slice one or more vertical clips by providing comma-separated timestamps (in `MM:SS` format):
```bash
python podcast_editor.py --mode shorts --input zoom_recording.mp4 --segments 02:15-03:45,10:00-11:30
```

#### 2. Generate Full Landscape Episode:
Overlay the recording feeds over a background loop for the entire duration:
```bash
python podcast_editor.py --mode full --input zoom_recording.mp4 --bg background_loop.mp4
```

Processed videos will save automatically into the `./output/` directory.

---

## 📐 How It Works Under the Hood

The processing pipeline uses complex FFmpeg filters to restructure raw Zoom screen captures:

1. **Splitting the Feeds**: Since Zoom records host and guest side-by-side in a single `1280x720` frame, we split it in half to isolate the left panel (host) and right panel (guest).
2. **Resizing**: Resizes feeds dynamically depending on the selected mode:
   - For **Shorts**, scales them to `1080x880` to fill vertical screen widths.
   - For **Full Episodes**, scales them to symmetric `880x880` squares.
3. **Layering & Compositing**: Composites the cropped feeds on top of a dark or custom animated background layer, positioning them with exact paddings and gaps.

---

🔒 *Private & Fast: All media processing occurs 100% locally on your computer. None of your podcast assets or video files are ever uploaded to external servers.*
