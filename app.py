#!/usr/bin/env python3
"""
Podcast Editor - Local Web App
Run: python app.py
Open: http://localhost:8000
"""

import asyncio
import io
import json
import os
import shutil
import subprocess
import uuid
import zipfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("./uploads")
OUTPUT_DIR = Path("./output")
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

jobs = {}


def ts_to_seconds(ts: str) -> float:
    parts = ts.strip().split(":")
    parts = [float(p) for p in parts]
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    elif len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    raise ValueError(f"Invalid timestamp: {ts}")


def get_duration(path: str) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True
    )
    return float(result.stdout.strip())


def run_ffmpeg(cmd: list, job_id: str, label: str):
    jobs[job_id]["status"] = label
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = result.stderr[-1000:]
        raise RuntimeError(f"ffmpeg failed: {result.stderr[-500:]}")


def make_short(input_path: str, start: float, end: float, caption: str,
               output_path: str, job_id: str, label: str, bg_path: str = ""):
    duration = end - start

    # Caption drawn in centre gap between panels (gap is y=733 to y=933, centre=833)
    caption_filter = ""
    if caption.strip():
        safe_caption = caption.replace("'", "\\'").replace(":", "\\:")
        caption_filter = (
            f",drawtext=text='{safe_caption}'"
            f":fontsize=48:fontcolor=white:fontfamily=Arial"
            f":x=(w-text_w)/2:y=833-(text_h/2)"
            f":shadowcolor=black:shadowx=2:shadowy=2"
        )

    if bg_path and os.path.exists(bg_path):
        # Background video mode
        filter_complex = (
            "[1:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920[bg];"
            "[0:v]crop=640:359:0:180,scale=1000:560[host];"
            "[0:v]crop=640:359:640:180,scale=1000:560[speaker];"
            "[bg][speaker]overlay=40:173[tmp];"
            f"[tmp][host]overlay=40:1147[v_base];"
            f"[v_base]null{caption_filter}[v]"
        )
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start),
            "-i", input_path,
            "-stream_loop", "-1", "-i", bg_path,
            "-t", str(duration),
            "-filter_complex", filter_complex,
            "-map", "[v]",
            "-map", "0:a",
            "-c:v", "libx264", "-crf", "18", "-preset", "fast",
            "-c:a", "aac", "-b:a", "192k",
            output_path
        ]
    else:
        # Dark background fallback
        filter_complex = (
            "[0:v]crop=640:359:640:180,scale=1000:560[speaker];"
            "[0:v]crop=640:359:0:180,scale=1000:560[host];"
            "color=#0d0d0d:s=1080x1920[bg];"
            "[bg][speaker]overlay=40:173[tmp];"
            f"[tmp][host]overlay=40:1147[v_base];"
            f"[v_base]null{caption_filter}[v]"
        )
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start),
            "-i", input_path,
            "-t", str(duration),
            "-filter_complex", filter_complex,
            "-map", "[v]",
            "-map", "0:a",
            "-c:v", "libx264", "-crf", "18", "-preset", "fast",
            "-c:a", "aac", "-b:a", "192k",
            output_path
        ]

    run_ffmpeg(cmd, job_id, label)


def make_full(input_path: str, bg_path: str, output_path: str, job_id: str):
    filter_complex = (
        "[1:v]scale=1280:720,setpts=PTS-STARTPTS[bg];"
        "[0:v]crop=640:359:0:180,scale=570:320[host];"
        "[0:v]crop=640:359:640:180,scale=570:320[speaker];"
        "[bg][host]overlay=46:200[tmp];"
        "[tmp][speaker]overlay=662:200[v]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-stream_loop", "-1", "-i", bg_path,
        "-filter_complex", filter_complex,
        "-map", "[v]",
        "-map", "0:a",
        "-c:v", "libx264", "-crf", "20", "-preset", "fast",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        output_path
    ]

    run_ffmpeg(cmd, job_id, "Processing full episode...")


@app.get("/", response_class=HTMLResponse)
async def index():
    with open("index.html") as f:
        return f.read()


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    ext = Path(file.filename).suffix
    uid = str(uuid.uuid4())[:8]
    filename = f"{uid}{ext}"
    path = UPLOAD_DIR / filename
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    try:
        duration = get_duration(str(path))
    except:
        duration = 0
    return {"filename": filename, "duration": duration}


@app.post("/export/shorts")
async def export_shorts(
    zoom_file: str = Form(...),
    segments: str = Form(...),
    bg_file: str = Form(""),
):
    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {"status": "starting", "progress": 0, "total": 0}

    segs = json.loads(segments)
    jobs[job_id]["total"] = len(segs)

    input_path = str(UPLOAD_DIR / zoom_file)
    if not os.path.exists(input_path):
        raise HTTPException(400, "Zoom file not found")

    bg_path = str(UPLOAD_DIR / bg_file) if bg_file else ""

    job_output_dir = OUTPUT_DIR / job_id
    job_output_dir.mkdir(exist_ok=True)

    async def process():
        try:
            output_files = []
            for i, seg in enumerate(segs):
                start = ts_to_seconds(seg["start"])
                end = ts_to_seconds(seg["end"])
                caption = seg.get("caption", "")
                out_file = str(job_output_dir / f"short_{i+1:02d}.mp4")
                label = f"Exporting short {i+1}/{len(segs)}..."
                jobs[job_id]["progress"] = i
                make_short(input_path, start, end, caption, out_file, job_id, label, bg_path)
                output_files.append(out_file)
                jobs[job_id]["progress"] = i + 1
            jobs[job_id]["status"] = "done"
            jobs[job_id]["files"] = output_files
        except Exception as e:
            jobs[job_id]["status"] = "error"
            jobs[job_id]["error"] = str(e)

    asyncio.create_task(process())
    return {"job_id": job_id}


@app.post("/export/full")
async def export_full(
    zoom_file: str = Form(...),
    bg_file: str = Form(...),
):
    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {"status": "starting", "progress": 0, "total": 1}

    input_path = str(UPLOAD_DIR / zoom_file)
    bg_path = str(UPLOAD_DIR / bg_file)

    if not os.path.exists(input_path):
        raise HTTPException(400, "Zoom file not found")
    if not os.path.exists(bg_path):
        raise HTTPException(400, "Background file not found")

    job_output_dir = OUTPUT_DIR / job_id
    job_output_dir.mkdir(exist_ok=True)
    out_file = str(job_output_dir / "episode.mp4")

    async def process():
        try:
            make_full(input_path, bg_path, out_file, job_id)
            jobs[job_id]["status"] = "done"
            jobs[job_id]["files"] = [out_file]
        except Exception as e:
            jobs[job_id]["status"] = "error"
            jobs[job_id]["error"] = str(e)

    asyncio.create_task(process())
    return {"job_id": job_id}


@app.get("/job/{job_id}")
async def job_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(404, "Job not found")
    return jobs[job_id]


@app.get("/download/{job_id}")
async def download(job_id: str):
    if job_id not in jobs:
        raise HTTPException(404)
    job = jobs[job_id]
    if job["status"] != "done":
        raise HTTPException(400, "Job not complete")

    files = job["files"]
    if len(files) == 1:
        return FileResponse(files[0], filename=Path(files[0]).name, media_type="video/mp4")

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            zf.write(f, Path(f).name)
    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=shorts.zip"}
    )


if __name__ == "__main__":
    import uvicorn
    import webbrowser
    import threading

    def open_browser():
        import time
        time.sleep(1.2)
        webbrowser.open("http://localhost:8000")

    threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")
