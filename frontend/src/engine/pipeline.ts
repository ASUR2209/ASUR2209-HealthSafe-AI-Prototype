/* Port of predict_safety_full() and helpers from backend/app.py.
   Field names and rounding match the Flask responses so the UI can't tell them apart. */

import rules from "./rules.json";
import type { SafetyModel } from "./model";

type Rule = { risk: string; conditions: string[]; reason: string };
const INGREDIENT_RULES = rules.INGREDIENT_RULES as Record<string, Rule>;
const MEDICATION_CONFLICTS = rules.MEDICATION_CONFLICTS as Record<string, Record<string, string>>;

/** Python's round(): half to even, on the exact binary value. */
export function pyRound(x: number, digits = 0): number {
  const m = 10 ** digits;
  const y = x * m;
  const r = Math.round(y);
  // Exact ties only: x*m is an exact .5 and the scaling introduced no error.
  if (Math.abs(y % 1) === 0.5 && y / m === x) return (r % 2 === 0 ? r : r - 1) / m;
  return digits === 0 ? r : Number(x.toFixed(digits));
}

const scoreLabel = (s: number) => (s >= 80 ? "Excellent" : s >= 65 ? "Good" : s >= 45 ? "Moderate" : s >= 25 ? "Poor" : "Dangerous");

// Python str.strip() / \s cover a few more characters than JS trim(); these are the ones that matter.
const pyStrip = (s: string) => s.replace(/^[\s\x1c-\x1f]+|[\s\x1c-\x1f]+$/g, "");

export function cleanIngredientText(text: string): string {
  let t = text.toLowerCase();
  t = t.replace(/\p{Nd}+\.?\p{Nd}*\s*%/gu, "");
  t = t.replace(/\(e\p{Nd}+\)/gu, "");
  t = t.replace(/[^\p{L}\p{N}_\s,]/gu, " ");
  t = t.replace(/-/g, " ").replace(/\//g, " ");
  return pyStrip(t.replace(/\s+/g, " "));
}

export interface Flag {
  ingredient: string;
  matched_keyword: string;
  position_in_list: number;
  risk: string;
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
export interface UserProfile {
  conditions?: unknown[];
  medications?: unknown[];
}

export function runLayer1(ingredientsText: string, profile: UserProfile) {
  const conditions = profile.conditions ?? [];
  const medications = profile.medications ?? [];
  if (!Array.isArray(conditions)) throw new Error("conditions must be a list");
  if (!Array.isArray(medications)) throw new Error("medications must be a list");
  const userConditions = conditions.map((c) => pyStrip(String(c)).toLowerCase()).filter(Boolean);
  const userMeds = medications.map((m) => pyStrip(String(m)).toLowerCase()).filter(Boolean);

  const cleaned = ingredientsText
    .split(/[,;]/)
    .filter((i) => pyStrip(i))
    .map(cleanIngredientText);

  const flagged: Flag[] = [];
  const seenFlags = new Set<string>();
  cleaned.forEach((ingredient, position) => {
    for (const [keyword, rule] of Object.entries(INGREDIENT_RULES)) {
      if (!ingredient.includes(keyword)) continue;
      const matching = rule.conditions.filter((c) => userConditions.includes(c));
      if (!matching.length) continue;
      const key = `${pyStrip(ingredient)}\u0000${keyword}\u0000${position}`;
      if (seenFlags.has(key)) continue;
      seenFlags.add(key);
      flagged.push({
        ingredient: pyStrip(ingredient),
        matched_keyword: keyword,
        position_in_list: position + 1,
        risk: rule.risk,
        harmful_for: matching,
        reason: rule.reason,
      });
    }
  });

  const conflicts: Conflict[] = [];
  const seenConflicts = new Set<string>();
  for (const medication of userMeds) {
    const table = MEDICATION_CONFLICTS[medication];
    if (!table) continue;
    for (const ingredient of cleaned) {
      for (const [keyword, msg] of Object.entries(table)) {
        if (!ingredient.includes(keyword)) continue;
        const message = String(msg);
        const m = /^\s*(HIGH|MEDIUM|LOW)\b/i.exec(message);
        let severity: string;
        let explanation: string;
        if (m) {
          severity = m[1].toUpperCase();
          explanation = pyStrip(pyStrip(message.slice(m[0].length)).replace(/^[^a-zA-Z0-9]+/, ""));
        } else {
          severity = "UNSPECIFIED";
          explanation = message;
        }
        const key = `${medication}\u0000${pyStrip(ingredient)}\u0000${keyword}`;
        if (seenConflicts.has(key)) continue;
        seenConflicts.add(key);
        conflicts.push({ medication, ingredient: pyStrip(ingredient), matched_keyword: keyword, severity, conflict: explanation });
      }
    }
  }

  const high = flagged.filter((f) => f.risk === "HIGH").length;
  const medium = flagged.filter((f) => f.risk === "MEDIUM").length;
  const highC = conflicts.filter((c) => c.severity === "HIGH").length;
  const mediumC = conflicts.filter((c) => c.severity === "MEDIUM").length;
  const overall = high || highC ? "HIGH" : medium || mediumC ? "MEDIUM" : "SAFE";
  return {
    flagged_ingredients: flagged,
    medication_conflicts: conflicts,
    overall_layer1_flag: overall,
    high_count: high,
    medium_count: medium,
    conflict_count: conflicts.length,
    high_conflict_count: highC,
    medium_conflict_count: mediumC,
  };
}

export function calculateProportionScore(ingredientsText: string, l1: ReturnType<typeof runLayer1>): [number, string] {
  const ingredients = ingredientsText
    .split(",")
    .map((i) => pyStrip(i).toLowerCase())
    .filter(Boolean);
  if (!ingredients.length) throw new Error("No valid ingredients were provided.");
  const riskScores: Record<string, number> = { HIGH: 15, MEDIUM: 45, LOW: 70 };
  const scores = ingredients.map((ing) => {
    const matched: number[] = [];
    for (const f of l1.flagged_ingredients) {
      const kw = pyStrip(String(f.matched_keyword ?? "")).toLowerCase();
      const risk = pyStrip(String(f.risk ?? "")).toUpperCase();
      if (kw && ing.includes(kw) && risk in riskScores) matched.push(riskScores[risk]);
    }
    return matched.length ? Math.min(...matched) : 90;
  });
  const final = pyRound(scores.reduce((a, b) => a + b, 0) / scores.length);
  return [final, scoreLabel(final)];
}

export function predictSafetyFull(model: SafetyModel, ingredientsText: string, profile: UserProfile) {
  if (typeof ingredientsText !== "string" || !pyStrip(ingredientsText)) throw new Error("ingredients_text must be a non-empty string");
  if (!profile || typeof profile !== "object" || Array.isArray(profile)) throw new Error("user_profile must be a JSON object");

  const l1 = runLayer1(ingredientsText, profile);

  let cleaned = ingredientsText.toLowerCase().replace(/[^a-zA-Z\s,]/g, " ");
  cleaned = pyStrip(cleaned.replace(/\s+/g, " "));

  const pUnsafe = model.probaUnsafe(cleaned);
  const predNum = pUnsafe > 0.5 ? 1 : 0;
  const predLabel = predNum === 1 ? "Unsafe" : "Safe";
  const confidence = (predNum === 1 ? pUnsafe : Math.fround(1 - pUnsafe)) * 100;

  const [propScore, propLabel] = calculateProportionScore(ingredientsText, l1);
  const mlScore = predLabel === "Safe" ? confidence : 100 - confidence;
  let hybrid = pyRound(0.5 * mlScore + 0.5 * propScore);

  let verdict: string;
  if (l1.overall_layer1_flag === "HIGH") {
    verdict = "Unsafe";
    hybrid = Math.min(hybrid, 20);
  } else if (l1.overall_layer1_flag === "MEDIUM") {
    if (predLabel === "Unsafe") {
      verdict = "Unsafe";
      hybrid = Math.min(hybrid, 44);
    } else {
      verdict = "Moderate";
      hybrid = Math.min(hybrid, 64);
    }
  } else {
    verdict = hybrid >= 65 ? "Safe" : hybrid >= 45 ? "Moderate" : "Unsafe";
  }
  hybrid = Math.max(0, Math.min(100, Math.trunc(hybrid)));

  const explanations = [
    ...l1.flagged_ingredients.map((f) => `${f.ingredient}: ${f.reason}`),
    ...l1.medication_conflicts.map((c) => `${c.medication} + ${c.ingredient}: ${c.conflict}`),
  ];

  return {
    final_verdict: verdict,
    final_score: hybrid,
    score_label: scoreLabel(hybrid),
    layer1_flag: l1.overall_layer1_flag,
    layer2_prediction: predLabel,
    layer2_confidence: pyRound(confidence, 1),
    explanation: explanations.length
      ? explanations.join(" ")
      : "No personalized ingredient or medication warnings were detected by the current rule engine.",
    flagged_count: l1.high_count + l1.medium_count,
    conflict_count: l1.conflict_count,
    high_conflict_count: l1.high_conflict_count,
    medium_conflict_count: l1.medium_conflict_count,
    flagged_ingredients: l1.flagged_ingredients,
    medication_conflicts: l1.medication_conflicts,
    ml_score: pyRound(mlScore, 1),
    proportion_score: propScore,
    proportion_score_label: propLabel,
    explanation_disclaimer:
      "Prototype assessment only. Ingredient and medication rules are not clinically validated and do not replace professional medical advice.",
  };
}

export type Analysis = ReturnType<typeof predictSafetyFull>;
