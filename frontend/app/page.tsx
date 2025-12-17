"use client";
import { useState } from "react";
import { Button, Input, Progress } from "@/components/ui";
import { Upload } from "lucide-react";

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [url, setUrl] = useState<string | null>(null);
  const [mode, setMode] = useState("instrumental_only");
  const [progress, setProgress] = useState(0);
  const [progressMessage, setProgressMessage] = useState("");
  const [startTime, setStartTime] = useState<number | null>(null);
  const [estimatedTimeLeft, setEstimatedTimeLeft] = useState<string>("");

  const handleUpload = async () => {
    if (!file) return;
    setLoading(true);
    setUrl(null);
    setProgress(0);
    setProgressMessage("Uploading...");
    setStartTime(Date.now());

    const formData = new FormData();
    formData.append("file", file);
    formData.append("mode", mode);

    try {
      const res = await fetch("/api/isolate", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        throw new Error("Upload failed");
      }

      const data = await res.json();
      const jobId = data.job_id;

      // Start listening to progress updates via SSE
      const eventSource = new EventSource(`/api/progress/${jobId}`);

      eventSource.onmessage = (event) => {
        const jobData = JSON.parse(event.data);

        setProgress(jobData.progress);
        setProgressMessage(jobData.message);

        // Calculate estimated time remaining
        if (startTime && jobData.progress > 0 && jobData.progress < 100) {
          const elapsed = Date.now() - startTime;
          const estimatedTotal = (elapsed / jobData.progress) * 100;
          const remaining = estimatedTotal - elapsed;

          const seconds = Math.ceil(remaining / 1000);
          if (seconds > 60) {
            const minutes = Math.floor(seconds / 60);
            const secs = seconds % 60;
            setEstimatedTimeLeft(`~${minutes}m ${secs}s remaining`);
          } else {
            setEstimatedTimeLeft(`~${seconds}s remaining`);
          }
        }

        if (jobData.status === "complete") {
          setUrl(jobData.output);
          setLoading(false);
          setEstimatedTimeLeft("");
          eventSource.close();
        } else if (jobData.status === "error") {
          alert(`Error: ${jobData.message}`);
          setLoading(false);
          setEstimatedTimeLeft("");
          eventSource.close();
        }
      };

      eventSource.onerror = () => {
        console.error("SSE connection error");
        eventSource.close();
        setLoading(false);
      };
    } catch (e) {
      console.error(e);
      alert("Something went wrong!");
      setLoading(false);
    }
  };

  const isVideoOutput = mode.includes("video");

  return (
    <div className="flex flex-col items-center justify-center min-h-screen gap-6 p-8 bg-neutral-950 text-white">
      <h1 className="text-3xl font-bold mb-4 tracking-tighter">
        Vocal Remover & Video Editor
      </h1>

      <div className="w-full max-w-md flex flex-col gap-4">
        <Input
          type="file"
          accept="audio/*,video/*"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
          className="cursor-pointer bg-neutral-900 border-neutral-800 text-neutral-200 file:text-blue-400 file:font-semibold"
        />

        <div className="flex flex-col gap-2">
          <label className="text-sm font-medium text-neutral-400">
            Processing Mode
          </label>
          <select
            value={mode}
            onChange={(e) => setMode(e.target.value)}
            className="flex h-10 w-full rounded-md border border-neutral-800 bg-neutral-900 px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <option value="instrumental_only">Instrumental Only (Audio)</option>
            <option value="vocals_only">Vocals Only (Audio)</option>
            <option value="video_no_vocals">Remove Vocals from Video</option>
            <option value="video_no_music">Remove Music from Video</option>
          </select>
        </div>

        <Button
          onClick={handleUpload}
          disabled={!file || loading}
          className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold"
        >
          {loading ? (
            "Processing..."
          ) : (
            <>
              <Upload className="mr-2 h-4 w-4" /> Start Processing
            </>
          )}
        </Button>
      </div>

      {loading && (
        <div className="flex flex-col items-center gap-3 w-full max-w-md">
          <div className="w-full bg-neutral-900 p-4 rounded-lg border border-neutral-800">
            <div className="flex justify-between items-center mb-2">
              <span className="text-sm font-medium text-neutral-300">
                {progressMessage}
              </span>
              <span className="text-sm font-bold text-blue-400">
                {progress}%
              </span>
            </div>
            <Progress value={progress} className="w-full h-2" />
            {estimatedTimeLeft && (
              <p className="text-xs text-neutral-500 mt-2 text-center">
                {estimatedTimeLeft}
              </p>
            )}
          </div>
        </div>
      )}

      {url && (
        <div className="mt-6 w-full max-w-2xl bg-neutral-900 p-4 rounded-xl border border-neutral-800">
          <p className="text-center mb-4 font-semibold text-green-400">
            Processing Complete!
          </p>
          {isVideoOutput ? (
            <video controls src={url} className="w-full rounded-lg" />
          ) : (
            <audio controls src={url} className="w-full" />
          )}
          <div className="mt-4 flex justify-center">
            <a
              href={url}
              download
              className="text-blue-400 hover:text-blue-300 text-sm underline"
            >
              Download Result
            </a>
          </div>
        </div>
      )}
    </div>
  );
}
