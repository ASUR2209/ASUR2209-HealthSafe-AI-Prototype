/* The Flask API, run in the browser. Used when the app is built without VITE_API_URL
   (e.g. GitHub Pages). Each route mirrors backend/app.py and returns the same JSON, so
   api.ts treats it exactly like a server response.

   Differences from the server, all forced by having no server:
   - Household accounts and scan history live in this browser's localStorage.
   - Alternatives come from the Open Food Facts v2 search API (the category pages the
     backend uses are often unavailable), falling back to the same local product list. */

import { loadModel, type SafetyModel } from "./model";
import { predictSafetyFull, pyRound, type UserProfile } from "./pipeline";
import { extractText, parseIngredients } from "./ocr";
import products from "./products.json";

type Res = { status: number; data: any };
const ok = (data: any): Res => ({ status: 200, data });
const fail = (status: number, data: any): Res => ({ status, data });

let model: Promise<SafetyModel> | null = null;
export const getModel = () => (model ??= loadModel(`${import.meta.env.BASE_URL}engine/model.json`));

const OFF = "https://world.openfoodfacts.org";
// Same 10 s limit as the backend's requests calls, so a slow Open Food Facts can't hang a scan.
const offFetch = (url: string) => fetch(url, { signal: AbortSignal.timeout(10_000) });

export async function localFetch(path: string, init?: RequestInit): Promise<Res> {
  const method = (init?.method ?? "GET").toUpperCase();
  const body = init?.body ? JSON.parse(String(init.body)) : null;
  const url = new URL(path, "http://local");
  const p = url.pathname;
  try {
    if (p === "/health") return ok({ status: "healthy" });
    if (p === "/scan" && method === "POST") return await scan(body);
    if (p === "/ocr/analyze" && method === "POST") return await ocrAnalyze(body);
    if (p === "/scan-barcode" && method === "POST") return await scanBarcode(body);
    if (p === "/recommend" && method === "POST") return await recommend(body);
    if (p.startsWith("/family/")) return await familyRoute(p, method, body, url.searchParams);
    return fail(404, { error: "Not found" });
  } catch (e: any) {
    return fail(500, { error: e?.message ?? String(e) });
  }
}

/* ── Scans ────────────────────────────────────────────────── */

async function scan(data: any): Promise<Res> {
  if (!data) return fail(400, { error: "No data sent" });
  if (!("ingredients" in data)) return fail(400, { error: "Missing ingredients" });
  if (!("user_profile" in data)) return fail(400, { error: "Missing user_profile" });
  const result = predictSafetyFull(await getModel(), data.ingredients, data.user_profile);
  saveScanIfMember(data, data.product_name || "Typed ingredients", data.ingredients, result, "text");
  return ok({
    status: "success",
    verdict: result.final_verdict,
    score: result.final_score,
    score_label: result.score_label,
    flagged_count: result.flagged_count,
    conflict_count: result.conflict_count,
    flagged_ingredients: result.flagged_ingredients,
    medication_conflicts: result.medication_conflicts,
    explanation: result.explanation,
    layer2_prediction: result.layer2_prediction,
    layer2_confidence: result.layer2_confidence,
    ml_score: result.ml_score,
    proportion_score: result.proportion_score,
  });
}

async function ocrAnalyze(data: any): Promise<Res> {
  let image: string | undefined = data?.image_base64;
  if (!image) return fail(400, { error: "No image provided" });
  if (!image.startsWith("data:")) image = `data:image/jpeg;base64,${image}`;
  const profile = { conditions: data.conditions ?? [], medications: data.medications ?? [] };
  if (!Array.isArray(profile.conditions)) return fail(400, { error: "conditions must be a list" });
  if (!Array.isArray(profile.medications)) return fail(400, { error: "medications must be a list" });

  const rawText = await extractText(image);
  const ingredients = parseIngredients(rawText);
  if (!ingredients.length)
    return fail(422, {
      error: "Could not extract ingredients from image",
      raw_text: rawText,
      tip: "Use a clear, well-lit image of the ingredient label.",
    });
  const text = ingredients.join(", ");
  const result = predictSafetyFull(await getModel(), text, profile);
  saveScanIfMember(data, "Label photo", text, result, "photo");
  return ok({ success: true, ocr: { ingredients_extracted: ingredients, ingredient_count: ingredients.length, raw_text: rawText }, analysis: result });
}

async function lookupBarcode(barcode: string) {
  let data: any;
  try {
    const res = await offFetch(`${OFF}/api/v0/product/${encodeURIComponent(barcode)}.json`);
    data = await res.json();
  } catch {
    return { success: false, error: "Request timed out — check internet connection" };
  }
  if (data.status !== 1) return { success: false, error: "Product not found in database", barcode };
  const product = data.product ?? {};
  const ingredients = (product.ingredients_text_en || product.ingredients_text || "").trim();
  if (!ingredients)
    return { success: false, error: "Product found but no ingredient data available", barcode, product_name: product.product_name ?? "Unknown" };
  const n = product.nutriments ?? {};
  return {
    success: true,
    barcode,
    product_name: product.product_name ?? "Unknown",
    brand: product.brands ?? "Unknown",
    category: product.categories ?? "",
    ingredients_text: ingredients,
    nutriscore: String(product.nutriscore_grade ?? "unknown").toUpperCase(),
    nutrition: {
      energy_kcal: n["energy-kcal_100g"] ?? null,
      sugar_100g: n.sugars_100g ?? null,
      sodium_100g: n.sodium_100g ?? null,
      fat_100g: n.fat_100g ?? null,
      saturated_fat_100g: n["saturated-fat_100g"] ?? null,
    },
  };
}

async function scanBarcode(data: any): Promise<Res> {
  if (!data || !("barcode" in data)) return fail(400, { error: "barcode is required" });
  if (!("user_profile" in data)) return fail(400, { error: "user_profile is required" });
  const product: any = await lookupBarcode(String(data.barcode));
  if (!product.success) return fail(404, { error: product.error, barcode: data.barcode, suggestion: "Try scanning the label image instead" });

  const result = predictSafetyFull(await getModel(), product.ingredients_text, data.user_profile);
  const { sugar_100g: sugar = 0, sodium_100g: sodium = 0, saturated_fat_100g: satFat = 0 } = product.nutrition;
  const warnings: string[] = [];
  if ((sugar ?? 0) > 22.5) warnings.push(`Very high sugar: ${sugar}g per 100g (WHO limit: 22.5g)`);
  if ((sodium ?? 0) > 0.6) warnings.push(`Very high sodium: ${sodium}g per 100g (WHO limit: 0.6g)`);
  if ((satFat ?? 0) > 5) warnings.push(`Very high saturated fat: ${satFat}g per 100g (WHO limit: 5g)`);
  saveScanIfMember(data, product.product_name, product.ingredients_text, result, "barcode");

  return ok({
    status: "success",
    source: "barcode",
    product_name: product.product_name,
    brand: product.brand,
    nutriscore: product.nutriscore,
    ingredients_text: product.ingredients_text,
    nutrition_per_100g: product.nutrition,
    nutrition_warnings: warnings,
    verdict: result.final_verdict,
    score: result.final_score,
    score_label: result.score_label,
    flagged_count: result.flagged_count,
    conflict_count: result.conflict_count,
    flagged_ingredients: result.flagged_ingredients,
    medication_conflicts: result.medication_conflicts,
    explanation: result.explanation,
    layer2_prediction: result.layer2_prediction,
    layer2_confidence: result.layer2_confidence,
    ml_score: result.ml_score,
    proportion_score: result.proportion_score,
  });
}

/* ── Alternatives (recommendation_engine.py) ───────────────── */

function categoryFor(ingredients: string, name = "") {
  const t = `${name} ${ingredients}`.toLowerCase();
  const has = (ws: string[]) => ws.some((w) => t.includes(w));
  if (has(["biscuit", "cookie", "cracker", "wafer"])) return "biscuits";
  if (has(["chips", "crisps", "namkeen", "snack"])) return "chips-and-crisps";
  if (has(["chocolate", "cocoa"])) return "chocolates";
  if (has(["bread", "toast", "roti"])) return "breads";
  if (has(["juice", "drink", "beverage", "cola", "soda"])) return "beverages";
  if (has(["milk", "dairy", "yogurt", "curd"])) return "dairy";
  if (has(["noodles", "pasta", "maggi"])) return "pastas";
  if (has(["cereal", "oats", "granola", "muesli"])) return "cereals";
  if (has(["sauce", "ketchup", "mayo", "dressing"])) return "sauces";
  if (has(["jam", "jelly", "spread", "butter"])) return "spreads";
  return "snacks";
}

const OFF_CATEGORY: Record<string, string> = { biscuits: "biscuits-and-cakes" };

// Open Food Facts allows ~10 searches a minute, so keep each category's results for the session.
const searchCache = new Map<string, any[]>();

async function searchAlternatives(category: string, max = 100): Promise<any[]> {
  const cached = searchCache.get(category);
  if (cached) return cached;
  let found: any[] = [];
  try {
    const q = new URLSearchParams({
      categories_tags: `en:${OFF_CATEGORY[category] ?? category}`,
      fields: "product_name,brands,ingredients_text,ingredients_text_en,nutriscore_grade,nutriments",
      page_size: String(max),
    });
    const res = await offFetch(`${OFF}/api/v2/search?${q}`);
    if (res.ok) {
      for (const p of (await res.json()).products ?? []) {
        const ing = (p.ingredients_text_en || p.ingredients_text || "").trim();
        if (ing.length < 10) continue;
        const ascii = [...ing].filter((c) => c.charCodeAt(0) < 128).length / ing.length;
        if (ascii >= 0.85) found.push(p);
      }
      if (found.length) searchCache.set(category, found.slice(0, max));
    }
  } catch {
    /* fall through to the local list, as the backend does */
  }
  if (!found.length)
    found = products
      .filter((p) => p.category === category)
      .map((p) => ({ product_name: p.product_name, brands: p.brand, ingredients_text: p.ingredients_text, nutriscore_grade: p.nutriscore, nutriments: {} }));
  return found.slice(0, max);
}

async function recommend(data: any): Promise<Res> {
  if (!data) return fail(400, { error: "No data sent" });
  if (!("ingredients_text" in data)) return fail(400, { error: "ingredients_text is required" });
  if (!("user_profile" in data)) return fail(400, { error: "user_profile is required" });
  const name: string = data.product_name ?? "";
  const category = data.category || categoryFor(data.ingredients_text, name);
  const candidates = await searchAlternatives(category);
  if (!candidates.length) return ok({ success: false, error: "No alternatives found in database", category, alternatives: [] });

  const m = await getModel();
  const scored: any[] = [];
  for (const p of candidates) {
    const ing = (p.ingredients_text_en || p.ingredients_text || "").trim();
    if (ing.length < 10) continue;
    let r;
    try {
      r = predictSafetyFull(m, ing, data.user_profile);
    } catch {
      continue;
    }
    const productName = p.product_name ?? "Unknown Product";
    if (productName.toLowerCase() === name.toLowerCase()) continue;
    const n = p.nutriments ?? {};
    scored.push({
      product_name: productName,
      brand: p.brands ?? "Unknown Brand",
      nutriscore: String(p.nutriscore_grade ?? "?").toUpperCase(),
      verdict: r.final_verdict,
      score: r.final_score,
      score_label: r.score_label,
      flagged_count: r.flagged_count,
      conflict_count: r.conflict_count,
      ingredients_text: ing,
      nutrition_per_100g: {
        sugar_100g: pyRound(n.sugars_100g || 0, 1),
        sodium_100g: pyRound(n.sodium_100g || 0, 3),
        saturated_fat_100g: pyRound(n["saturated-fat_100g"] || 0, 1),
      },
      safer_than_scanned: true,
      note: "Relatively safer option — consult your doctor before consuming",
    });
  }
  if (!scored.length) return ok({ success: false, error: `No alternatives found in ${category} category`, category, alternatives: [] });
  scored.sort((a, b) => b.score - a.score); // stable, like Python's sort
  return ok({
    success: true,
    category,
    total_candidates_checked: scored.length,
    disclaimer: "These are relatively safer options compared to the scanned product. Always consult your doctor.",
    alternatives: scored.slice(0, 3),
  });
}

/* ── Household (database.py), stored in localStorage ────────── */

interface DB {
  families: { id: string; head_name: string; email: string; password_hash: string; created_at: string }[];
  members: any[];
  scans: any[];
}
const KEY = "hs.localdb";
function readDb(): DB {
  try {
    const raw = localStorage.getItem(KEY);
    if (raw) return JSON.parse(raw);
  } catch {}
  return { families: [], members: [], scans: [] };
}
function writeDb(db: DB) {
  try {
    localStorage.setItem(KEY, JSON.stringify(db));
  } catch {
    throw new Error("This browser blocked local storage, so household data can't be saved.");
  }
}
const now = () => new Date().toISOString();
async function sha256(s: string) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s));
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
}
const memberOut = (m: any) => ({
  member_id: m.id,
  name: m.name,
  age: m.age,
  gender: m.gender,
  relationship: m.relationship,
  conditions: m.conditions,
  medications: m.medications,
  allergies: m.allergies,
  is_head: m.is_head,
});
const membersOf = (db: DB, familyId: string) =>
  db.members
    .filter((m) => m.family_id === familyId)
    .sort((a, b) => Number(b.is_head) - Number(a.is_head) || a.created_at.localeCompare(b.created_at))
    .map(memberOut);

function saveScanIfMember(data: any, productName: string, ingredients: string, r: ReturnType<typeof predictSafetyFull>, source: string) {
  if (!data?.family_id || !data?.member_id) return;
  try {
    const db = readDb();
    db.scans.push({
      id: crypto.randomUUID(),
      family_id: data.family_id,
      member_id: data.member_id,
      product_name: productName,
      ingredients_text: ingredients,
      verdict: r.final_verdict,
      score: r.final_score,
      score_label: r.score_label,
      flagged_count: r.flagged_count,
      conflict_count: r.conflict_count,
      flagged_ingredients: r.flagged_ingredients,
      source,
      scanned_at: now(),
    });
    writeDb(db);
  } catch (e) {
    console.warn("save_scan error:", e);
  }
}

async function familyRoute(path: string, method: string, data: any, query: URLSearchParams): Promise<Res> {
  const db = readDb();
  const parts = path.split("/").filter(Boolean); // ["family", ...]

  if (parts[1] === "register" && method === "POST") {
    if (!data) return fail(400, { error: "No data sent" });
    for (const f of ["head_name", "email", "password"]) if (!(f in data)) return fail(400, { error: `Missing ${f}` });
    if (db.families.some((f) => f.email === data.email)) return fail(400, { success: false, error: "Email already registered" });
    const id = crypto.randomUUID();
    const memberId = crypto.randomUUID();
    const t = now();
    db.families.push({ id, head_name: data.head_name, email: data.email, password_hash: await sha256(data.password), created_at: t });
    db.members.push({ id: memberId, family_id: id, name: data.head_name, age: null, gender: null, relationship: "Self", conditions: [], medications: [], allergies: [], is_head: true, created_at: t });
    writeDb(db);
    return ok({ success: true, family_id: id, member_id: memberId, message: `Family account created for ${data.head_name}` });
  }

  if (parts[1] === "login" && method === "POST") {
    if (!data?.email || !data?.password) return fail(400, { error: "Email and password required" });
    const hash = await sha256(data.password);
    const fam = db.families.find((f) => f.email === data.email && f.password_hash === hash);
    if (!fam) return fail(401, { success: false, error: "Invalid email or password" });
    return ok({ success: true, family_id: fam.id, head_name: fam.head_name, email: fam.email, members: membersOf(db, fam.id) });
  }

  const familyId = parts[1];
  const section = parts[2];
  const memberId = parts[3];

  if (section === "members" && !memberId && method === "GET") return ok({ family_id: familyId, members: membersOf(db, familyId) });

  if (section === "members" && !memberId && method === "POST") {
    if (!data?.name) return fail(400, { error: "name is required" });
    const id = crypto.randomUUID();
    db.members.push({
      id,
      family_id: familyId,
      name: data.name,
      age: data.age ?? null,
      gender: data.gender ?? null,
      relationship: data.relationship ?? "Family Member",
      conditions: data.conditions ?? [],
      medications: data.medications ?? [],
      allergies: data.allergies ?? [],
      is_head: false,
      created_at: now(),
    });
    writeDb(db);
    return ok({ success: true, member_id: id, message: `${data.name} added to family` });
  }

  if (section === "members" && memberId) {
    const m = db.members.find((x) => x.id === memberId && x.family_id === familyId);
    if (!m) return fail(400, { success: false, error: "Member not found" });
    if (method === "PUT") {
      if (!data) return fail(400, { error: "No data sent" });
      for (const k of ["name", "age", "gender", "relationship", "conditions", "medications", "allergies"]) if (k in data) m[k] = data[k];
      writeDb(db);
      return ok({ success: true, message: "Member updated" });
    }
    if (method === "DELETE") {
      if (m.is_head) return fail(400, { success: false, error: "Cannot delete head of family" });
      db.members = db.members.filter((x) => x !== m);
      writeDb(db);
      return ok({ success: true, message: "Member removed" });
    }
  }

  if (section === "dashboard" && method === "GET") {
    const members = membersOf(db, familyId).map((m) => {
      const scans = db.scans
        .filter((s) => s.family_id === familyId && s.member_id === m.member_id)
        .sort((a, b) => b.scanned_at.localeCompare(a.scanned_at))
        .slice(0, 10);
      const total = scans.length;
      return {
        member_id: m.member_id,
        name: m.name,
        relationship: m.relationship,
        age: m.age,
        conditions: m.conditions,
        is_head: m.is_head,
        stats: {
          total_scans: total,
          avg_safety_score: total ? pyRound(scans.reduce((a, s) => a + s.score, 0) / total) : null,
          unsafe_scans: scans.filter((s) => s.verdict === "Unsafe").length,
          last_scan: total ? scans[0].scanned_at : null,
        },
      };
    });
    const all = members.map((m) => m.stats.avg_safety_score).filter((s): s is number => s !== null);
    return ok({ family_id: familyId, family_score: all.length ? pyRound(all.reduce((a, b) => a + b, 0) / all.length) : null, members });
  }

  if (section === "history" && method === "GET") {
    const member = query.get("member_id");
    const limit = Number(query.get("limit") ?? 20);
    const names = new Map(db.members.map((m) => [m.id, m.name]));
    const history = db.scans
      .filter((s) => s.family_id === familyId && (!member || s.member_id === member) && (member || names.has(s.member_id)))
      .sort((a, b) => b.scanned_at.localeCompare(a.scanned_at))
      .slice(0, limit)
      .map((s) => ({ scan_id: s.id, ...s, ...(member ? {} : { member_name: names.get(s.member_id) }) }));
    return ok({ family_id: familyId, history });
  }

  return fail(404, { error: "Not found" });
}
