import { useRef, useState } from "react";
import { SAMPLES } from "./data";
import { Tabs, tabPanelProps } from "./a11y";

export type Mode = "text" | "photo" | "barcode";

interface Props {
  running: boolean;
  onText: (t: string) => void;
  onPhoto: (dataUrl: string) => void;
  onBarcode: (code: string) => void;
}

export function Composer({ running, onText, onPhoto, onBarcode }: Props) {
  const [mode, setMode] = useState<Mode>("text");
  const [text, setText] = useState(SAMPLES[0].text);
  const [photo, setPhoto] = useState<string | null>(null);
  const [code, setCode] = useState("3017620422003");
  const [drag, setDrag] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const loadFile = async (f: File | undefined) => {
    if (!f || !f.type.startsWith("image/")) return;
    setPhoto(await downscale(f, 1600));
  };

  const [missing, setMissing] = useState("");

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (running) return;
    setMissing("");
    if (mode === "text") {
      if (text.trim()) return onText(text);
      setMissing("Type or paste the ingredient list first.");
      document.getElementById("ing")?.focus();
    }
    if (mode === "photo") {
      if (photo) return onPhoto(photo);
      setMissing("Choose a photo of the ingredient panel first.");
      document.getElementById("drop")?.focus();
    }
    if (mode === "barcode") {
      if (code.length >= 8) return onBarcode(code);
      setMissing("Enter at least 8 digits of the barcode.");
      document.getElementById("bc")?.focus();
    }
  };

  return (
    <form className="composer" onSubmit={submit} aria-labelledby="scan-heading" aria-busy={running}>
      <h2 id="scan-heading" className="sr-only">
        Scan a product
      </h2>
      <Tabs
        id="mode"
        label="How to read the product"
        value={mode}
        onChange={(m) => (setMode(m), setMissing(""))}
        options={[
          ["text", "Type ingredients"],
          ["photo", "Photo of label"],
          ["barcode", "Barcode"],
        ]}
      />

      <div className={`pane ${mode === "barcode" ? "barcode-pane" : ""}`} {...tabPanelProps("mode", mode)}>
        {mode === "text" && (
          <>
            <label className="field-label" htmlFor="ing">
              Ingredients, as printed on the pack
            </label>
            <textarea
              id="ing"
              className="specimen"
              value={text}
              onChange={(e) => setText(e.target.value)}
              rows={5}
              spellCheck={false}
              aria-describedby="ing-hint"
              aria-invalid={!!missing || undefined}
            />
            <p id="ing-hint" className="hint">
              Separate ingredients with commas.
            </p>
            <div className="samples" role="group" aria-labelledby="samples-label">
              <span id="samples-label">Try a sample</span>
              {SAMPLES.map((s) => (
                <button type="button" key={s.name} aria-pressed={text === s.text} className={text === s.text ? "on" : ""} onClick={() => setText(s.text)}>
                  {s.name}
                </button>
              ))}
            </div>
          </>
        )}

        {mode === "photo" && (
          <>
            <button
              type="button"
              id="drop"
              className={`drop ${drag ? "is-drag" : ""} ${photo ? "has-photo" : ""} ${running ? "is-scanning" : ""}`}
              onDragOver={(e) => (e.preventDefault(), setDrag(true))}
              onDragLeave={() => setDrag(false)}
              onDrop={(e) => (e.preventDefault(), setDrag(false), loadFile(e.dataTransfer.files[0]))}
              onClick={() => fileRef.current?.click()}
              aria-label={photo ? "Label photo chosen. Choose a different photo" : "Choose a photo of the ingredient panel"}
              aria-describedby="drop-hint"
            >
              {photo ? (
                <>
                  <img src={photo} alt="" />
                  <span className="scanline" aria-hidden />
                  <span className="corner tl" aria-hidden />
                  <span className="corner tr" aria-hidden />
                  <span className="corner bl" aria-hidden />
                  <span className="corner br" aria-hidden />
                </>
              ) : (
                <span className="drop-empty" aria-hidden>
                  <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <path d="M3 8V5a2 2 0 0 1 2-2h3M16 3h3a2 2 0 0 1 2 2v3M21 16v3a2 2 0 0 1-2 2h-3M8 21H5a2 2 0 0 1-2-2v-3" />
                    <path d="M7 9h10M7 12h8M7 15h6" />
                  </svg>
                  <b>Choose or drop a photo of the ingredient panel</b>
                </span>
              )}
            </button>
            <p id="drop-hint" className="hint">
              Flat, well-lit and close up reads best. Text is read with OCR, so a blurry photo may miss ingredients.
            </p>
            <input
              ref={fileRef}
              type="file"
              accept="image/*"
              capture="environment"
              className="sr-only"
              tabIndex={-1}
              aria-hidden
              onChange={(e) => loadFile(e.target.files?.[0])}
            />
          </>
        )}

        {mode === "barcode" && (
          <>
            <Bars code={code} />
            <label className="field-label" htmlFor="bc">
              Barcode number (EAN or UPC)
            </label>
            <input
              id="bc"
              className="bc-input"
              inputMode="numeric"
              autoComplete="off"
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 14))}
              aria-describedby="bc-hint"
              aria-invalid={!!missing || undefined}
            />
            <p id="bc-hint" className="hint">
              Digits only, usually 13. Looked up on Open Food Facts, then scored against your profile.
            </p>
          </>
        )}
      </div>

      {missing && (
        <p className="field-err" role="alert">
          {missing}
        </p>
      )}

      <button className="run" type="submit" disabled={running}>
        {running ? <span className="dots">Analysing</span> : "Analyse for this profile"}
      </button>
    </form>
  );
}

// EAN L-code patterns: draws a plausible barcode from whatever digits are typed.
const L = ["0001101", "0011001", "0010011", "0111101", "0100011", "0110001", "0101111", "0111011", "0110111", "0001011"];

function Bars({ code }: { code: string }) {
  const digits = code.padEnd(12, "0").slice(0, 12).split("").map(Number);
  const half = (ds: number[], invert: boolean) => ds.map((d) => (invert ? L[d].replace(/./g, (c) => (c === "1" ? "0" : "1")) : L[d])).join("");
  const bits = "101" + half(digits.slice(0, 6), false) + "01010" + half(digits.slice(6), true) + "101";
  const W = bits.length;
  return (
    <svg className="bars" aria-hidden viewBox={`0 0 ${W} 40`} preserveAspectRatio="none">
      {bits.split("").map((b, i) => {
        const guard = i < 3 || i >= W - 3 || (i >= 45 && i < 50);
        return b === "1" ? <rect key={i} x={i} y={0} width={1} height={guard ? 40 : 34} /> : null;
      })}
    </svg>
  );
}

function downscale(file: File, max: number): Promise<string> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      const k = Math.min(1, max / Math.max(img.width, img.height));
      const c = document.createElement("canvas");
      c.width = Math.round(img.width * k);
      c.height = Math.round(img.height * k);
      c.getContext("2d")!.drawImage(img, 0, 0, c.width, c.height);
      URL.revokeObjectURL(img.src);
      resolve(c.toDataURL("image/jpeg", 0.92));
    };
    img.onerror = reject;
    img.src = URL.createObjectURL(file);
  });
}
