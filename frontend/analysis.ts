import type { AnalysisResult, FlaggedIngredient, MedicationConflict, UserProfile } from "../types";

const API_URL = "http://localhost:5000";

export async function analyseIngredients(
  ingredients: string,
  profile: UserProfile
): Promise<AnalysisResult> {

  const response = await fetch(`${API_URL}/scan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      ingredients: ingredients,
      user_profile: {
        name: profile.name,
        conditions: profile.conditions,
        medications: profile.medications,
      },
    }),
  });

  if (!response.ok) {
    throw new Error("API request failed");
  }

  const data = await response.json();

  // Map Flask API response → your frontend types
  const flagged: FlaggedIngredient[] = (data.flagged_ingredients || []).map(
    (f: any) => ({
      name: f.matched_keyword
        .split(" ")
        .map((w: string) => w.charAt(0).toUpperCase() + w.slice(1))
        .join(" "),
      reason: f.reason,
      condition: f.harmful_for?.[0] || "General",
      severity: f.risk === "HIGH" ? "high" : f.risk === "MEDIUM" ? "medium" : "low",
    })
  );

  const conflicts: MedicationConflict[] = (data.medication_conflicts || []).map(
    (c: any) => ({
      ingredient: c.ingredient,
      medication: c.medication,
      detail: c.conflict,
    })
  );

  let summary = data.explanation || "";
  if (data.verdict === "Safe") {
    summary = "This product appears safe for your health profile. No major concerns detected.";
  } else if (data.verdict === "Moderate") {
    summary = "This product contains some ingredients that may require attention given your health profile.";
  } else {
    summary = `This product contains ${data.flagged_count} ingredients that conflict with your health profile.${
      data.conflict_count > 0 ? ` Also found ${data.conflict_count} medication conflict(s).` : ""
    }`;
  }

  return {
    verdict: data.verdict as "Safe" | "Moderate" | "Unsafe",
    score: data.score,
    summary,
    flagged,
    conflicts,
  };
}
