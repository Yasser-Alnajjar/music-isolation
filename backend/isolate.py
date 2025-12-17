import subprocess
import os
from pathlib import Path
import shutil
import time
import re
from typing import Callable, Optional

def isolate_music(
    input_path: str, 
    output_dir: str, 
    mode: str = "instrumental_only",
    progress_callback: Optional[Callable[[int, str], None]] = None
):
    """
    Process audio/video file to separate stems.
    
    Args:
        input_path: Path to input file
        output_dir: Directory for output files
        mode: Processing mode
        progress_callback: Optional callback(percentage, message) for progress updates
    """
    def report_progress(percent: int, message: str):
        if progress_callback:
            progress_callback(percent, message)
    
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Check if input is video (basic extension check or probe)
    video_exts = {'.mp4', '.mov', '.avi', '.mkv', '.webm'}
    ext = os.path.splitext(input_path)[1].lower()
    is_video = ext in video_exts
    
    audio_path = input_path
    report_progress(5, "Starting processing...")
    
    if is_video:
        # Extract audio from video
        report_progress(10, "Extracting audio from video...")
        audio_path = os.path.join(output_dir, "extracted_audio.wav")
        subprocess.run([
            "ffmpeg", "-y", "-i", input_path, "-vn", "-acodec", "pcm_s16le", audio_path
        ], check=True, capture_output=True)
        report_progress(20, "Audio extraction complete")
    else:
        report_progress(15, "Audio file detected")
        
    # Run Demucs with progress monitoring
    report_progress(25, "Separating audio stems (this may take a while)...")
    
    process = subprocess.Popen(
        [
            "demucs",
            "-n", "htdemucs",
            "--two-stems", "vocals",
            audio_path,
            "-o", output_dir,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True
    )
    
    # Monitor demucs progress
    base_progress = 25
    max_progress = 75
    last_percent = 0
    
    # Read from stderr where demucs outputs progress
    for line in process.stderr:
        # Demucs outputs progress like "0%" to "100%"
        match = re.search(r'(\d+)%', line)
        if match:
            demucs_percent = int(match.group(1))
            if demucs_percent > last_percent:
                # Map demucs 0-100% to our 25-75% range
                current_progress = base_progress + int((demucs_percent / 100) * (max_progress - base_progress))
                report_progress(current_progress, f"Processing audio stems... {demucs_percent}%")
                last_percent = demucs_percent
    
    process.wait()
    if process.returncode != 0:
        raise subprocess.CalledProcessError(process.returncode, "demucs")
    
    report_progress(75, "Stem separation complete")
    
    # Demucs creates a folder with the filename
    track_name = os.path.splitext(os.path.basename(audio_path))[0]
    demucs_out = os.path.join(output_dir, "htdemucs", track_name)
    
    vocals = os.path.join(demucs_out, "vocals.wav")
    no_vocals = os.path.join(demucs_out, "no_vocals.wav")
    
    final_audio = None
    
    # Determine which audio to use
    if mode == "vocals_only":
        final_audio = vocals
    elif mode == "instrumental_only":
        final_audio = no_vocals
    elif mode == "video_no_music":
        final_audio = vocals
    elif mode == "video_no_vocals":
        final_audio = no_vocals
    else:
        final_audio = no_vocals

    output_filename = f"output{ext}" if is_video else f"output.wav"
    final_output = os.path.join(output_dir, output_filename)

    if is_video and "video" in mode:
        report_progress(80, "Merging audio back into video...")
        subprocess.run([
            "ffmpeg", "-y",
            "-i", input_path,
            "-i", final_audio,
            "-c:v", "copy",
            "-map", "0:v:0",
            "-map", "1:a:0",
            final_output
        ], check=True, capture_output=True)
        report_progress(95, "Video processing complete")
    else:
        report_progress(85, "Finalizing audio file...")
        shutil.copy(final_audio, final_output)
        report_progress(95, "Audio processing complete")
    
    report_progress(100, "Processing finished!")
    return final_output
