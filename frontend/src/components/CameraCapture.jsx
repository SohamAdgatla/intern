import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Camera capture using getUserMedia with mobile fallback to file input + capture attribute.
 */
export default function CameraCapture({ onCapture, disabled }) {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  const fileInputRef = useRef(null);

  const [previewUrl, setPreviewUrl] = useState(null);
  const [capturedFile, setCapturedFile] = useState(null);
  const [cameraActive, setCameraActive] = useState(false);
  const [error, setError] = useState(null);

  const stopCamera = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    setCameraActive(false);
  }, []);

  useEffect(() => () => stopCamera(), [stopCamera]);

  const startCamera = async () => {
    setError(null);
    try {
      stopCamera();
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: "environment" } },
        audio: false,
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      setCameraActive(true);
    } catch {
      setError("Camera access unavailable. Use “Choose photo” below instead.");
    }
  };

  const applyCapture = (file, url) => {
    setCapturedFile(file);
    setPreviewUrl(url);
    onCapture?.(file);
    stopCamera();
  };

  const captureFrame = () => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(video, 0, 0);

    canvas.toBlob(
      (blob) => {
        if (!blob) return;
        const file = new File([blob], `capture-${Date.now()}.jpg`, { type: "image/jpeg" });
        applyCapture(file, URL.createObjectURL(blob));
      },
      "image/jpeg",
      0.92
    );
  };

  const handleFileChange = (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    if (!file.type.startsWith("image/")) {
      setError("Please select an image file.");
      return;
    }
    applyCapture(file, URL.createObjectURL(file));
  };

  const clearCapture = () => {
    setCapturedFile(null);
    setPreviewUrl(null);
    onCapture?.(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-600 dark:text-slate-300">
        Photograph a lab report, glucose meter, or blood pressure screen. Your photo is stored securely with your record.
      </p>

      {error && (
        <p className="rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:bg-amber-900/30 dark:text-amber-100" role="alert">
          {error}
        </p>
      )}

      {!previewUrl ? (
        <div className="overflow-hidden rounded-2xl border border-slate-200 bg-slate-900 dark:border-slate-600">
          <video
            ref={videoRef}
            className={`aspect-video w-full object-cover ${cameraActive ? "block" : "hidden"}`}
            playsInline
            muted
            aria-label="Camera preview"
          />
          {!cameraActive && (
            <div className="flex aspect-video items-center justify-center bg-slate-800 text-slate-300">
              <p className="px-4 text-center text-sm">Tap “Open camera” to photograph your result</p>
            </div>
          )}
        </div>
      ) : (
        <div className="overflow-hidden rounded-2xl border border-clinical-200">
          <img src={previewUrl} alt="Captured health reading" className="max-h-80 w-full object-contain bg-black" />
        </div>
      )}

      <canvas ref={canvasRef} className="hidden" aria-hidden="true" />

      <div className="flex flex-wrap gap-3">
        {!previewUrl && (
          <>
            <button
              type="button"
              disabled={disabled}
              onClick={startCamera}
              className="rounded-xl bg-clinical-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-clinical-700 disabled:opacity-50"
            >
              Open camera
            </button>
            {cameraActive && (
              <button
                type="button"
                disabled={disabled}
                onClick={captureFrame}
                className="rounded-xl bg-story-trust px-4 py-2.5 text-sm font-semibold text-white hover:opacity-90"
              >
                Take photo
              </button>
            )}
          </>
        )}

        <button
          type="button"
          disabled={disabled}
          onClick={() => fileInputRef.current?.click()}
          className="rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-story-trust hover:bg-slate-50 dark:border-slate-600 dark:bg-slate-800 dark:text-white"
        >
          Choose photo
        </button>

        {previewUrl && (
          <button
            type="button"
            disabled={disabled}
            onClick={clearCapture}
            className="rounded-xl px-4 py-2.5 text-sm font-semibold text-red-700 hover:bg-red-50"
          >
            Retake
          </button>
        )}
      </div>

      <input
        ref={fileInputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        capture="environment"
        className="sr-only"
        onChange={handleFileChange}
        aria-label="Upload photo from camera or gallery"
      />
    </div>
  );
}
