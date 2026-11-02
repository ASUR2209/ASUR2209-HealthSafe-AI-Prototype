import { DEMO_MED_CONFLICTS, DEMO_RULES, fixText } from "./data";

const BASE: string = import.meta.env.VITE_API_URL ?? "/api";

export type Risk = "HIGH" | "MEDIUM" | "LOW";
export type Verdict = "Safe" | "Moderate" | "Unsafe";

export interface Profile {
  name: string;
  conditions: string[];
  medications: string[];
  memberId?: string;
}

export interface Flag {
  ingredient: string;
  matched_keyword: string;
  position_in_list: number;
  risk: Risk;
  harmful_for: string[];
  reason: string;
}

export interface Conflict {
  medication: string;
  ingredient: string;
  matched_keyword: string;
  severity: string;
  conflict: string;
}

export interface Product {
  name: string;
  brand?: string;
  nutriscore?: string;
  nutrition?: Record<string, number | null>;
  warnings: string[];
}

export interface Result {
  source: "text" | "photo" | "barcode";
  demo: boolean;
  verdict: Verdict;
  score: number;
  scoreLabel: string;
  ingredientsText: string;
  ingredients: string[];
  flagged: Flag[];
  conflicts: Conflict[];
  explanation: string;
  model?: { prediction: string; confidence: number; mlScore: number };
  heuristic?: number;
  product?: Product;
  ocrText?: string;
}

export interface Alternative {
  product_name: string;
  brand?: string;
  nutriscore?: string;
  verdict: Verdict;
  score: number;
  score_label: string;
  flagged_count: number;
}

export class ApiError extends Error {
  constructor(message: string, public offline = false, public tip?: string) {
    super(message);
  }
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(BASE + path, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    });
  } catch {
    throw new ApiError("Can't reach the HealthSafe API.", true);
  }
  // Vite's proxy answers 502/504 when Flask isn't running.
  if (res.status === 502 || res.status === 504) throw new ApiError("Can't reach the HealthSafe API.", true);
  const data = await res.json().catch(() => ({}));
  if (!res.ok || data.success === false) {
    throw new ApiError(fixText(data.error) || `Request failed (${res.status})`, false, data.tip ?? data.suggestion);
  }
  return data as T;
}

const post = <T,>(path: string, body: unknown) => call<T>(path, { method: "POST", body: JSON.stringify(body) });

export async function checkHealth(): Promise<boolean> {
  try {
    await call("/health");
    return true;
  } catch {
    return false;
  }
}

export const splitIngredients = (text: string) =>
  text
    .split(/[,;]/)
    .map((s) => s.trim())
    .filter(Boolean);

const userProfile = (p: Profile) => ({ name: p.name, conditions: p.conditions, medications: p.medications });

const cleanFlags = (flags: Flag[] = []) => flags.map((f) => ({ ...f, reason: fixText(f.reason) }));
const cleanConflicts = (cs: Conflict[] = []) => cs.map((c) => ({ ...c, conflict: fixText(c.conflict) }));

// Flat responses from /scan and /scan-barcode share these fields.
function fromFlat(d: any, source: Result["source"], ingredientsText: string): Result {
  return {
    source,
    demo: false,
    verdict: d.verdict,
    score: d.score,
    scoreLabel: d.score_label,
    ingredientsText,
    ingredients: splitIngredients(ingredientsText),
    flagged: cleanFlags(d.flagged_ingredients),
    conflicts: cleanConflicts(d.medication_conflicts),
    explanation: fixText(d.explanation),
    model:
      d.layer2_prediction != null
        ? { prediction: d.layer2_prediction, confidence: d.layer2_confidence, mlScore: d.ml_score }
        : undefined,
    heuristic: d.proportion_score ?? undefined,
  };
}

const memberRef = (profile: Profile, familyId?: string) =>
  familyId && profile.memberId ? { family_id: familyId, member_id: profile.memberId } : {};

export async function scanText(text: string, profile: Profile, familyId?: string): Promise<Result> {
  try {
    const d = await post<any>("/scan", { ingredients: text, user_profile: userProfile(profile), ...memberRef(profile, familyId) });
    return fromFlat(d, "text", text);
  } catch (e) {
    if (e instanceof ApiError && e.offline) return demoScan(text, profile);
    throw e;
  }
}

export async function scanPhoto(dataUrl: string, profile: Profile, familyId?: string): Promise<Result> {
  const d = await post<any>("/ocr/analyze", {
    image_base64: dataUrl,
    conditions: profile.conditions,
    medications: profile.medications,
    ...memberRef(profile, familyId),
  });
  const a = d.analysis;
  const text = (d.ocr.ingredients_extracted as string[]).join(", ");
  return {
    source: "photo",
    demo: false,
    verdict: a.final_verdict,
    score: a.final_score,
    scoreLabel: a.score_label,
    ingredientsText: text,
    ingredients: d.ocr.ingredients_extracted,
    flagged: cleanFlags(a.flagged_ingredients),
    conflicts: cleanConflicts(a.medication_conflicts),
    explanation: fixText(a.explanation),
    model: { prediction: a.layer2_prediction, confidence: a.layer2_confidence, mlScore: a.ml_score },
    heuristic: a.proportion_score,
    ocrText: d.ocr.raw_text,
  };
}

export async function scanBarcode(code: string, profile: Profile, familyId?: string): Promise<Result> {
  const d = await post<any>("/scan-barcode", {
    barcode: code,
    user_profile: userProfile(profile),
    family_id: familyId,
    member_id: profile.memberId,
  });
  return {
    ...fromFlat(d, "barcode", d.ingredients_text),
    product: {
      name: d.product_name,
      brand: d.brand,
      nutriscore: d.nutriscore,
      nutrition: d.nutrition_per_100g,
      warnings: d.nutrition_warnings ?? [],
    },
  };
}

export async function recommend(r: Result, profile: Profile) {
  return post<{ success?: boolean; category?: string; alternatives: Alternative[]; error?: string }>("/recommend", {
    product_name: r.product?.name ?? "",
    ingredients_text: r.ingredientsText,
    user_profile: userProfile(profile),
  });
}

/* ── Household ─────────────────────────────────────────────── */

export interface Member {
  member_id: string;
  name: string;
  age?: number | null;
  relationship?: string;
  conditions: string[];
  medications?: string[];
  is_head?: boolean;
  stats?: { total_scans: number; avg_safety_score: number | null; unsafe_scans: number; last_scan: string | null };
}

export const family = {
  register: (head_name: string, email: string, password: string) =>
    post<any>("/family/register", { head_name, email, password }),
  login: (email: string, password: string) => post<any>("/family/login", { email, password }),
  members: (id: string) => call<{ members: Member[] }>(`/family/${id}/members`),
  dashboard: (id: string) => call<{ family_score: number | null; members: Member[] }>(`/family/${id}/dashboard`),
  addMember: (id: string, m: Partial<Member>) => post<any>(`/family/${id}/members`, m),
  updateMember: (id: string, memberId: string, m: Partial<Member>) =>
    call<any>(`/family/${id}/members/${memberId}`, { method: "PUT", body: JSON.stringify(m) }),
  removeMember: (id: string, memberId: string) => call<any>(`/family/${id}/members/${memberId}`, { method: "DELETE" }),
};

/* ── Offline demo engine ───────────────────────────────────────
   Mirrors the shape of predict_safety_full with a reduced rule set so the
   interface can be explored without Flask. The model lane is absent. */

function demoScan(text: string, profile: Profile): Result {
  const ingredients = splitIngredients(text);
  const conds = profile.conditions;
  const flagged: Flag[] = [];
  ingredients.forEach((ing, i) => {
    const low = ing.toLowerCase().replace(/-/g, " ");
    for (const [kw, rule] of Object.entries(DEMO_RULES)) {
      const hit = rule.conditions.filter((c) => conds.includes(c));
      if (low.includes(kw) && hit.length)
        flagged.push({ ingredient: low, matched_keyword: kw, position_in_list: i + 1, risk: rule.risk, harmful_for: hit, reason: rule.reason });
    }
  });
  const conflicts: Conflict[] = [];
  for (const med of profile.medications) {
    for (const [kw, msg] of Object.entries(DEMO_MED_CONFLICTS[med] ?? {})) {
      const ing = ingredients.find((x) => x.toLowerCase().includes(kw));
      if (ing) {
        const [sev, ...rest] = msg.split(" — ");
        conflicts.push({ medication: med, ingredient: ing.toLowerCase(), matched_keyword: kw, severity: sev, conflict: rest.join(" — ") });
      }
    }
  }
  const perIng = ingredientRisks(ingredients, flagged).map((r) => (r === "HIGH" ? 15 : r === "MEDIUM" ? 45 : 90));
  const heuristic = Math.round(perIng.reduce((a, b) => a + b, 0) / Math.max(1, perIng.length));
  const anyHigh = flagged.some((f) => f.risk === "HIGH") || conflicts.some((c) => c.severity === "HIGH");
  const anyMed = flagged.some((f) => f.risk === "MEDIUM") || conflicts.some((c) => c.severity === "MEDIUM");
  let score = heuristic;
  let verdict: Verdict = score >= 65 ? "Safe" : score >= 45 ? "Moderate" : "Unsafe";
  if (anyHigh) (score = Math.min(score, 20)), (verdict = "Unsafe");
  else if (anyMed) (score = Math.min(score, 64)), (verdict = "Moderate");
  return {
    source: "text",
    demo: true,
    verdict,
    score,
    scoreLabel: labelFor(score),
    ingredientsText: text,
    ingredients,
    flagged,
    conflicts,
    explanation: "",
    heuristic,
  };
}

// Approximates clean_ingredient_text so raw label text matches backend keywords.
export const norm = (s: string) => s.toLowerCase().replace(/[-/]/g, " ").replace(/\s+/g, " ");

export const labelFor =(s: number) =>
  s >= 80 ? "Excellent" : s >= 65 ? "Good" : s >= 45 ? "Moderate" : s >= 25 ? "Poor" : "Dangerous";

// Same matching rule as calculate_proportion_score: worst flag whose keyword appears in the ingredient.
export function ingredientRisks(ingredients: string[], flagged: Flag[]): (Risk | null)[] {
  return ingredients.map((ing) => {
    const low = norm(ing);
    const hits = flagged.filter((f) => f.matched_keyword && low.includes(f.matched_keyword.toLowerCase()));
    if (hits.some((h) => h.risk === "HIGH")) return "HIGH";
    if (hits.some((h) => h.risk === "MEDIUM")) return "MEDIUM";
    if (hits.length) return "LOW";
    return null;
  });
}
