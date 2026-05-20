# 🌌 [Metaverse Entangled](https://www.youtube.com/@MetaverseEntangled) — Podcast Editor

Welcome! **Metaverse Entangled** is my podcast, and I built this custom local editing studio to automate the tedious parts of my post-production workflow and dramatically speed up how I edit my episodes.

Whether you need to generate quick, vertical **9:16 portrait shorts** (for Reels, TikTok, or YouTube Shorts) with stacked speakers and caption spaces, or you want to render a full landscape **16:9 episode** overlaying a beautiful animated background, this tool does it all locally on your machine.

---

# 🎨 Local Studio Web Interface

Here is a look at the custom-built, futuristic, starfield dark-themed web interface that processes everything locally — ensuring maximum privacy and zero latency.

![Metaverse Entangled Studio UI](assets/ui.png)

---

# ✨ Features

## ✦ Portrait Shorts Mode (9:16 Vertical Reels)

- Automatically crops and slices custom timestamps from a Zoom recording.
- Stacks the speaker panel (right side of the recording) on top and the host panel (left side) on the bottom.
- Generates an elegant center gap reserved specifically for captions.
- Supports uploading custom video background loops or falls back to a sleek dark background.
- Renders ready-to-publish vertical `1080x1920` clips.

---

## ◈ Landscape Full Episode Mode (16:9 Side-by-Side)

- Places host and guest side-by-side inside matching square panels (`880x880`).
- Seamlessly blends both feeds over a beautiful, looped background animation.
- Automatically stretches/loops the background to match the exact duration of the podcast.
- Renders a clean `1920x1080` master episode.

---

# 🛠️ Core Files & Dependencies

This project is built to be simple and lightweight.

## Core Files

- **app.py**  
  The FastAPI local server that handles uploads, processes jobs asynchronously, and manages the editing pipeline.

- **index.html**  
  The modern, starfield-themed dashboard UI that lets you upload recordings and manage rendering progress.

- **podcast_editor.py**  
  The underlying core command-line utility powered by FFmpeg for crop/scale/composition processing.

- **requirements.txt**  
  List of Python packages required for the project.

---

# 📦 Prerequisites

This tool relies on **FFmpeg** and **FFprobe** for video cropping and compositing.

They must be installed and available in your system path.

## macOS

```bash
brew install ffmpeg
```

## Linux

```bash
sudo apt update
sudo apt install ffmpeg
```

---

# 🚀 Getting Started

## 1. Clone the Repository

```bash
git clone https://github.com/Ambrissh/podcast-editor.git
cd podcast-editor
```

---

## 2. Create a Virtual Environment (Optional but Recommended)

```bash
python3 -m venv venv
```

### Activate Environment

#### macOS/Linux

```bash
source venv/bin/activate
```

#### Windows

```bash
venv\Scripts\activate
```

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

# 🖥️ How to Use It

## Option A — Local Web Studio (Recommended)

Run the local dashboard:

```bash
python app.py
```

Then open:

```bash
http://localhost:8000
```

### Shorts Workflow

1. Upload your Zoom recording.
2. Add clip start/end timestamps.
3. Add optional captions.
4. Click **Export Shorts**.

### Full Episode Workflow

1. Upload your Zoom recording.
2. Upload a custom animated background.
3. Click **Export Full Episode**.

The rendered files can be downloaded directly from the dashboard.

---

## Option B — Command Line Usage

You can also use the editor directly from the terminal.

### Generate Portrait Shorts

```bash
python podcast_editor.py --mode shorts --input zoom_recording.mp4 --segments 02:15-03:45,10:00-11:30
```

---

### Generate Full Landscape Episode

```bash
python podcast_editor.py --mode full --input zoom_recording.mp4 --bg background_loop.mp4
```

Processed videos are automatically saved inside:

```bash
./output/
```

---

# 📐 How It Works Internally

The processing pipeline uses advanced FFmpeg filters to restructure raw Zoom recordings.

## Pipeline Overview

### 1. Feed Splitting

Zoom recordings contain both speakers side-by-side inside a single `1280x720` frame.

The editor splits:
- Left side → Host
- Right side → Guest

---

### 2. Dynamic Resizing

#### Shorts Mode
- Resizes feeds to `1080x880`
- Optimized for vertical content

#### Full Episode Mode
- Resizes both feeds into symmetric `880x880` squares

---

### 3. Layering & Composition

The editor composites the cropped feeds over:
- Animated backgrounds
- Dark themes
- Looping visual layers

All positioned with carefully tuned spacing and padding.

---

# 🔒 Privacy First

All processing happens **100% locally** on your computer.

No podcast assets, recordings, or video files are uploaded to external servers.

---

# 🌟 Future Plans

- AI auto clipping
- Speaker detection
- Automatic subtitles
- Viral short generation
- Background templates
- Cloud deployment
- Multi-platform exports

---

# 📄 License

MIT License

---

Built with passion for creators, podcasters, and deep conversations ❤️
