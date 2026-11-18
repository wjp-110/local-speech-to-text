"use strict";

const MAX_RECORD_SECONDS = 60;
const ALLOWED_EXTENSIONS = [".wav", ".webm", ".ogg", ".mp3", ".m4a", ".flac"];

const elements = {
  language: document.getElementById("language"),
  startBtn: document.getElementById("startBtn"),
  stopBtn: document.getElementById("stopBtn"),
  status: document.getElementById("status"),
  timer: document.getElementById("timer"),
  fileInput: document.getElementById("fileInput"),
  fileName: document.getElementById("fileName"),
  uploadBtn: document.getElementById("uploadBtn"),
  result: document.getElementById("result"),
  resultLanguage: document.getElementById("resultLanguage"),
  duration: document.getElementById("duration"),
  processing: document.getElementById("processing"),
  copyBtn: document.getElementById("copyBtn"),
  error: document.getElementById("error"),
  liveMode: document.getElementById("liveMode"),
  livePanel: document.getElementById("livePanel"),
  liveResult: document.getElementById("liveResult"),
};

let mediaStream = null;
let recorder = null;
let chunks = [];
let startTime = 0;
let timerId = null;
let isBusy = false;
let liveChain = Promise.resolve();

function setStatus(text) {
  elements.status.textContent = text;
}

function showError(message) {
  elements.error.textContent = message;
  elements.error.hidden = false;
}

function clearError() {
  elements.error.textContent = "";
  elements.error.hidden = true;
}

function formatTime(seconds) {
  const total = Math.max(0, Math.floor(seconds));
  const mm = String(Math.floor(total / 60)).padStart(2, "0");
  const ss = String(total % 60).padStart(2, "0");
  return `${mm}:${ss}`;
}

function setBusy(busy) {
  isBusy = busy;
  elements.startBtn.disabled = busy || recorder !== null;
  elements.stopBtn.disabled = busy || recorder === null;
  elements.uploadBtn.disabled = busy;
}

function startTimer() {
  startTime = performance.now();
  elements.timer.textContent = "00:00";
  timerId = window.setInterval(() => {
    const elapsed = (performance.now() - startTime) / 1000;
    elements.timer.textContent = formatTime(elapsed);
    if (elapsed >= MAX_RECORD_SECONDS && recorder && recorder.state === "recording") {
      stopRecording();
    }
  }, 200);
}

function stopTimer() {
  if (timerId !== null) {
    window.clearInterval(timerId);
    timerId = null;
  }
}

function pickMimeType() {
  const candidates = [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/ogg;codecs=opus",
    "audio/ogg",
  ];
  if (typeof MediaRecorder === "undefined" || !MediaRecorder.isTypeSupported) {
    return "";
  }
  return candidates.find((type) => MediaRecorder.isTypeSupported(type)) || "";
}

function extensionFromMime(mime) {
  if (!mime) return ".webm";
  if (mime.includes("ogg")) return ".ogg";
  if (mime.includes("wav")) return ".wav";
  if (mime.includes("mp4")) return ".m4a";
  if (mime.includes("mpeg")) return ".mp3";
  return ".webm";
}

function extensionFromName(name) {
  const match = /\.[^.]+$/.exec(name || "");
  return match ? match[0].toLowerCase() : "";
}

function describeMediaError(error) {
  if (!error) return "Could not access the microphone.";
  if (error.name === "NotAllowedError" || error.name === "PermissionDeniedError") {
    return "Microphone permission was denied. Please allow access in your browser and try again.";
  }
  if (error.name === "NotFoundError" || error.name === "DevicesNotFoundError") {
    return "No microphone was found on this device.";
  }
  if (error.name === "NotReadableError") {
    return "The microphone is already in use by another application.";
  }
  return `Microphone error: ${error.message || error.name}`;
}

async function startRecording() {
  clearError();
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    showError("Microphone API is unavailable. Use Chrome/Edge on http://127.0.0.1 or HTTPS.");
    return;
  }
  if (typeof MediaRecorder === "undefined") {
    showError("MediaRecorder is not supported by this browser.");
    return;
  }

  setStatus("Requesting microphone permission...");
  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch (error) {
    setStatus("Permission failed");
    showError(describeMediaError(error));
    return;
  }

  chunks = [];
  const live = elements.liveMode.checked;
  elements.livePanel.hidden = !live;
  if (live) elements.liveResult.value = "";
  const mimeType = pickMimeType();
  try {
    recorder = mimeType
      ? new MediaRecorder(mediaStream, { mimeType })
      : new MediaRecorder(mediaStream);
  } catch (error) {
    mediaStream.getTracks().forEach((track) => track.stop());
    mediaStream = null;
    setStatus("Recorder error");
    showError(`Could not start recording: ${error.message}`);
    return;
  }

  const recorderMimeType = recorder.mimeType || mimeType;

  recorder.ondataavailable = (event) => {
    if (event.data && event.data.size > 0) chunks.push(event.data);
    if (live && chunks.length > 0) {
      submitLiveSnapshot(recorderMimeType, extensionFromMime(recorderMimeType));
    }
  };

  recorder.onstop = async () => {
    stopTimer();
    if (mediaStream) {
      mediaStream.getTracks().forEach((track) => track.stop());
      mediaStream = null;
    }
    recorder = null;
    const mime = recorderMimeType;
    const blob = new Blob(chunks, { type: mime || "audio/webm" });
    chunks = [];
    setBusy(false);
    setStatus("Recording finished");
    if (blob.size === 0) {
      showError("No audio was captured. Please try again.");
      return;
    }
    await submitAudio(blob, extensionFromMime(mime), "recording");
  };

  setBusy(false);
  elements.startBtn.disabled = true;
  elements.stopBtn.disabled = false;
  setStatus("Recording...");
  startTimer();
  if (live) recorder.start(4000);
  else recorder.start();
}

function stopRecording() {
  if (recorder && recorder.state !== "inactive") {
    setStatus("Stopping...");
    recorder.stop();
  }
}

function submitLiveSnapshot(mime, extension) {
  const snapshot = new Blob(chunks, { type: mime || "audio/webm" });
  if (snapshot.size === 0) return;

  liveChain = liveChain.then(async () => {
    const formData = new FormData();
    formData.append("file", new File([snapshot], `live${extension}`, { type: snapshot.type }));
    formData.append("language", elements.language.value);
    try {
      const response = await fetch("/api/transcribe", { method: "POST", body: formData });
      if (response.ok) {
        const payload = await response.json();
        if (payload.text) elements.liveResult.value = payload.text;
      }
    } catch {
      // Real-time preview is best-effort; the final result is submitted on stop.
    }
  });
}

async function submitAudio(blob, extension, source) {
  clearError();
  setBusy(true);
  setStatus("Uploading...");

  const file = new File([blob], `audio${extension}`, { type: blob.type || "" });
  const formData = new FormData();
  formData.append("file", file);
  formData.append("language", elements.language.value);

  try {
    setStatus("Recognizing...");
    const response = await fetch("/api/transcribe", {
      method: "POST",
      body: formData,
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.detail || `Server returned HTTP ${response.status}`);
    }

    elements.result.value = payload.text || "";
    elements.resultLanguage.textContent = payload.language || elements.language.value;
    elements.duration.textContent = `${Number(payload.duration_seconds || 0).toFixed(1)} s`;
    elements.processing.textContent = `${Number(payload.processing_seconds || 0).toFixed(2)} s`;
    elements.copyBtn.disabled = !payload.text;
    setStatus("Done");
  } catch (error) {
    setStatus("Failed");
    showError(`${source === "upload" ? "Upload" : "Recognition"} failed: ${error.message}`);
  } finally {
    setBusy(false);
  }
}

elements.startBtn.addEventListener("click", startRecording);
elements.stopBtn.addEventListener("click", stopRecording);

elements.liveMode.addEventListener("change", () => {
  elements.livePanel.hidden = !elements.liveMode.checked;
});

elements.fileInput.addEventListener("change", () => {
  const file = elements.fileInput.files[0];
  if (!file) {
    elements.fileName.textContent = "No file selected.";
    return;
  }
  elements.fileName.textContent = file.name;
  const ext = extensionFromName(file.name);
  if (!ALLOWED_EXTENSIONS.includes(ext)) {
    showError(`Unsupported file type '${ext}'. Supported: ${ALLOWED_EXTENSIONS.join(", ")}`);
    elements.uploadBtn.disabled = true;
    return;
  }
  clearError();
  elements.uploadBtn.disabled = isBusy;
});

elements.uploadBtn.addEventListener("click", () => {
  const file = elements.fileInput.files[0];
  if (!file) {
    showError("Please choose an audio file first.");
    return;
  }
  submitAudio(file, extensionFromName(file.name), "upload");
});

elements.copyBtn.addEventListener("click", async () => {
  const text = elements.result.value;
  if (!text) return;
  try {
    await navigator.clipboard.writeText(text);
    elements.copyBtn.textContent = "Copied!";
    window.setTimeout(() => (elements.copyBtn.textContent = "Copy"), 1500);
  } catch {
    elements.result.focus();
    elements.result.select();
    document.execCommand("copy");
    elements.copyBtn.textContent = "Copied!";
    window.setTimeout(() => (elements.copyBtn.textContent = "Copy"), 1500);
  }
});
