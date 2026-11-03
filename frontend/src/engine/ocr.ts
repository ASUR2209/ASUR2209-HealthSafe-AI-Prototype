/* Browser version of backend/ocr_engine.py: Tesseract (via tesseract.js, WebAssembly)
   on a preprocessed copy of the photo, then the same ingredient parser. */

import type { Worker } from "tesseract.js";

let worker: Promise<Worker> | null = null;

function getWorker() {
  // Loaded on first use: the OCR engine and English data are a few MB from the CDN.
  worker ??= import("tesseract.js").then(async ({ createWorker, PSM }) => {
    const w = await createWorker("eng");
    await w.setParameters({ tessedit_pageseg_mode: PSM.SINGLE_BLOCK }); // --psm 6
    return w;
  });
  return worker;
}

/** preprocess_image(): upscale, greyscale, contrast ×3 (PIL ImageEnhance semantics). */
async function preprocess(dataUrl: string): Promise<HTMLCanvasElement> {
  // onload rather than img.decode(): decode() never settles in some embedded browsers.
  const img = await new Promise<HTMLImageElement>((resolve, reject) => {
    const i = new Image();
    i.onload = () => resolve(i);
    i.onerror = () => reject(new Error("Could not read that image"));
    i.src = dataUrl;
  });
  // The backend upscales 3×; cap the size so phones don't run out of memory.
  const scale = Math.min(3, 2400 / Math.max(img.width, img.height));
  const c = document.createElement("canvas");
  c.width = Math.round(img.width * scale);
  c.height = Math.round(img.height * scale);
  const ctx = c.getContext("2d", { willReadFrequently: true })!;
  ctx.imageSmoothingQuality = "high";
  ctx.drawImage(img, 0, 0, c.width, c.height);
  const px = ctx.getImageData(0, 0, c.width, c.height);
  const d = px.data;
  let sum = 0;
  for (let i = 0; i < d.length; i += 4) {
    const l = (d[i] * 299 + d[i + 1] * 587 + d[i + 2] * 114) / 1000;
    d[i] = l;
    sum += l;
  }
  const mean = Math.round(sum / (d.length / 4));
  for (let i = 0; i < d.length; i += 4) {
    const v = Math.max(0, Math.min(255, mean + 3 * (d[i] - mean)));
    d[i] = d[i + 1] = d[i + 2] = v;
  }
  ctx.putImageData(px, 0, 0);
  return c;
}

export async function extractText(dataUrl: string): Promise<string> {
  const [w, canvas] = await Promise.all([getWorker(), preprocess(dataUrl)]);
  const { data } = await w.recognize(canvas);
  return data.text;
}

/** parse_ingredients() from backend/ocr_engine.py. */
export function parseIngredients(rawText: string): string[] {
  const text = rawText.toLowerCase();
  if (!text.includes("ingredients")) return [];
  const start = text.indexOf("ingredients") + "ingredients".length;
  let section = rawText.slice(start).replace(/^[: \n]+|[: \n]+$/g, "");
  const low = section.toLowerCase();
  for (const stop of ["allergen", "may contain", "contains wheat", "numbers in brackets"]) {
    if (low.includes(stop)) {
      section = section.slice(0, low.indexOf(stop));
      break;
    }
  }
  section = section.split(/\r\n|[\n\r\v\f\x1c-\x1e\x85\u2028\u2029]/).join(" ");
  const out: string[] = [];
  for (const item of section.split(",")) {
    const cleaned = [...item]
      .filter((ch) => /\p{L}/u.test(ch) || " ()%.".includes(ch))
      .join("")
      .trim()
      .toLowerCase();
    if (cleaned.length > 2) out.push(cleaned);
  }
  return out;
}
