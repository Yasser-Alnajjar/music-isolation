from fastapi import FastAPI, UploadFile, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
import tempfile
import os
import asyncio
import uuid
from typing import Dict
from isolate import isolate_music

app = FastAPI()

# Create media directory if it doesn't exist
MEDIA_DIR = "/media"
os.makedirs(MEDIA_DIR, exist_ok=True)

app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")

# Store job progress
job_progress: Dict[str, Dict] = {}

@app.post("/isolate")
async def isolate(
    file: UploadFile,
    mode: str = Form("instrumental_only")
):
    """Start processing and return job ID"""
    # Save uploaded file
    suffix = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    # Create a unique output directory in media
    job_id = str(uuid.uuid4())
    output_dir = os.path.join(MEDIA_DIR, job_id)
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize job progress
    job_progress[job_id] = {
        "progress": 0,
        "message": "Starting...",
        "status": "processing",
        "output": None,
        "tmp_path": tmp_path,
        "output_dir": output_dir,
        "mode": mode
    }
    
    # Start processing in background
    asyncio.create_task(process_job(job_id, tmp_path, output_dir, mode))
    
    return {"status": "ok", "job_id": job_id}

async def process_job(job_id: str, tmp_path: str, output_dir: str, mode: str):
    """Process the job in background"""
    def progress_callback(percent: int, message: str):
        job_progress[job_id]["progress"] = percent
        job_progress[job_id]["message"] = message
    
    try:
        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        result_path = await loop.run_in_executor(
            None,
            lambda: isolate_music(tmp_path, output_dir, mode, progress_callback)
        )
        
        # relative path for the url
        relative_path = os.path.relpath(result_path, MEDIA_DIR)
        full_url = f"/media/{relative_path}"
        
        job_progress[job_id]["status"] = "complete"
        job_progress[job_id]["output"] = full_url
        job_progress[job_id]["progress"] = 100
        job_progress[job_id]["message"] = "Complete!"
    except Exception as e:
        job_progress[job_id]["status"] = "error"
        job_progress[job_id]["message"] = str(e)
    finally:
        # Cleanup temp upload file
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

@app.get("/progress/{job_id}")
async def progress_stream(job_id: str):
    """Stream progress updates via SSE"""
    async def event_generator():
        last_progress = -1
        while True:
            if job_id not in job_progress:
                yield f"data: {{'error': 'Job not found'}}\n\n"
                break
            
            job = job_progress[job_id]
            
            # Only send update if progress changed
            if job["progress"] != last_progress:
                import json
                yield f"data: {json.dumps(job)}\n\n"
                last_progress = job["progress"]
            
            # Stop streaming when complete or error
            if job["status"] in ["complete", "error"]:
                break
            
            await asyncio.sleep(0.5)  # Check every 500ms
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
