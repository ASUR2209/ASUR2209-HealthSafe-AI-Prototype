# =============================================================================
# LAYER 1 — RULE-BASED SAFETY ENGINE
# HealthSafe AI — Personalized Food Safety System
# Patent: "An Intelligent Wearable-Integrated Mobile System for Personalized
#          Food Safety Analysis..."
#
# HOW IT WORKS:
#   1. You pass in a list of ingredients from OCR scan
#   2. You pass in the user's health profile (diseases, medications)
#   3. Layer 1 checks each ingredient against a curated rulebook
#   4. Returns per-ingredient verdicts + overall flag
#   5. These results then COMBINE with XGBoost (Layer 2) for final verdict
# =============================================================================

import re

# =============================================================================
# THE RULEBOOK — Ingredients mapped to conditions they harm
# Each entry:
#   "ingredient_keyword": {
#       "risk": "HIGH" / "MEDIUM",
#       "conditions": [list of health conditions this harms],
#       "reason": human-readable explanation,
#       "threshold_note": optional — at what amount it becomes dangerous
#   }
# =============================================================================

INGREDIENT_RULES = {

    # ── DIABETES / HIGH BLOOD SUGAR ──────────────────────────────────────────
    "sugar": {
        "risk": "HIGH",
        "conditions": ["diabetes", "prediabetes", "insulin_resistance", "pcos"],
        "reason": "Direct blood glucose spike. Diabetics must strictly limit added sugar.",
        "threshold_note": "Any amount listed in top 3 ingredients is critical"
    },
    "high fructose corn syrup": {
        "risk": "HIGH",
        "conditions": ["diabetes", "prediabetes", "obesity", "fatty_liver"],
        "reason": "Rapidly raises blood glucose. Linked to insulin resistance.",
    },
    "hfcs": {
        "risk": "HIGH",
        "conditions": ["diabetes", "prediabetes"],
        "reason": "Abbreviation for high fructose corn syrup — same risk.",
    },
    "glucose": {
        "risk": "HIGH",
        "conditions": ["diabetes", "prediabetes"],
        "reason": "Direct blood sugar raiser.",
    },
    "dextrose": {
        "risk": "HIGH",
        "conditions": ["diabetes", "prediabetes"],
        "reason": "Another name for glucose — immediate blood sugar impact.",
    },
    "maltose": {
        "risk": "HIGH",
        "conditions": ["diabetes"],
        "reason": "High glycemic index sugar.",
    },
    "fructose": {
        "risk": "MEDIUM",
        "conditions": ["diabetes", "fatty_liver"],
        "reason": "Processed by liver — excess leads to fatty liver and insulin resistance.",
    },
    "corn syrup": {
        "risk": "HIGH",
        "conditions": ["diabetes", "prediabetes"],
        "reason": "High glycemic — rapid blood sugar spike.",
    },
    "maltodextrin": {
        "risk": "HIGH",
        "conditions": ["diabetes"],
        "reason": "GI index of 85-105 — higher than table sugar. Hidden in many processed foods.",
    },
    "refined flour": {
        "risk": "MEDIUM",
        "conditions": ["diabetes", "prediabetes"],
        "reason": "Rapidly converts to glucose. Choose whole grain alternatives.",
    },
    "enriched flour": {
        "risk": "MEDIUM",
        "conditions": ["diabetes"],
        "reason": "Stripped of fibre — spikes blood sugar faster than whole wheat.",
    },
    "white rice": {
        "risk": "MEDIUM",
        "conditions": ["diabetes"],
        "reason": "High glycemic index — prefer brown rice or millets.",
    },

    # ── HYPERTENSION / HIGH BLOOD PRESSURE ───────────────────────────────────
    "sodium": {
        "risk": "HIGH",
        "conditions": ["hypertension", "kidney_disease", "heart_disease"],
        "reason": "Raises blood pressure. ICMR limit: <2g sodium/day for hypertension patients.",
        "threshold_note": "Dangerous if >600mg per 100g of product"
    },
    "salt": {
        "risk": "HIGH",
        "conditions": ["hypertension", "kidney_disease", "heart_disease"],
        "reason": "Primary source of dietary sodium. Must be restricted.",
    },
    "monosodium glutamate": {
        "risk": "HIGH",
        "conditions": ["hypertension"],
        "reason": "MSG adds significant sodium load.",
    },
    "msg": {
        "risk": "HIGH",
        "conditions": ["hypertension"],
        "reason": "Monosodium glutamate — high sodium content.",
    },
    "soy sauce": {
        "risk": "HIGH",
        "conditions": ["hypertension", "kidney_disease"],
        "reason": "Extremely high sodium — 900mg per tablespoon.",
    },
    "baking soda": {
        "risk": "MEDIUM",
        "conditions": ["hypertension"],
        "reason": "Sodium bicarbonate — adds to sodium intake.",
    },
    "sodium bicarbonate": {
        "risk": "MEDIUM",
        "conditions": ["hypertension"],
        "reason": "Hidden sodium source in processed foods.",
    },
    "sodium nitrate": {
        "risk": "HIGH",
        "conditions": ["hypertension", "heart_disease"],
        "reason": "Preservative with high sodium + linked to cardiovascular risk.",
    },
    "sodium benzoate": {
        "risk": "MEDIUM",
        "conditions": ["hypertension"],
        "reason": "Preservative — contributes to sodium load.",
    },
    "disodium": {
        "risk": "MEDIUM",
        "conditions": ["hypertension"],
        "reason": "Any disodium compound adds to sodium intake.",
    },

    # ── HEART DISEASE / CHOLESTEROL ───────────────────────────────────────────
    "palm oil": {
        "risk": "HIGH",
        "conditions": ["heart_disease", "high_cholesterol", "obesity"],
        "reason": "Very high in saturated fat — raises LDL cholesterol.",
    },
    "hydrogenated": {
        "risk": "HIGH",
        "conditions": ["heart_disease", "high_cholesterol", "diabetes"],
        "reason": "Trans fat — worst type of fat for heart health. Banned in many countries.",
    },
    "partially hydrogenated": {
        "risk": "HIGH",
        "conditions": ["heart_disease", "high_cholesterol"],
        "reason": "Main source of artificial trans fat. Strongly linked to heart attacks.",
    },
    "trans fat": {
        "risk": "HIGH",
        "conditions": ["heart_disease", "high_cholesterol", "diabetes"],
        "reason": "Raises LDL, lowers HDL — most harmful dietary fat.",
    },
    "lard": {
        "risk": "HIGH",
        "conditions": ["heart_disease", "high_cholesterol"],
        "reason": "Animal fat — very high saturated fat content.",
    },
    "shortening": {
        "risk": "HIGH",
        "conditions": ["heart_disease", "high_cholesterol"],
        "reason": "Often contains trans fats — avoid for heart conditions.",
    },
    "coconut oil": {
        "risk": "MEDIUM",
        "conditions": ["heart_disease", "high_cholesterol"],
        "reason": "Very high in saturated fat despite 'healthy' reputation.",
    },
    "butter": {
        "risk": "MEDIUM",
        "conditions": ["heart_disease", "high_cholesterol"],
        "reason": "High saturated fat — moderate restriction recommended.",
    },

    # ── KIDNEY DISEASE ────────────────────────────────────────────────────────
    "potassium chloride": {
        "risk": "HIGH",
        "conditions": ["kidney_disease"],
        "reason": "Damaged kidneys cannot remove excess potassium — can cause fatal arrhythmia.",
    },
    "phosphate": {
        "risk": "HIGH",
        "conditions": ["kidney_disease"],
        "reason": "Kidneys cannot filter phosphates properly — leads to bone disease.",
    },
    "dicalcium phosphate": {
        "risk": "HIGH",
        "conditions": ["kidney_disease"],
        "reason": "Phosphate additive — dangerous for CKD patients.",
    },
    "sodium phosphate": {
        "risk": "HIGH",
        "conditions": ["kidney_disease", "hypertension"],
        "reason": "Double risk — both phosphate and sodium load.",
    },
    "potassium": {
        "risk": "MEDIUM",
        "conditions": ["kidney_disease"],
        "reason": "High-potassium ingredients need careful monitoring with CKD.",
    },
    "oxalic acid": {
        "risk": "MEDIUM",
        "conditions": ["kidney_disease", "kidney_stones"],
        "reason": "Can form calcium oxalate kidney stones.",
    },

    # ── THYROID ───────────────────────────────────────────────────────────────
    "soy": {
        "risk": "MEDIUM",
        "conditions": ["hypothyroidism"],
        "reason": "Soy isoflavones can interfere with thyroid hormone absorption if taken near medication.",
    },
    "soybean": {
        "risk": "MEDIUM",
        "conditions": ["hypothyroidism"],
        "reason": "May block thyroid hormone absorption — avoid within 4 hours of medication.",
    },
    "soy lecithin": {
        "risk": "MEDIUM",
        "conditions": ["hypothyroidism"],
        "reason": "Soy-derived — small interference risk for hypothyroid patients on levothyroxine.",
    },
    "iodine": {
        "risk": "MEDIUM",
        "conditions": ["hyperthyroidism", "thyroid_disease"],
        "reason": "Excess iodine worsens hyperthyroidism. Hypothyroid patients may need it.",
    },

    # ── PCOS ──────────────────────────────────────────────────────────────────
    "white sugar": {
        "risk": "HIGH",
        "conditions": ["pcos"],
        "reason": "Worsens insulin resistance — key driver of PCOS symptoms.",
    },
    "refined carbohydrate": {
        "risk": "HIGH",
        "conditions": ["pcos"],
        "reason": "Spikes insulin — disrupts hormonal balance in PCOS.",
    },
    "artificial sweetener": {
        "risk": "MEDIUM",
        "conditions": ["pcos"],
        "reason": "May affect gut microbiome and insulin sensitivity.",
    },
    "aspartame": {
        "risk": "MEDIUM",
        "conditions": ["pcos"],
        "reason": "Artificial sweetener — may worsen insulin sensitivity.",
    },

    # ── ALLERGIES ─────────────────────────────────────────────────────────────
    "peanut": {
        "risk": "HIGH",
        "conditions": ["peanut_allergy"],
        "reason": "Severe anaphylaxis risk for peanut allergy sufferers.",
    },
    "groundnut": {
        "risk": "HIGH",
        "conditions": ["peanut_allergy"],
        "reason": "Another name for peanut — same severe allergy risk.",
    },
    "tree nut": {
        "risk": "HIGH",
        "conditions": ["tree_nut_allergy"],
        "reason": "Can trigger anaphylaxis in tree nut allergy.",
    },
    "almond": {
        "risk": "HIGH",
        "conditions": ["tree_nut_allergy"],
        "reason": "Tree nut — serious allergy risk.",
    },
    "cashew": {
        "risk": "HIGH",
        "conditions": ["tree_nut_allergy"],
        "reason": "Tree nut — serious allergy risk.",
    },
    "walnut": {
        "risk": "HIGH",
        "conditions": ["tree_nut_allergy"],
        "reason": "Tree nut — serious allergy risk.",
    },
    "milk": {
        "risk": "HIGH",
        "conditions": ["lactose_intolerance", "dairy_allergy"],
        "reason": "Contains lactose and dairy proteins — causes symptoms for intolerant users.",
    },
    "lactose": {
        "risk": "HIGH",
        "conditions": ["lactose_intolerance"],
        "reason": "Directly causes digestive issues in lactose intolerance.",
    },
    "whey": {
        "risk": "HIGH",
        "conditions": ["dairy_allergy", "lactose_intolerance"],
        "reason": "Dairy protein — triggers dairy allergy reactions.",
    },
    "casein": {
        "risk": "HIGH",
        "conditions": ["dairy_allergy"],
        "reason": "Dairy protein — main allergen in milk allergy.",
    },
    "gluten": {
        "risk": "HIGH",
        "conditions": ["celiac_disease", "gluten_intolerance"],
        "reason": "Triggers immune attack on small intestine in celiac disease.",
    },
    "wheat": {
        "risk": "HIGH",
        "conditions": ["celiac_disease", "gluten_intolerance", "wheat_allergy"],
        "reason": "Primary source of gluten — dangerous for celiac patients.",
    },
    "barley": {
        "risk": "HIGH",
        "conditions": ["celiac_disease"],
        "reason": "Contains gluten — must avoid with celiac disease.",
    },
    "rye": {
        "risk": "HIGH",
        "conditions": ["celiac_disease"],
        "reason": "Contains gluten — avoid with celiac disease.",
    },
    "egg": {
        "risk": "HIGH",
        "conditions": ["egg_allergy"],
        "reason": "Common allergen — can cause severe reactions.",
    },
    "shellfish": {
        "risk": "HIGH",
        "conditions": ["shellfish_allergy"],
        "reason": "Severe anaphylaxis risk.",
    },

    # ── LIVER DISEASE ─────────────────────────────────────────────────────────
    "alcohol": {
        "risk": "HIGH",
        "conditions": ["liver_disease", "fatty_liver", "cirrhosis"],
        "reason": "Directly toxic to liver cells — any amount worsens liver disease.",
    },
    "fructose": {
        "risk": "HIGH",
        "conditions": ["fatty_liver"],
        "reason": "Processed exclusively by liver — excess directly causes fatty liver.",
    },
    "artificial colour": {
        "risk": "MEDIUM",
        "conditions": ["liver_disease"],
        "reason": "Synthetic dyes processed by liver — added burden on impaired liver.",
    },

    # ── ASTHMA / RESPIRATORY ──────────────────────────────────────────────────
    "sulphite": {
        "risk": "HIGH",
        "conditions": ["asthma"],
        "reason": "Sulphites trigger asthma attacks in sensitive individuals.",
    },
    "sulfite": {
        "risk": "HIGH",
        "conditions": ["asthma"],
        "reason": "Preservative — known asthma trigger.",
    },
    "tartrazine": {
        "risk": "MEDIUM",
        "conditions": ["asthma"],
        "reason": "Yellow dye (E102) — can trigger asthma in aspirin-sensitive patients.",
    },
    "benzoate": {
        "risk": "MEDIUM",
        "conditions": ["asthma"],
        "reason": "Preservative — can worsen asthma symptoms.",
    },

    # ── GENERAL HARMFUL ADDITIVES ─────────────────────────────────────────────
    "artificial flavour": {
        "risk": "MEDIUM",
        "conditions": ["diabetes", "hypertension", "liver_disease", "pcos"],
        "reason": "Synthetic compounds — may contain hidden sodium, sugars, or allergens.",
    },
    "preservative": {
        "risk": "MEDIUM",
        "conditions": ["asthma", "liver_disease"],
        "reason": "Various preservatives can trigger reactions or burden the liver.",
    },
    "food colour": {
        "risk": "MEDIUM",
        "conditions": ["liver_disease"],
        "reason": "Synthetic dyes — additional metabolic burden.",
    },
    "bleached": {
        "risk": "MEDIUM",
        "conditions": ["celiac_disease", "asthma"],
        "reason": "Chemical bleaching leaves residues — may irritate sensitive systems.",
    },

    # ── CAFFEINE / STIMULANTS ─────────────────────────────────────────────────
    "caffeine": {
        "risk": "MEDIUM",
        "conditions": ["hypertension", "anxiety", "heart_arrhythmia", "pregnancy"],
        "reason": "Raises blood pressure and heart rate — restricted for cardiac patients.",
    },
    "taurine": {
        "risk": "MEDIUM",
        "conditions": ["heart_disease", "hypertension"],
        "reason": "Often paired with caffeine in energy drinks — combined cardiovascular stress.",
    },
    "guarana": {
        "risk": "MEDIUM",
        "conditions": ["hypertension", "heart_arrhythmia"],
        "reason": "Natural caffeine source — same risks as caffeine.",
    },
}


# =============================================================================
# MEDICATION — INGREDIENT CONFLICT DATABASE
# =============================================================================

MEDICATION_CONFLICTS = {
    "metformin": {
        "alcohol": "HIGH — alcohol + metformin can cause dangerous lactic acidosis",
        "contrast_dye": "HIGH — iodine contrast agents with metformin risk kidney failure",
    },
    "warfarin": {
        "vitamin k": "HIGH — vitamin K directly counteracts warfarin's blood-thinning effect",
        "grapefruit": "HIGH — grapefruit alters warfarin metabolism",
    },
    "levothyroxine": {
        "soy": "MEDIUM — soy can reduce levothyroxine absorption by up to 30%",
        "calcium": "MEDIUM — calcium binds levothyroxine — take medication 4 hours apart",
        "iron": "MEDIUM — iron supplements block levothyroxine absorption",
    },
    "statins": {
        "grapefruit": "HIGH — grapefruit dramatically increases statin blood levels — toxicity risk",
        "red yeast rice": "HIGH — contains natural statins — combined overdose risk",
    },
    "ace inhibitors": {
        "potassium": "HIGH — ACE inhibitors already raise potassium — high potassium foods risk heart arrhythmia",
        "potassium chloride": "HIGH — dangerous hyperkalaemia risk",
    },
    "ssri": {
        "alcohol": "HIGH — dangerous CNS depression, serotonin syndrome risk",
        "grapefruit": "MEDIUM — may increase SSRI blood levels unpredictably",
    },
    "aspirin": {
        "alcohol": "HIGH — increases gastrointestinal bleeding risk",
        "tartrazine": "MEDIUM — aspirin-sensitive patients often react to tartrazine",
    },
}


# =============================================================================
# THE ENGINE — Main function you call
# =============================================================================

def clean_ingredient_text(text):
    """Clean raw OCR ingredient text for matching."""
    text = text.lower()
    text = re.sub(r'\d+\.?\d*\s*%', '', text)   # remove percentages
    text = re.sub(r'\(e\d+\)', '', text)          # remove E-numbers like (E102)
    text = re.sub(r'[^\w\s,]', ' ', text)         # keep letters, spaces, commas
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def run_layer1(ingredients_text, user_profile):
    """
    Layer 1 Rule-Based Safety Engine.

    Parameters
    ----------
    ingredients_text : str
        Raw ingredient list from OCR scan.
        Example: "Sugar, Enriched Flour (Wheat), Palm Oil, Cocoa 8%, Salt"

    user_profile : dict
        User health profile.
        Example: {
            "conditions": ["diabetes", "hypertension"],
            "medications": ["metformin"],
            "name": "Ambar"   # optional, for display
        }

    Returns
    -------
    dict with:
        - flagged_ingredients: list of flagged items with detail
        - medication_conflicts: list of drug-food conflicts found
        - overall_layer1_flag: "HIGH" / "MEDIUM" / "SAFE"
        - summary: human-readable summary string
        - pass_to_layer2: bool (always True — Layer 2 always runs after)
    """

    # Parse inputs
    user_conditions = [c.lower() for c in user_profile.get("conditions", [])]
    user_medications = [m.lower() for m in user_profile.get("medications", [])]

    # Split ingredient list — ingredients separated by commas or semicolons
    raw_ingredients = re.split(r'[,;]', ingredients_text)
    cleaned_ingredients = [clean_ingredient_text(i) for i in raw_ingredients if i.strip()]

    flagged = []
    seen_flags = set()

    # ── CHECK EACH INGREDIENT AGAINST RULEBOOK ────────────────────────────────
    for position, ingredient in enumerate(cleaned_ingredients):
        for keyword, rule in INGREDIENT_RULES.items():
            if keyword in ingredient:
                # Does this rule apply to ANY of the user's conditions?
                matching_conditions = [
                    c for c in rule["conditions"] if c in user_conditions
                ]
                if matching_conditions:
                    flag_key = keyword + str(position)
                    if flag_key not in seen_flags:
                        seen_flags.add(flag_key)
                        flagged.append({
                            "ingredient": ingredient.strip(),
                            "matched_keyword": keyword,
                            "position_in_list": position + 1,   # 1-indexed for humans
                            "risk": rule["risk"],
                            "harmful_for": matching_conditions,
                            "reason": rule["reason"],
                            "threshold_note": rule.get("threshold_note", ""),
                            "position_penalty": "HIGH" if position < 3 else "NORMAL",
                        })

    # ── CHECK MEDICATION CONFLICTS ────────────────────────────────────────────
    med_conflicts = []
    for medication in user_medications:
        if medication in MEDICATION_CONFLICTS:
            conflicts = MEDICATION_CONFLICTS[medication]
            for ingredient in cleaned_ingredients:
                for conflict_keyword, conflict_msg in conflicts.items():
                    if conflict_keyword in ingredient:
                        med_conflicts.append({
                            "medication": medication,
                            "ingredient": ingredient.strip(),
                            "conflict": conflict_msg,
                        })

    # ── DETERMINE OVERALL LAYER 1 FLAG ───────────────────────────────────────
    high_flags = [f for f in flagged if f["risk"] == "HIGH"]
    medium_flags = [f for f in flagged if f["risk"] == "MEDIUM"]

    if high_flags or med_conflicts:
        overall_flag = "HIGH"
    elif medium_flags:
        overall_flag = "MEDIUM"
    else:
        overall_flag = "SAFE"

    # ── BUILD HUMAN-READABLE SUMMARY ─────────────────────────────────────────
    user_name = user_profile.get("name", "User")
    condition_str = ", ".join(user_conditions).upper() if user_conditions else "No conditions"

    summary_lines = [
        f"Layer 1 Result for {user_name} [{condition_str}]",
        f"Overall flag: {overall_flag}",
        f"Flagged ingredients: {len(flagged)}  |  Medication conflicts: {len(med_conflicts)}",
    ]

    if flagged:
        summary_lines.append("\nFlagged ingredients:")
        for f in flagged:
            pos_note = f" [Position #{f['position_in_list']} — HIGH QUANTITY]" if f["position_penalty"] == "HIGH" else f" [Position #{f['position_in_list']}]"
            summary_lines.append(
                f"  [{f['risk']}] '{f['matched_keyword']}' found in '{f['ingredient']}'{pos_note}"
                f"\n         Harmful for: {', '.join(f['harmful_for'])}"
                f"\n         Reason: {f['reason']}"
            )

    if med_conflicts:
        summary_lines.append("\nMedication conflicts:")
        for c in med_conflicts:
            summary_lines.append(
                f"  [CONFLICT] {c['ingredient']} + {c['medication']}: {c['conflict']}"
            )

    return {
        "flagged_ingredients": flagged,
        "medication_conflicts": med_conflicts,
        "overall_layer1_flag": overall_flag,
        "high_count": len(high_flags),
        "medium_count": len(medium_flags),
        "conflict_count": len(med_conflicts),
        "summary": "\n".join(summary_lines),
        "pass_to_layer2": True,   # always pass to XGBoost after Layer 1
    }


# =============================================================================
# COMBINING LAYER 1 + LAYER 2 — Final verdict function
# =============================================================================

def combine_layers(layer1_result, layer2_prediction, layer2_confidence):
    """
    Combine Layer 1 rule engine output with Layer 2 XGBoost prediction
    into a single final verdict.

    Parameters
    ----------
    layer1_result   : dict — output from run_layer1()
    layer2_prediction : str — 'Safe', 'Moderate', or 'Unsafe' from XGBoost
    layer2_confidence : float — confidence % from XGBoost (0-100)

    Returns
    -------
    dict with final_verdict, final_score, explanation
    """

    l1_flag = layer1_result["overall_layer1_flag"]
    conflicts = layer1_result["conflict_count"]

    # Rule: If Layer 1 finds HIGH risk or medication conflict,
    # override XGBoost even if it said "Safe"
    if l1_flag == "HIGH" or conflicts > 0:
        final_verdict = "Unsafe"
        override_reason = (
            "Layer 1 rule engine detected high-risk ingredients or "
            "medication conflicts for your specific health conditions."
        )
        final_score = min(20, int(100 - layer2_confidence))

    elif l1_flag == "MEDIUM":
        # Blend: if XGBoost also says Unsafe, trust that; else → Moderate
        if layer2_prediction == "Unsafe":
            final_verdict = "Unsafe"
            final_score = int(100 - layer2_confidence)
        else:
            final_verdict = "Moderate"
            final_score = 50
        override_reason = "Layer 1 found medium-risk ingredients — combined with XGBoost assessment."

    else:
        # Layer 1 found nothing → trust XGBoost fully
        final_verdict = layer2_prediction
        final_score = int(layer2_confidence) if layer2_prediction == "Safe" else int(100 - layer2_confidence)
        override_reason = "Layer 1 found no condition-specific risks — XGBoost verdict used."

    # Map verdict to label
    if final_score >= 80:
        score_label = "Excellent"
    elif final_score >= 65:
        score_label = "Good"
    elif final_score >= 45:
        score_label = "Moderate"
    elif final_score >= 25:
        score_label = "Poor"
    else:
        score_label = "Dangerous"

    return {
        "final_verdict": final_verdict,
        "final_score": final_score,
        "score_label": score_label,
        "layer1_flag": l1_flag,
        "layer2_prediction": layer2_prediction,
        "layer2_confidence": round(layer2_confidence, 1),
        "explanation": override_reason,
        "flagged_count": layer1_result["high_count"] + layer1_result["medium_count"],
        "conflict_count": layer1_result["conflict_count"],
    }


# =============================================================================
# DEMO — Run this to see it working
# =============================================================================

# if __name__ == "__main__":

#     print("=" * 65)
#     print("HEALTHSAFE AI — LAYER 1 RULE ENGINE DEMO")
#     print("=" * 65)

#     # ── TEST 1: Diabetic user scanning Oreo ──────────────────────────────────
#     print("\nTEST 1: Diabetic + Hypertension user scanning Oreo biscuits")
#     print("-" * 55)

#     user1 = {
#         "name": "Rajesh (58yr)",
#         "conditions": ["diabetes", "hypertension"],
#         "medications": ["metformin"],
#     }

#     oreo_ingredients = (
#         "Sugar, Enriched Flour (Wheat), Palm Oil, Cocoa, "
#         "High Fructose Corn Syrup, Leavening Agents (Baking Soda), "
#         "Salt, Soy Lecithin, Artificial Flavour"
#     )

#     result1 = run_layer1(oreo_ingredients, user1)
#     print(result1["summary"])

#     # Simulating Layer 2 XGBoost output (in real use, call pipeline2.predict())
#     l2_pred = "Unsafe"
#     l2_conf = 99.4
#     final1 = combine_layers(result1, l2_pred, l2_conf)
#     print(f"\nFINAL VERDICT: {final1['final_verdict']} | Score: {final1['final_score']}/100 ({final1['score_label']})")
#     print(f"Explanation: {final1['explanation']}")

#     # ── TEST 2: Healthy user scanning Almonds ─────────────────────────────────
#     print("\n\nTEST 2: Healthy user scanning Almonds")
#     print("-" * 55)

#     user2 = {
#         "name": "Priya (25yr)",
#         "conditions": [],
#         "medications": [],
#     }

#     almond_ingredients = "Almonds"

#     result2 = run_layer1(almond_ingredients, user2)
#     print(result2["summary"])
#     final2 = combine_layers(result2, "Safe", 62.2)
#     print(f"\nFINAL VERDICT: {final2['final_verdict']} | Score: {final2['final_score']}/100 ({final2['score_label']})")

#     # ── TEST 3: Hypothyroid user + levothyroxine medication conflict ──────────
#     print("\n\nTEST 3: Hypothyroid user on levothyroxine scanning soy protein bar")
#     print("-" * 55)

#     user3 = {
#         "name": "Meera (42yr)",
#         "conditions": ["hypothyroidism"],
#         "medications": ["levothyroxine"],
#     }

#     soy_bar_ingredients = (
#         "Soy Protein Isolate, Soybean Oil, Sugar, Calcium Carbonate, "
#         "Iron, Artificial Flavour, Soy Lecithin"
#     )

#     result3 = run_layer1(soy_bar_ingredients, user3)
#     print(result3["summary"])
#     final3 = combine_layers(result3, "Moderate", 58.0)
#     print(f"\nFINAL VERDICT: {final3['final_verdict']} | Score: {final3['final_score']}/100 ({final3['score_label']})")

#     print("\n" + "=" * 65)
#     print("All tests complete. Integrate run_layer1() before pipeline2.predict()")
#     print("=" * 65)
