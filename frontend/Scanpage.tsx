// ScanPage.tsx — replace or merge into your existing Scan page
// Adds camera capture + file upload → sends to Flask /ocr/analyze

import { useState, useRef } from "react";

interface ScanResult {
  success: boolean;
  ocr: {
    ingredients_extracted: string[];
    ingredient_count: number;
  };
}

interface ScanPageProps {
  userConditions: string[];   // from Profile page state
  userMedications: string[];  // from Profile page state
}

export default function ScanPage({ userConditions, userMedications }: ScanPageProps) {
  const [preview, setPreview] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ScanResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [rawText, setRawText] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);

  // ── Shared: convert file to base64 and send to Flask ──────────────────────
  const handleFile = async (file: File) => {
    if (!file) return;

    setError(null);
    setResult(null);

    // Show preview
    const reader = new FileReader();
    reader.onloadend = () => {
      const base64 = reader.result as string;
      setPreview(base64);
      sendToFlask(base64);
    };
    reader.readAsDataURL(file);
  };

  const sendToFlask = async (base64Image: string) => {
    setLoading(true);
    try {
      const response = await fetch("http://localhost:5000/ocr/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          image_base64: base64Image,
          conditions: userConditions,
          medications: userMedications,
          lang: "eng",
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        setError(data.error || "Analysis failed. Try better lighting.");
        return;
      }

      setResult(data);

    } catch (err) {
      setError("Could not reach the server. Is Flask running on port 5000?");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-xl mx-auto p-4 space-y-6">
      <h1 className="text-2xl font-medium text-gray-900">Scan Food Label</h1>

      {/* ── Input options ── */}
      <div className="grid grid-cols-2 gap-4">
        {/* Camera button (mobile — opens camera directly) */}
        <button
          className="flex flex-col items-center gap-2 p-4 border border-teal-200 rounded-xl bg-teal-50 hover:bg-teal-100 transition"
          onClick={() => cameraInputRef.current?.click()}
        >
          <span className="text-3xl">📷</span>
          <span className="text-sm font-medium text-teal-800">Take Photo</span>
          <span className="text-xs text-teal-600">Point at ingredient label</span>
        </button>

        {/* File upload (desktop testing) */}
        <button
          className="flex flex-col items-center gap-2 p-4 border border-gray-200 rounded-xl bg-gray-50 hover:bg-gray-100 transition"
          onClick={() => fileInputRef.current?.click()}
        >
          <span className="text-3xl">🖼️</span>
          <span className="text-sm font-medium text-gray-700">Upload Image</span>
          <span className="text-xs text-gray-500">JPG, PNG from files</span>
        </button>
      </div>

      {/* Hidden file inputs */}
      <input
        ref={cameraInputRef}
        type="file"
        accept="image/*"
        capture="environment"   // opens rear camera on mobile
        className="hidden"
        onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
      />
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
      />

      {/* ── Image preview ── */}
      {preview && (
        <div className="rounded-xl overflow-hidden border border-gray-200">
          <img src={preview} alt="Scanned label" className="w-full object-contain max-h-64" />
        </div>
      )}

      {/* ── Loading state ── */}
      {loading && (
        <div className="text-center py-8 space-y-2">
          <div className="animate-spin text-3xl">⏳</div>
          <p className="text-sm text-gray-500">Extracting ingredients...</p>
        </div>
      )}

      {/* ── Error state ── */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4">
          <p className="text-sm font-medium text-red-800">{error}</p>
          <ul className="mt-2 text-xs text-red-600 list-disc list-inside space-y-1">
            <li>Make sure the label text is clearly visible</li>
            <li>Good lighting — avoid shadows over the label</li>
            <li>Hold the camera steady, text should be sharp</li>
          </ul>
        </div>
      )}

      {/* ── Results ── */}
      {result?.success && (
        <div className="space-y-4">
          <div className="bg-teal-50 border border-teal-200 rounded-xl p-4">
            <p className="text-sm font-medium text-teal-800 mb-3">
              ✓ Found {result.ocr.ingredient_count} ingredients
            </p>
            <ol className="space-y-1">
              {result.ocr.ingredients_extracted.map((ing, i) => (
                <li key={i} className="text-sm text-teal-900 flex gap-2">
                  <span className="text-teal-400 font-mono text-xs mt-0.5">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <span>{ing}</span>
                </li>
              ))}
            </ol>
          </div>

          {/* TODO: wire result.verdict here once backend returns it */}
          <p className="text-xs text-gray-400 text-center">
            Wiring ML analysis verdict next...
          </p>
        </div>
      )}
    </div>
  );
}