#!/usr/bin/env python3
"""
Podcast Editor - Local Web App
Run: python app.py
Open: http://localhost:8000
"""

import asyncio
import io
import json
import logging
import os
import shutil
import subprocess
import time
import uuid
import zipfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("podcast-editor")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "output"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

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
    jobs[job_id]["updated_at"] = time.time()
    logger.info("[%s] %s", job_id, label)
    logger.info("[%s] ffmpeg command: %s", job_id, " ".join(cmd))
    logger.info("[%s] ffmpeg started", job_id)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = result.stderr[-1000:]
        jobs[job_id]["updated_at"] = time.time()
        logger.error("[%s] ffmpeg failed: %s", job_id, result.stderr[-2000:])
        raise RuntimeError(f"ffmpeg failed: {result.stderr[-500:]}")
    jobs[job_id]["updated_at"] = time.time()
    logger.info("[%s] ffmpeg finished", job_id)


def require_output_file(path: str, job_id: str):
    output_path = Path(path)
    if not output_path.exists():
        raise FileNotFoundError(f"Expected output file was not created: {output_path}")
    if output_path.stat().st_size == 0:
        raise RuntimeError(f"Expected output file is empty: {output_path}")
    logger.info("[%s] output path generated: %s (%s bytes)", job_id, output_path, output_path.stat().st_size)


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
    with open(BASE_DIR / "index.html") as f:
        return f.read()


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(400, "No upload filename provided")

    ext = Path(file.filename).suffix.lower()
    if not ext:
        ext = ".mp4"

    uid = str(uuid.uuid4())[:8]
    filename = f"{uid}{ext}"
    path = UPLOAD_DIR / filename

    logger.info(
        "Receiving upload field='file' original='%s' content_type='%s' -> %s",
        file.filename,
        file.content_type,
        path,
    )

    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    size = path.stat().st_size
    if size == 0:
        path.unlink(missing_ok=True)
        logger.warning("Rejected empty upload: %s", file.filename)
        raise HTTPException(400, "Uploaded file is empty")

    try:
        duration = get_duration(str(path))
    except Exception as exc:
        logger.warning("Could not read duration for %s: %s", path, exc)
        duration = 0

    logger.info("Saved upload %s (%s bytes, %.2fs)", path, size, duration)
    return {
        "filename": filename,
        "original_filename": file.filename,
        "size": size,
        "duration": duration,
    }


@app.post("/export/shorts")
async def export_shorts(
    zoom_file: str = Form(...),
    segments: str = Form(...),
    bg_file: str = Form(""),
):
    job_id = str(uuid.uuid4())[:8]
    now = time.time()
    jobs[job_id] = {
        "status": "queued",
        "mode": "shorts",
        "progress": 0,
        "total": 0,
        "files": [],
        "created_at": now,
        "updated_at": now,
    }

    try:
        segs = json.loads(segments)
    except json.JSONDecodeError as exc:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = f"Invalid segments JSON: {exc}"
        jobs[job_id]["updated_at"] = time.time()
        raise HTTPException(400, "Invalid segments JSON") from exc

    if not segs:
        raise HTTPException(400, "At least one segment is required")

    jobs[job_id]["total"] = len(segs)
    jobs[job_id]["updated_at"] = time.time()

    input_path = str(UPLOAD_DIR / zoom_file)
    if not os.path.exists(input_path):
        logger.warning("[%s] Zoom file not found: %s", job_id, input_path)
        raise HTTPException(400, "Zoom file not found")

    bg_path = str(UPLOAD_DIR / bg_file) if bg_file else ""
    if bg_path and not os.path.exists(bg_path):
        logger.warning("[%s] Background file not found: %s", job_id, bg_path)
        raise HTTPException(400, "Background file not found")

    job_output_dir = OUTPUT_DIR / job_id
    job_output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(
        "[%s] Starting shorts export zoom=%s bg=%s segments=%s output_dir=%s",
        job_id,
        input_path,
        bg_path or "(dark fallback)",
        len(segs),
        job_output_dir,
    )

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
                jobs[job_id]["updated_at"] = time.time()
                await asyncio.to_thread(make_short, input_path, start, end, caption, out_file, job_id, label, bg_path)
                require_output_file(out_file, job_id)
                output_files.append(out_file)
                jobs[job_id]["progress"] = i + 1
                jobs[job_id]["updated_at"] = time.time()
            jobs[job_id]["status"] = "done"
            jobs[job_id]["files"] = output_files
            jobs[job_id]["updated_at"] = time.time()
            logger.info("[%s] Shorts export completed: %s", job_id, output_files)
        except Exception as e:
            jobs[job_id]["status"] = "error"
            jobs[job_id]["error"] = str(e)
            jobs[job_id]["updated_at"] = time.time()
            logger.exception("[%s] Shorts export failed", job_id)

    asyncio.create_task(process())
    return {"job_id": job_id}


@app.post("/export/full")
async def export_full(
    zoom_file: str = Form(...),
    bg_file: str = Form(...),
):
    job_id = str(uuid.uuid4())[:8]
    now = time.time()
    jobs[job_id] = {
        "status": "queued",
        "mode": "full",
        "progress": 0,
        "total": 1,
        "files": [],
        "created_at": now,
        "updated_at": now,
    }

    input_path = str(UPLOAD_DIR / zoom_file)
    bg_path = str(UPLOAD_DIR / bg_file)

    if not os.path.exists(input_path):
        logger.warning("[%s] Zoom file not found: %s", job_id, input_path)
        raise HTTPException(400, "Zoom file not found")
    if not os.path.exists(bg_path):
        logger.warning("[%s] Background file not found: %s", job_id, bg_path)
        raise HTTPException(400, "Background file not found")

    job_output_dir = OUTPUT_DIR / job_id
    job_output_dir.mkdir(parents=True, exist_ok=True)
    out_file = str(job_output_dir / "episode.mp4")
    logger.info(
        "[%s] Starting full export zoom=%s bg=%s output=%s",
        job_id,
        input_path,
        bg_path,
        out_file,
    )

    async def process():
        try:
            jobs[job_id]["status"] = "Processing full video..."
            jobs[job_id]["updated_at"] = time.time()
            await asyncio.to_thread(make_full, input_path, bg_path, out_file, job_id)
            require_output_file(out_file, job_id)
            jobs[job_id]["status"] = "done"
            jobs[job_id]["files"] = [out_file]
            jobs[job_id]["progress"] = 1
            jobs[job_id]["updated_at"] = time.time()
            logger.info("[%s] Full export completed: %s", job_id, out_file)
        except Exception as e:
            jobs[job_id]["status"] = "error"
            jobs[job_id]["error"] = str(e)
            jobs[job_id]["updated_at"] = time.time()
            logger.exception("[%s] Full export failed", job_id)

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
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
