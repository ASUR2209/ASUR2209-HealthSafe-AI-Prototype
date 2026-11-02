# HealthSafe AI â€” Flask API
import pickle
import re
from flask import Flask, request, jsonify
from flask_cors import CORS
# Add this import at the top with your other imports
from ocr_engine import extract_text_from_image, parse_ingredients
import tempfile
import os
from barcode_lookup import lookup_barcode
from recommendation_engine import get_recommendations, get_category_from_ingredients
from local_product_db import get_local_alternatives
from database import (
    create_family, login_family, add_family_member,
    get_family_members, update_family_member, delete_family_member,
    save_scan, get_scan_history, get_family_dashboard
)

app = Flask(__name__)
CORS(app)

# â”€â”€ Load model â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("Loading model...")
MODEL_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "ml",
    "healthsafe_model_v6.pkl"
)

pipeline2 = pickle.load(open(MODEL_PATH, "rb"))
print("Model loaded!")

# â”€â”€ Paste Layer 1 functions directly here â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# (no exec, no import â€” just paste the functions)
INGREDIENT_RULES = {

    # â”€â”€ DIABETES / PREDIABETES / PCOS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    "sugar": {"risk": "HIGH", "conditions": ["diabetes", "prediabetes", "pcos"], "reason": "Direct blood glucose spike."},
    "invert sugar": {"risk": "HIGH", "conditions": ["diabetes", "prediabetes"], "reason": "Rapidly raises blood glucose."},
    "high fructose corn syrup": {"risk": "HIGH", "conditions": ["diabetes", "prediabetes"], "reason": "Rapidly raises blood glucose."},
    "corn syrup": {"risk": "HIGH", "conditions": ["diabetes", "prediabetes"], "reason": "High glycemic index."},
    "dextrose": {"risk": "HIGH", "conditions": ["diabetes", "prediabetes"], "reason": "Direct blood sugar raiser."},
    "maltodextrin": {"risk": "HIGH", "conditions": ["diabetes", "prediabetes"], "reason": "Higher GI than table sugar."},
    "glucose": {"risk": "HIGH", "conditions": ["diabetes", "prediabetes"], "reason": "Direct blood glucose spike."},
    "fructose": {"risk": "HIGH", "conditions": ["diabetes", "prediabetes", "fatty_liver"], "reason": "Processed by liver, raises triglycerides."},
    "sucrose": {"risk": "HIGH", "conditions": ["diabetes", "prediabetes"], "reason": "Table sugar â€” raises blood glucose."},
    "honey": {"risk": "HIGH", "conditions": ["diabetes", "prediabetes"], "reason": "High glycemic index despite being natural."},
    "jaggery": {"risk": "HIGH", "conditions": ["diabetes", "prediabetes"], "reason": "High sugar content despite being natural."},
    "maida": {"risk": "HIGH", "conditions": ["diabetes", "prediabetes", "pcos"], "reason": "Refined flour â€” very high glycemic index."},
    "refined wheat flour": {"risk": "HIGH", "conditions": ["diabetes", "prediabetes", "pcos"], "reason": "Refined flour spikes blood sugar fast."},
    "refined flour": {"risk": "HIGH", "conditions": ["diabetes", "prediabetes", "pcos"], "reason": "High GI â€” causes rapid glucose rise."},
    "enriched flour": {"risk": "MEDIUM", "conditions": ["diabetes"], "reason": "Spikes blood sugar fast."},
    "white rice": {"risk": "MEDIUM", "conditions": ["diabetes", "prediabetes"], "reason": "High glycemic index."},
    "condensed milk": {"risk": "HIGH", "conditions": ["diabetes", "prediabetes"], "reason": "Very high sugar content."},
    "chocolate": {"risk": "MEDIUM", "conditions": ["diabetes"], "reason": "High sugar content unless dark chocolate."},
    "caramel": {"risk": "HIGH", "conditions": ["diabetes", "prediabetes"], "reason": "Concentrated sugar."},
    "treacle": {"risk": "HIGH", "conditions": ["diabetes"], "reason": "High sugar content."},
    "molasses": {"risk": "HIGH", "conditions": ["diabetes"], "reason": "High sugar content."},

    # â”€â”€ HYPERTENSION / BLOOD PRESSURE â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    "salt": {"risk": "HIGH", "conditions": ["hypertension", "kidney_disease"], "reason": "Primary sodium source â€” raises blood pressure."},
    "sodium": {"risk": "HIGH", "conditions": ["hypertension", "kidney_disease"], "reason": "Raises blood pressure."},
    "msg": {"risk": "HIGH", "conditions": ["hypertension"], "reason": "High sodium content."},
    "monosodium glutamate": {"risk": "HIGH", "conditions": ["hypertension"], "reason": "High sodium â€” raises blood pressure."},
    "ajinomoto": {"risk": "HIGH", "conditions": ["hypertension"], "reason": "MSG â€” high sodium content."},
    "sodium benzoate": {"risk": "HIGH", "conditions": ["hypertension", "kidney_disease"], "reason": "Sodium-based preservative."},
    "sodium nitrate": {"risk": "HIGH", "conditions": ["hypertension", "heart_disease"], "reason": "Raises blood pressure, linked to heart disease."},
    "sodium nitrite": {"risk": "HIGH", "conditions": ["hypertension", "heart_disease"], "reason": "Processed meat preservative â€” cardiovascular risk."},
    "baking soda": {"risk": "MEDIUM", "conditions": ["hypertension", "kidney_disease"], "reason": "Contains sodium bicarbonate."},
    "sodium bicarbonate": {"risk": "MEDIUM", "conditions": ["hypertension", "kidney_disease"], "reason": "High sodium content."},
    "disodium": {"risk": "HIGH", "conditions": ["hypertension", "kidney_disease"], "reason": "Sodium-based additive."},
    "caffeine": {"risk": "MEDIUM", "conditions": ["hypertension", "heart_arrhythmia"], "reason": "Raises blood pressure temporarily."},
    "iodised salt": {"risk": "HIGH", "conditions": ["hypertension", "kidney_disease"], "reason": "Primary sodium source."},
    "rock salt": {"risk": "HIGH", "conditions": ["hypertension", "kidney_disease"], "reason": "High sodium content."},

    # â”€â”€ HEART DISEASE / HIGH CHOLESTEROL â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    "palm oil": {"risk": "HIGH", "conditions": ["heart_disease", "high_cholesterol"], "reason": "High saturated fat â€” raises LDL cholesterol."},
    "palmolein": {"risk": "HIGH", "conditions": ["heart_disease", "high_cholesterol"], "reason": "Palm oil derivative â€” high saturated fat."},
    "palm kernel": {"risk": "HIGH", "conditions": ["heart_disease", "high_cholesterol"], "reason": "Very high saturated fat content."},
    "fractionated fat": {"risk": "HIGH", "conditions": ["heart_disease", "high_cholesterol"], "reason": "Processed fat â€” high saturated fat content."},
    "fractionated palm": {"risk": "HIGH", "conditions": ["heart_disease", "high_cholesterol"], "reason": "Processed palm fat â€” raises LDL."},
    "vanaspati": {"risk": "HIGH", "conditions": ["heart_disease", "high_cholesterol"], "reason": "Partially hydrogenated vegetable fat â€” contains trans fats."},
    "hydrogenated": {"risk": "HIGH", "conditions": ["heart_disease", "high_cholesterol"], "reason": "Trans fat â€” significantly raises cardiovascular risk."},
    "partially hydrogenated": {"risk": "HIGH", "conditions": ["heart_disease"], "reason": "Artificial trans fat â€” worst for heart health."},
    "shortening": {"risk": "HIGH", "conditions": ["heart_disease", "high_cholesterol"], "reason": "High trans and saturated fat."},
    "lard": {"risk": "HIGH", "conditions": ["heart_disease", "high_cholesterol"], "reason": "Animal fat â€” high saturated fat."},
    "coconut oil": {"risk": "MEDIUM", "conditions": ["heart_disease", "high_cholesterol"], "reason": "High saturated fat â€” consume in moderation."},
    "cream": {"risk": "MEDIUM", "conditions": ["heart_disease", "high_cholesterol"], "reason": "High saturated fat content."},
    "butter": {"risk": "MEDIUM", "conditions": ["heart_disease", "high_cholesterol"], "reason": "High saturated fat and cholesterol."},
    "ghee": {"risk": "MEDIUM", "conditions": ["heart_disease", "high_cholesterol"], "reason": "High saturated fat â€” moderation needed."},
    "interesterified": {"risk": "HIGH", "conditions": ["heart_disease", "high_cholesterol"], "reason": "Processed fat linked to cardiovascular risk."},

    # â”€â”€ KIDNEY DISEASE â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    "potassium chloride": {"risk": "HIGH", "conditions": ["kidney_disease"], "reason": "Kidneys cannot remove excess potassium â€” dangerous buildup."},
    "potassium": {"risk": "HIGH", "conditions": ["kidney_disease"], "reason": "High potassium is dangerous for kidney patients."},
    "phosphate": {"risk": "HIGH", "conditions": ["kidney_disease"], "reason": "Kidneys cannot filter phosphates â€” bone disease risk."},
    "phosphoric acid": {"risk": "HIGH", "conditions": ["kidney_disease"], "reason": "High phosphorus â€” dangerous for kidney patients."},
    "calcium phosphate": {"risk": "HIGH", "conditions": ["kidney_disease"], "reason": "Phosphate additive â€” dangerous for kidney disease."},
    "sodium phosphate": {"risk": "HIGH", "conditions": ["kidney_disease", "hypertension"], "reason": "Phosphate + sodium â€” double risk for kidney patients."},
    "potassium sorbate": {"risk": "MEDIUM", "conditions": ["kidney_disease"], "reason": "Potassium-based preservative."},
    "oxalic acid": {"risk": "HIGH", "conditions": ["kidney_disease", "kidney_stones"], "reason": "Forms kidney stones â€” avoid completely."},

    # â”€â”€ THYROID DISORDERS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    "soy": {"risk": "MEDIUM", "conditions": ["hypothyroidism"], "reason": "Interferes with thyroid medication absorption."},
    "soybean": {"risk": "MEDIUM", "conditions": ["hypothyroidism"], "reason": "Blocks thyroid hormone absorption."},
    "soy lecithin": {"risk": "MEDIUM", "conditions": ["hypothyroidism"], "reason": "Soy-derived â€” thyroid absorption risk."},
    "soy protein": {"risk": "MEDIUM", "conditions": ["hypothyroidism"], "reason": "Soy compound â€” interferes with levothyroxine."},
    "tofu": {"risk": "MEDIUM", "conditions": ["hypothyroidism"], "reason": "Soy-based â€” blocks thyroid hormone absorption."},
    "iodine": {"risk": "HIGH", "conditions": ["hyperthyroidism"], "reason": "Excess iodine worsens hyperthyroidism."},
    "seaweed": {"risk": "HIGH", "conditions": ["hyperthyroidism", "hypothyroidism"], "reason": "Very high iodine content â€” disrupts thyroid function."},
    "kelp": {"risk": "HIGH", "conditions": ["hyperthyroidism", "hypothyroidism"], "reason": "Extremely high iodine â€” dangerous for thyroid patients."},
    "flaxseed": {"risk": "MEDIUM", "conditions": ["hypothyroidism"], "reason": "Goitrogenic â€” may reduce thyroid hormone production."},
    "millet": {"risk": "MEDIUM", "conditions": ["hypothyroidism"], "reason": "Goitrogenic compound â€” interferes with thyroid function."},

    # â”€â”€ LIVER DISEASE / FATTY LIVER â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    "alcohol": {"risk": "HIGH", "conditions": ["liver_disease", "fatty_liver"], "reason": "Directly toxic to liver cells."},
    "fructose": {"risk": "HIGH", "conditions": ["fatty_liver"], "reason": "Processed entirely by liver â€” worsens fatty liver."},
    "artificial colour": {"risk": "MEDIUM", "conditions": ["liver_disease"], "reason": "Synthetic dyes processed by liver."},
    "tartrazine": {"risk": "MEDIUM", "conditions": ["liver_disease"], "reason": "Synthetic dye â€” liver metabolised."},

    # â”€â”€ PCOS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    "artificial sweetener": {"risk": "MEDIUM", "conditions": ["pcos"], "reason": "May disrupt insulin sensitivity."},
    "aspartame": {"risk": "MEDIUM", "conditions": ["pcos"], "reason": "Artificial sweetener â€” insulin disruption risk."},
    "sucralose": {"risk": "MEDIUM", "conditions": ["pcos", "diabetes"], "reason": "May affect gut microbiome and insulin response."},
    "trans fat": {"risk": "HIGH", "conditions": ["pcos", "heart_disease"], "reason": "Worsens insulin resistance and inflammation."},
    "refined oil": {"risk": "MEDIUM", "conditions": ["pcos"], "reason": "Pro-inflammatory â€” worsens PCOS symptoms."},

    # â”€â”€ ALLERGIES â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    "peanut": {"risk": "HIGH", "conditions": ["peanut_allergy"], "reason": "Severe anaphylaxis risk."},
    "groundnut": {"risk": "HIGH", "conditions": ["peanut_allergy"], "reason": "Peanut â€” severe anaphylaxis risk."},
    "wheat": {"risk": "HIGH", "conditions": ["celiac_disease", "wheat_allergy"], "reason": "Contains gluten â€” triggers immune attack."},
    "gluten": {"risk": "HIGH", "conditions": ["celiac_disease"], "reason": "Triggers autoimmune response in celiac disease."},
    "barley": {"risk": "HIGH", "conditions": ["celiac_disease"], "reason": "Contains gluten."},
    "rye": {"risk": "HIGH", "conditions": ["celiac_disease"], "reason": "Contains gluten."},
    "oats": {"risk": "MEDIUM", "conditions": ["celiac_disease"], "reason": "Often cross-contaminated with gluten."},
    "milk": {"risk": "HIGH", "conditions": ["lactose_intolerance", "dairy_allergy"], "reason": "Contains lactose and dairy proteins."},
    "lactose": {"risk": "HIGH", "conditions": ["lactose_intolerance"], "reason": "Causes digestive issues â€” bloating and cramping."},
    "whey": {"risk": "HIGH", "conditions": ["dairy_allergy"], "reason": "Dairy protein â€” triggers allergic reaction."},
    "casein": {"risk": "HIGH", "conditions": ["dairy_allergy"], "reason": "Dairy protein â€” allergic reaction risk."},
    "egg": {"risk": "HIGH", "conditions": ["egg_allergy"], "reason": "Triggers allergic reaction in egg allergy."},
    "albumin": {"risk": "HIGH", "conditions": ["egg_allergy"], "reason": "Egg white protein â€” allergen."},
    "sesame": {"risk": "HIGH", "conditions": ["sesame_allergy"], "reason": "Triggers allergic reaction."},
    "til": {"risk": "HIGH", "conditions": ["sesame_allergy"], "reason": "Sesame seeds â€” allergen."},
    "tree nut": {"risk": "HIGH", "conditions": ["tree_nut_allergy"], "reason": "Severe allergic reaction risk."},
    "almond": {"risk": "HIGH", "conditions": ["tree_nut_allergy"], "reason": "Tree nut â€” anaphylaxis risk."},
    "cashew": {"risk": "HIGH", "conditions": ["tree_nut_allergy"], "reason": "Tree nut â€” anaphylaxis risk."},
    "walnut": {"risk": "HIGH", "conditions": ["tree_nut_allergy"], "reason": "Tree nut â€” anaphylaxis risk."},
    "pistachio": {"risk": "HIGH", "conditions": ["tree_nut_allergy"], "reason": "Tree nut â€” anaphylaxis risk."},
    "fish": {"risk": "HIGH", "conditions": ["fish_allergy"], "reason": "Triggers allergic reaction."},
    "shellfish": {"risk": "HIGH", "conditions": ["shellfish_allergy"], "reason": "Severe allergic reaction risk."},
    "shrimp": {"risk": "HIGH", "conditions": ["shellfish_allergy"], "reason": "Shellfish â€” anaphylaxis risk."},
    "prawn": {"risk": "HIGH", "conditions": ["shellfish_allergy"], "reason": "Shellfish â€” anaphylaxis risk."},
    "mustard": {"risk": "HIGH", "conditions": ["mustard_allergy"], "reason": "Triggers allergic reaction."},
    "sulphite": {"risk": "HIGH", "conditions": ["sulphite_sensitivity", "asthma"], "reason": "Triggers asthma attacks and allergic reactions."},
    "sulphur dioxide": {"risk": "HIGH", "conditions": ["sulphite_sensitivity", "asthma"], "reason": "Preservative â€” triggers asthma."},

    # â”€â”€ E-NUMBERS (common in Indian packaged foods) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    "e102": {"risk": "MEDIUM", "conditions": ["asthma", "hyperactivity"], "reason": "Tartrazine â€” artificial yellow dye, triggers asthma."},
    "e110": {"risk": "MEDIUM", "conditions": ["asthma", "hyperactivity"], "reason": "Sunset yellow â€” artificial dye, hyperactivity in children."},
    "e122": {"risk": "MEDIUM", "conditions": ["asthma", "hyperactivity"], "reason": "Carmoisine â€” artificial red dye."},
    "e124": {"risk": "MEDIUM", "conditions": ["asthma", "hyperactivity"], "reason": "Ponceau 4R â€” artificial red dye, asthma trigger."},
    "e129": {"risk": "MEDIUM", "conditions": ["asthma", "hyperactivity"], "reason": "Allura red â€” linked to hyperactivity in children."},
    "e211": {"risk": "MEDIUM", "conditions": ["asthma", "liver_disease"], "reason": "Sodium benzoate â€” preservative, asthma trigger."},
    "e220": {"risk": "HIGH", "conditions": ["asthma", "sulphite_sensitivity"], "reason": "Sulphur dioxide â€” strong asthma trigger."},
    "e250": {"risk": "HIGH", "conditions": ["hypertension", "heart_disease"], "reason": "Sodium nitrite â€” processed meat preservative, cardiovascular risk."},
    "e621": {"risk": "HIGH", "conditions": ["hypertension"], "reason": "MSG â€” raises blood pressure."},
    "e951": {"risk": "MEDIUM", "conditions": ["pcos", "diabetes"], "reason": "Aspartame â€” artificial sweetener, insulin disruption."},
    "e955": {"risk": "MEDIUM", "conditions": ["pcos", "diabetes"], "reason": "Sucralose â€” may affect insulin response."},

    # â”€â”€ ASTHMA â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    "tartrazine": {"risk": "HIGH", "conditions": ["asthma"], "reason": "Artificial yellow dye â€” known asthma trigger."},
    "benzoate": {"risk": "MEDIUM", "conditions": ["asthma"], "reason": "Preservative â€” triggers asthma in sensitive individuals."},
    "metabisulphite": {"risk": "HIGH", "conditions": ["asthma", "sulphite_sensitivity"], "reason": "Sulphite compound â€” strong asthma trigger."},
    "bisulphite": {"risk": "HIGH", "conditions": ["asthma", "sulphite_sensitivity"], "reason": "Sulphite preservative â€” asthma trigger."},

    # â”€â”€ URIC ACID / GOUT â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    "yeast extract": {"risk": "HIGH", "conditions": ["gout", "high_uric_acid"], "reason": "High purine content â€” raises uric acid levels."},
    "anchovies": {"risk": "HIGH", "conditions": ["gout", "high_uric_acid"], "reason": "High purine seafood â€” triggers gout attacks."},
    "sardine": {"risk": "HIGH", "conditions": ["gout", "high_uric_acid"], "reason": "High purine â€” raises uric acid."},
    "fructose": {"risk": "HIGH", "conditions": ["gout", "high_uric_acid"], "reason": "Fructose metabolism produces uric acid."},
}
MEDICATION_CONFLICTS = {

    # â”€â”€ DIABETES MEDICATIONS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    "metformin": {
        "alcohol": "HIGH â€” alcohol + metformin causes dangerous lactic acidosis",
        "sugar": "MEDIUM â€” directly counteracts blood glucose control",
        "refined flour": "MEDIUM â€” raises blood glucose, reduces metformin effectiveness",
        "maida": "MEDIUM â€” high GI flour counteracts metformin",
    },
    "glipizide": {
        "alcohol": "HIGH â€” severe hypoglycemia risk",
        "sugar": "HIGH â€” directly counteracts glipizide glucose control",
        "caffeine": "MEDIUM â€” caffeine raises blood glucose unpredictably",
    },
    "glimepiride": {
        "alcohol": "HIGH â€” dangerous hypoglycemia with sulfonylureas",
        "sugar": "HIGH â€” counteracts medication directly",
    },
    "glyburide": {
        "alcohol": "HIGH â€” severe hypoglycemia and flushing reaction",
        "sugar": "HIGH â€” counteracts glucose control",
    },
    "insulin": {
        "alcohol": "HIGH â€” alcohol causes dangerous hypoglycemia with insulin",
        "sugar": "HIGH â€” directly raises blood glucose, counteracts insulin",
        "glucose": "HIGH â€” directly raises blood glucose",
        "fructose": "MEDIUM â€” raises blood glucose unpredictably",
        "maida": "MEDIUM â€” high GI â€” unpredictable glucose spike",
    },
    "sitagliptin": {
        "sugar": "MEDIUM â€” counteracts blood glucose management",
        "refined flour": "MEDIUM â€” high GI reduces drug effectiveness",
    },
    "empagliflozin": {
        "sugar": "MEDIUM â€” counteracts SGLT2 inhibitor glucose control",
        "alcohol": "MEDIUM â€” dehydration and blood pressure drop risk",
    },
    "dapagliflozin": {
        "sugar": "MEDIUM â€” counteracts glucose control",
        "alcohol": "MEDIUM â€” dehydration risk with SGLT2 inhibitors",
    },

    # â”€â”€ BLOOD PRESSURE MEDICATIONS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    "lisinopril": {
        "potassium": "HIGH â€” ACE inhibitors + potassium causes dangerous hyperkalemia",
        "potassium chloride": "HIGH â€” dangerous potassium buildup",
        "salt substitute": "HIGH â€” most salt substitutes contain potassium chloride",
        "alcohol": "MEDIUM â€” excessive blood pressure drop",
    },
    "enalapril": {
        "potassium": "HIGH â€” hyperkalemia risk with ACE inhibitors",
        "potassium chloride": "HIGH â€” dangerous potassium accumulation",
        "alcohol": "MEDIUM â€” blood pressure drop risk",
    },
    "losartan": {
        "potassium": "HIGH â€” ARBs + potassium causes hyperkalemia",
        "potassium chloride": "HIGH â€” dangerous potassium buildup",
        "grapefruit": "MEDIUM â€” may alter losartan metabolism",
        "alcohol": "MEDIUM â€” enhanced blood pressure lowering effect",
    },
    "telmisartan": {
        "potassium": "HIGH â€” hyperkalemia risk",
        "alcohol": "MEDIUM â€” excessive blood pressure drop",
    },
    "amlodipine": {
        "grapefruit": "HIGH â€” grapefruit increases amlodipine levels dangerously",
        "alcohol": "MEDIUM â€” enhanced blood pressure lowering, dizziness",
    },
    "nifedipine": {
        "grapefruit": "HIGH â€” dramatically increases nifedipine blood levels",
        "alcohol": "MEDIUM â€” excessive blood pressure lowering",
    },
    "metoprolol": {
        "caffeine": "MEDIUM â€” caffeine counteracts beta blocker effectiveness",
        "alcohol": "MEDIUM â€” enhanced sedation and blood pressure drop",
    },
    "atenolol": {
        "caffeine": "MEDIUM â€” counteracts beta blocker heart rate control",
        "alcohol": "MEDIUM â€” blood pressure drop risk",
        "calcium": "MEDIUM â€” calcium reduces atenolol absorption",
    },
    "propranolol": {
        "caffeine": "MEDIUM â€” counteracts beta blocker",
        "alcohol": "HIGH â€” dangerous blood pressure and heart rate drop",
    },
    "hydrochlorothiazide": {
        "alcohol": "MEDIUM â€” excessive blood pressure lowering",
        "calcium": "MEDIUM â€” thiazides increase calcium absorption â€” risk of hypercalcemia",
        "sodium": "MEDIUM â€” high sodium counteracts diuretic effectiveness",
    },
    "furosemide": {
        "sodium": "MEDIUM â€” high sodium counteracts diuretic",
        "alcohol": "MEDIUM â€” dehydration and blood pressure drop",
        "potassium": "MEDIUM â€” furosemide depletes potassium â€” monitor levels",
    },

    # â”€â”€ CHOLESTEROL MEDICATIONS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    "statins": {
        "grapefruit": "HIGH â€” dramatically increases statin blood levels, toxicity risk",
        "red yeast rice": "HIGH â€” contains natural statin â€” dangerous combined dose",
        "alcohol": "MEDIUM â€” increases liver damage risk with statins",
    },
    "atorvastatin": {
        "grapefruit": "HIGH â€” dramatically raises atorvastatin blood levels",
        "alcohol": "MEDIUM â€” liver damage risk",
        "red yeast rice": "HIGH â€” dangerous statin overdose effect",
    },
    "rosuvastatin": {
        "alcohol": "MEDIUM â€” liver damage risk",
        "antacids": "MEDIUM â€” aluminium antacids reduce rosuvastatin absorption",
    },
    "simvastatin": {
        "grapefruit": "HIGH â€” grapefruit juice dramatically increases simvastatin levels",
        "alcohol": "MEDIUM â€” liver toxicity risk",
        "red yeast rice": "HIGH â€” dangerous combined statin effect",
    },

    # â”€â”€ THYROID MEDICATIONS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    "levothyroxine": {
        "soy": "HIGH â€” reduces levothyroxine absorption by up to 30%",
        "calcium": "HIGH â€” binds levothyroxine â€” take 4 hours apart",
        "iron": "HIGH â€” blocks levothyroxine absorption completely",
        "fibre": "MEDIUM â€” reduces absorption if taken together",
        "walnuts": "MEDIUM â€” inhibits levothyroxine absorption",
        "coffee": "MEDIUM â€” reduces absorption â€” take on empty stomach",
        "milk": "MEDIUM â€” calcium in milk reduces absorption",
    },
    "carbimazole": {
        "iodine": "HIGH â€” iodine worsens hyperthyroidism being treated",
        "seaweed": "HIGH â€” very high iodine content â€” dangerous with carbimazole",
    },

    # â”€â”€ BLOOD THINNERS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    "warfarin": {
        "vitamin k": "HIGH â€” vitamin K directly counteracts warfarin anticoagulation",
        "grapefruit": "HIGH â€” alters warfarin metabolism dangerously",
        "cranberry": "HIGH â€” significantly increases bleeding risk",
        "alcohol": "HIGH â€” increases bleeding risk severely",
        "fish oil": "MEDIUM â€” omega-3 has additional blood thinning effect",
        "garlic": "MEDIUM â€” natural blood thinner â€” enhances warfarin effect",
        "ginger": "MEDIUM â€” mild blood thinning â€” enhances warfarin",
    },
    "aspirin": {
        "alcohol": "HIGH â€” increases gastrointestinal bleeding risk severely",
        "fish oil": "MEDIUM â€” combined blood thinning effect â€” bleeding risk",
        "garlic": "MEDIUM â€” enhanced blood thinning",
    },
    "clopidogrel": {
        "alcohol": "HIGH â€” increased bleeding risk",
        "grapefruit": "MEDIUM â€” may reduce clopidogrel effectiveness",
        "fish oil": "MEDIUM â€” enhanced blood thinning effect",
    },

    # â”€â”€ ANTIBIOTICS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    "ciprofloxacin": {
        "calcium": "HIGH â€” calcium blocks ciprofloxacin absorption completely",
        "iron": "HIGH â€” iron blocks antibiotic absorption",
        "milk": "MEDIUM â€” dairy reduces antibiotic absorption",
        "caffeine": "HIGH â€” ciprofloxacin dramatically increases caffeine levels",
    },
    "amoxicillin": {
        "alcohol": "MEDIUM â€” reduces antibiotic effectiveness and increases side effects",
    },
    "azithromycin": {
        "alcohol": "MEDIUM â€” reduces effectiveness, increases liver stress",
        "antacids": "MEDIUM â€” aluminium antacids reduce azithromycin absorption",
    },
    "doxycycline": {
        "milk": "HIGH â€” dairy completely blocks doxycycline absorption",
        "calcium": "HIGH â€” calcium binds doxycycline â€” take 2 hours apart",
        "iron": "HIGH â€” iron blocks absorption",
        "alcohol": "MEDIUM â€” reduces effectiveness",
    },
    "metronidazole": {
        "alcohol": "HIGH â€” causes severe vomiting, flushing, rapid heartbeat",
    },

    # â”€â”€ ANTACIDS / GUT MEDICATIONS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    "omeprazole": {
        "alcohol": "MEDIUM â€” alcohol worsens acid reflux condition being treated",
        "caffeine": "MEDIUM â€” caffeine increases acid production",
        "iron": "MEDIUM â€” omeprazole reduces iron absorption",
    },
    "pantoprazole": {
        "alcohol": "MEDIUM â€” worsens acid reflux",
        "caffeine": "MEDIUM â€” increases acid production",
    },
    "ranitidine": {
        "alcohol": "MEDIUM â€” increases alcohol blood levels dangerously",
        "caffeine": "MEDIUM â€” worsens acid condition",
    },

    # â”€â”€ MENTAL HEALTH MEDICATIONS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    "sertraline": {
        "alcohol": "HIGH â€” dangerous CNS depression, increased suicidal risk",
        "caffeine": "MEDIUM â€” increased anxiety and jitteriness",
        "grapefruit": "MEDIUM â€” may increase sertraline blood levels",
    },
    "fluoxetine": {
        "alcohol": "HIGH â€” dangerous CNS depression",
        "caffeine": "MEDIUM â€” worsens anxiety side effects",
        "grapefruit": "MEDIUM â€” increases fluoxetine levels",
    },
    "alprazolam": {
        "alcohol": "HIGH â€” fatal respiratory depression risk",
        "caffeine": "MEDIUM â€” counteracts anti-anxiety effect",
        "grapefruit": "HIGH â€” dramatically increases alprazolam blood levels",
    },

    # â”€â”€ PAIN MEDICATIONS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    "ibuprofen": {
        "alcohol": "HIGH â€” severe gastrointestinal bleeding risk",
        "caffeine": "MEDIUM â€” caffeine enhances ibuprofen effect â€” monitor dose",
    },
    "paracetamol": {
        "alcohol": "HIGH â€” alcohol + paracetamol causes severe liver damage",
    },
    "diclofenac": {
        "alcohol": "HIGH â€” gastrointestinal bleeding risk",
        "sodium": "MEDIUM â€” high sodium worsens fluid retention side effect",
    },
}
import re as _re

def clean_ingredient_text(text):
    text = text.lower()
    text = _re.sub(r'\d+\.?\d*\s*%', '', text)
    text = _re.sub(r'\(e\d+\)', '', text)
    text = _re.sub(r'[^\w\s,]', ' ', text)
    text = re.sub(r'-', ' ', text)          # ADD THIS â€” converts high-fructose â†’ high fructose
    text = re.sub(r'/', ' ', text)          # ADD THIS â€” converts palm/canola â†’ palm canola
    text = _re.sub(r'\s+', ' ', text).strip()
    return text

def run_layer1(ingredients_text, user_profile):
    """
    Personalized ingredient and medication warning engine.
    Medication severity is read from the existing rule message.
    These are prototype warnings, not clinically validated interactions.
    """

    if not isinstance(user_profile, dict):
        raise ValueError("user_profile must be a dictionary")

    conditions = user_profile.get("conditions", [])
    medications = user_profile.get("medications", [])

    if not isinstance(conditions, list):
        raise ValueError("conditions must be a list")

    if not isinstance(medications, list):
        raise ValueError("medications must be a list")

    user_conditions = [
        str(c).strip().lower() for c in conditions if str(c).strip()
    ]
    user_medications = [
        str(m).strip().lower() for m in medications if str(m).strip()
    ]

    raw_ingredients = _re.split(r'[,;]', ingredients_text)
    cleaned_ingredients = [
        clean_ingredient_text(i)
        for i in raw_ingredients if i.strip()
    ]

    flagged = []
    seen_flags = set()

    for position, ingredient in enumerate(cleaned_ingredients):
        for keyword, rule in INGREDIENT_RULES.items():
            if keyword in ingredient:
                matching_conditions = [
                    c for c in rule["conditions"] if c in user_conditions
                ]

                if matching_conditions:
                    flag_key = (ingredient.strip(), keyword, position)

                    if flag_key not in seen_flags:
                        seen_flags.add(flag_key)
                        flagged.append({
                            "ingredient": ingredient.strip(),
                            "matched_keyword": keyword,
                            "position_in_list": position + 1,
                            "risk": rule["risk"],
                            "harmful_for": matching_conditions,
                            "reason": rule["reason"],
                        })

    med_conflicts = []
    seen_conflicts = set()

    for medication in user_medications:
        if medication not in MEDICATION_CONFLICTS:
            continue

        conflicts = MEDICATION_CONFLICTS[medication]

        for ingredient in cleaned_ingredients:
            for conflict_keyword, conflict_msg in conflicts.items():
                if conflict_keyword in ingredient:
                    message = str(conflict_msg)
                    match = _re.match(
                        r'^\s*(HIGH|MEDIUM|LOW)\b',
                        message,
                        flags=_re.IGNORECASE
                    )

                    if match:
                        severity = match.group(1).upper()
                        explanation = message[match.end():].strip()
                        explanation = _re.sub(
                            r'^[^a-zA-Z0-9]+', '', explanation
                        ).strip()
                    else:
                        severity = "UNSPECIFIED"
                        explanation = message

                    conflict_key = (
                        medication, ingredient.strip(), conflict_keyword
                    )

                    if conflict_key not in seen_conflicts:
                        seen_conflicts.add(conflict_key)
                        med_conflicts.append({
                            "medication": medication,
                            "ingredient": ingredient.strip(),
                            "matched_keyword": conflict_keyword,
                            "severity": severity,
                            "conflict": explanation,
                        })

    high_flags = [f for f in flagged if f["risk"] == "HIGH"]
    medium_flags = [f for f in flagged if f["risk"] == "MEDIUM"]

    high_conflicts = [
        c for c in med_conflicts if c["severity"] == "HIGH"
    ]
    medium_conflicts = [
        c for c in med_conflicts if c["severity"] == "MEDIUM"
    ]

    if high_flags or high_conflicts:
        overall_flag = "HIGH"
    elif medium_flags or medium_conflicts:
        overall_flag = "MEDIUM"
    else:
        overall_flag = "SAFE"

    return {
        "flagged_ingredients": flagged,
        "medication_conflicts": med_conflicts,
        "overall_layer1_flag": overall_flag,
        "high_count": len(high_flags),
        "medium_count": len(medium_flags),
        "conflict_count": len(med_conflicts),
        "high_conflict_count": len(high_conflicts),
        "medium_conflict_count": len(medium_conflicts),
        "pass_to_layer2": True,
    }

def combine_layers(layer1_result, layer2_prediction, layer2_confidence):
    l1_flag = layer1_result["overall_layer1_flag"]

    if l1_flag == "HIGH":
        final_verdict = "Unsafe"
        final_score = min(20, int(100 - layer2_confidence))
        override_reason = (
            "Personalized assessment detected HIGH-risk ingredient "
            "or medication warnings."
        )

    elif l1_flag == "MEDIUM":
        final_verdict = (
            "Unsafe" if layer2_prediction == "Unsafe" else "Moderate"
        )
        final_score = 50
        override_reason = (
            "Personalized assessment detected MEDIUM-risk warnings."
        )

    else:
        final_verdict = layer2_prediction
        final_score = (
            int(layer2_confidence)
            if layer2_prediction == "Safe"
            else int(100 - layer2_confidence)
        )
        override_reason = "No condition-specific risks were detected."

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
        "flagged_count": (
            layer1_result["high_count"]
            + layer1_result["medium_count"]
        ),
        "conflict_count": layer1_result["conflict_count"],
        "high_conflict_count": layer1_result["high_conflict_count"],
        "medium_conflict_count": layer1_result["medium_conflict_count"],
        "flagged_ingredients": layer1_result["flagged_ingredients"],
        "medication_conflicts": layer1_result["medication_conflicts"],
    }

def calculate_proportion_score(ingredients_text, layer1_result):
    """
    Estimate ingredient risk using Layer 1 ingredient flags.

    This is a heuristic, not a measured nutritional or clinical score.
    Ingredient quantities are not available, so ingredient order is
    not treated as a proxy for concentration.
    """

    if not isinstance(ingredients_text, str):
        raise ValueError("ingredients_text must be a string")

    if not isinstance(layer1_result, dict):
        raise ValueError("layer1_result must be a dictionary")

    ingredients = [
        item.strip().lower()
        for item in ingredients_text.split(",")
        if item.strip()
    ]

    if not ingredients:
        raise ValueError("No valid ingredients were provided.")

    flagged_ingredients = layer1_result.get(
        "flagged_ingredients", []
    )

    if not isinstance(flagged_ingredients, list):
        raise ValueError("flagged_ingredients must be a list")

    risk_scores = {
        "HIGH": 15,
        "MEDIUM": 45,
        "LOW": 70
    }

    ingredient_scores = []

    for ingredient in ingredients:
        matched_risks = []

        for flag in flagged_ingredients:
            if not isinstance(flag, dict):
                continue

            keyword = str(
                flag.get("matched_keyword", "")
            ).strip().lower()

            risk = str(
                flag.get("risk", "")
            ).strip().upper()

            if keyword and keyword in ingredient:
                if risk in risk_scores:
                    matched_risks.append(risk_scores[risk])

        if matched_risks:
            ingredient_score = min(matched_risks)
        else:
            ingredient_score = 90

        ingredient_scores.append(ingredient_score)

    final_score = round(
        sum(ingredient_scores) / len(ingredient_scores)
    )

    if final_score >= 80:
        label = "Excellent"
    elif final_score >= 65:
        label = "Good"
    elif final_score >= 45:
        label = "Moderate"
    elif final_score >= 25:
        label = "Poor"
    else:
        label = "Dangerous"

    return final_score, label

def predict_safety_full(ingredients_text, user_profile):
    """
    Hybrid prediction using personalized rules, XGBoost,
    and the current ingredient assessment heuristic.
    """

    if not isinstance(ingredients_text, str) or not ingredients_text.strip():
        raise ValueError("ingredients_text must be a non-empty string")

    if not isinstance(user_profile, dict):
        raise ValueError("user_profile must be a JSON object")

    # Layer 1: Personalized rule engine
    l1 = run_layer1(ingredients_text, user_profile)

    # Clean ingredient text
    cleaned = ingredients_text.lower()
    cleaned = _re.sub(r'[^a-zA-Z\s,]', ' ', cleaned)
    cleaned = _re.sub(r'\s+', ' ', cleaned).strip()

    # Layer 2: XGBoost prediction
    label_map = {0: "Safe", 1: "Unsafe"}

    pred_num = int(pipeline2.predict([cleaned])[0])

    if pred_num not in label_map:
        raise ValueError(f"Unexpected model prediction: {pred_num}")

    pred_label = label_map[pred_num]

    probabilities = pipeline2.predict_proba([cleaned])[0]
    class_index = list(pipeline2.classes_).index(pred_num)
    confidence = float(probabilities[class_index]) * 100

    # Layer 3: Ingredient assessment heuristic
    prop_score, prop_label = calculate_proportion_score(
        ingredients_text, l1
    )

    # Convert ML output into a safety-oriented score
    ml_score = confidence if pred_label == "Safe" else 100 - confidence

    # 50:50 hybrid score
    hybrid_score = round(
        (0.50 * ml_score) + (0.50 * prop_score)
    )

    # Combine the ML prediction and personalized assessment
    final = combine_layers(l1, pred_label, confidence)

    # Apply severity-aware personalized overrides
    if l1["overall_layer1_flag"] == "HIGH":
        final_verdict = "Unsafe"
        hybrid_score = min(hybrid_score, 20)

    elif l1["overall_layer1_flag"] == "MEDIUM":
        if pred_label == "Unsafe":
            final_verdict = "Unsafe"
            hybrid_score = min(hybrid_score, 44)
        else:
            final_verdict = "Moderate"
            hybrid_score = min(hybrid_score, 64)

    else:
        if hybrid_score >= 65:
            final_verdict = "Safe"
        elif hybrid_score >= 45:
            final_verdict = "Moderate"
        else:
            final_verdict = "Unsafe"

    hybrid_score = max(0, min(100, int(hybrid_score)))

    # Score label
    if hybrid_score >= 80:
        score_label = "Excellent"
    elif hybrid_score >= 65:
        score_label = "Good"
    elif hybrid_score >= 45:
        score_label = "Moderate"
    elif hybrid_score >= 25:
        score_label = "Poor"
    else:
        score_label = "Dangerous"

    # Update response while preserving existing fields
    final["final_verdict"] = final_verdict
    final["final_score"] = hybrid_score
    final["score_label"] = score_label
    final["ml_score"] = round(ml_score, 1)
    final["proportion_score"] = prop_score
    final["proportion_score_label"] = prop_label
    final["layer2_confidence"] = round(confidence, 1)

    # Preserve detailed ingredient and medication information
    explanations = []

    for flag in l1["flagged_ingredients"]:
        explanations.append(
            f'{flag["ingredient"]}: {flag["reason"]}'
        )

    for conflict in l1["medication_conflicts"]:
        explanations.append(
            f'{conflict["medication"]} + {conflict["ingredient"]}: '
            f'{conflict["conflict"]}'
        )

    final["explanation"] = (
        " ".join(explanations)
        if explanations
        else "No personalized ingredient or medication warnings were "
             "detected by the current rule engine."
    )

    final["explanation_disclaimer"] = (
        "Prototype assessment only. Ingredient and medication rules "
        "are not clinically validated and do not replace professional "
        "medical advice."
    )

    return final

def save_scan_if_member(data, product_name, ingredients_text, result, source):
    """Save a scan to history when the request names a family member."""
    family_id = data.get('family_id')
    member_id = data.get('member_id')
    if not (family_id and member_id):
        return
    try:
        save_scan(
            family_id=family_id,
            member_id=member_id,
            product_name=product_name,
            ingredients_text=ingredients_text,
            verdict=result['final_verdict'],
            score=result['final_score'],
            score_label=result['score_label'],
            flagged_count=result['flagged_count'],
            conflict_count=result['conflict_count'],
            flagged_ingredients=result['flagged_ingredients'],
            source=source
        )
    except Exception as save_err:
        print(f"save_scan error: {save_err}")


@app.route('/')
def home():
    return jsonify({"status": "running", "message": "HealthSafe AI API is live!", "version": "1.0"})


@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy"})


@app.route('/scan', methods=['POST'])
def scan():
    """Original route â€” accepts typed ingredients text + user_profile as JSON."""
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No data sent"}), 400
        if 'ingredients' not in data:
            return jsonify({"error": "Missing ingredients"}), 400
        if 'user_profile' not in data:
            return jsonify({"error": "Missing user_profile"}), 400

        result = predict_safety_full(data['ingredients'], data['user_profile'])
        save_scan_if_member(data, data.get('product_name') or 'Typed ingredients', data['ingredients'], result, 'text')
        return jsonify({
            "status": "success",
            "verdict": result['final_verdict'],
            "score": result['final_score'],
            "score_label": result['score_label'],
            "flagged_count": result['flagged_count'],
            "conflict_count": result['conflict_count'],
            "flagged_ingredients": result['flagged_ingredients'],
            "medication_conflicts": result['medication_conflicts'],
            "explanation": result['explanation'],
            "layer2_prediction": result['layer2_prediction'],
            "layer2_confidence": result['layer2_confidence'],
            "ml_score": result['ml_score'],
            "proportion_score": result['proportion_score']
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/scan-image', methods=['POST'])
def scan_image():
    """New route â€” accepts image upload + user_profile, runs OCR then full analysis."""
    try:
        if 'image' not in request.files:
            return jsonify({"error": "No image file provided"}), 400

        user_profile_raw = request.form.get('user_profile')
        if not user_profile_raw:
            return jsonify({"error": "Missing user_profile"}), 400

        import json, tempfile, os
        user_profile = json.loads(user_profile_raw)

        # Save image to temp file and run OCR
        image_file = request.files['image']
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp:
            image_file.save(tmp.name)
            raw_text = extract_text_from_image(tmp.name)
        os.unlink(tmp.name)

        # Parse ingredients
        ingredients_list = parse_ingredients(raw_text)

        if not ingredients_list:
            return jsonify({
                "error": "Could not extract ingredients from image",
                "raw_text": raw_text,
                "tip": "Ensure label is flat, well-lit, and text is clearly visible"
            }), 422

        ingredients_text = ', '.join(ingredients_list)

        # Run full two-layer analysis
        result = predict_safety_full(ingredients_text, user_profile)

        return jsonify({
            "status": "success",
            "ocr_ingredients": ingredients_list,
            "ingredients_text": ingredients_text,
            "verdict": result['final_verdict'],
            "score": result['final_score'],
            "score_label": result['score_label'],
            "flagged_count": result['flagged_count'],
            "conflict_count": result['conflict_count'],
            "flagged_ingredients": result['flagged_ingredients'],
            "medication_conflicts": result['medication_conflicts'],
            "explanation": result['explanation'],
            "layer2_prediction": result['layer2_prediction'],
            "layer2_confidence": result['layer2_confidence'],
            "ml_score": result['ml_score'],
            "proportion_score": result['proportion_score']
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/ocr/analyze', methods=['POST'])
def ocr_analyze():
    """Accept a Base64 image, extract ingredients, and run full analysis."""
    import base64
    import tempfile
    import os

    temp_path = None

    try:
        data = request.get_json(silent=True) or {}

        image_base64 = data.get("image_base64")
        if not image_base64:
            return jsonify({"error": "No image provided"}), 400

        # Remove the data-URL prefix if the frontend included it.
        if "," in image_base64:
            image_base64 = image_base64.split(",", 1)[1]

        try:
            image_bytes = base64.b64decode(image_base64, validate=True)
        except Exception:
            return jsonify({"error": "Invalid Base64 image"}), 400

        if not image_bytes:
            return jsonify({"error": "Empty image"}), 400

        # Build the profile expected by the existing Layer 1 engine.
        user_profile = {
            "conditions": data.get("conditions", []),
            "medications": data.get("medications", [])
        }

        if not isinstance(user_profile["conditions"], list):
            return jsonify({"error": "conditions must be a list"}), 400

        if not isinstance(user_profile["medications"], list):
            return jsonify({"error": "medications must be a list"}), 400

        # Save decoded image temporarily for the existing OCR function.
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=".jpg"
        ) as temp:
            temp.write(image_bytes)
            temp_path = temp.name

        raw_text = extract_text_from_image(temp_path)
        ingredients_list = parse_ingredients(raw_text)

        if not ingredients_list:
            return jsonify({
                "error": "Could not extract ingredients from image",
                "raw_text": raw_text,
                "tip": "Use a clear, well-lit image of the ingredient label."
            }), 422

        ingredients_text = ", ".join(ingredients_list)

        # Reuse the existing complete safety-analysis pipeline.
        result = predict_safety_full(
            ingredients_text,
            user_profile
        )
        save_scan_if_member(data, 'Label photo', ingredients_text, result, 'photo')

        return jsonify({
            "success": True,
            "ocr": {
                "ingredients_extracted": ingredients_list,
                "ingredient_count": len(ingredients_list),
                "raw_text": raw_text
            },
            "analysis": result
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)

@app.route('/scan-barcode', methods=['POST'])
def scan_barcode():
    """Accepts a barcode number, looks up product, runs full analysis."""
    try:
        data = request.json
        if not data or 'barcode' not in data:
            return jsonify({"error": "barcode is required"}), 400
        if 'user_profile' not in data:
            return jsonify({"error": "user_profile is required"}), 400

        # Step 1: Look up barcode
        product = lookup_barcode(data['barcode'])

        if not product['success']:
            return jsonify({
                "error": product['error'],
                "barcode": data['barcode'],
                "suggestion": "Try scanning the label image instead"
            }), 404

        # Step 2: Run full analysis on ingredients
        result = predict_safety_full(
            product['ingredients_text'],
            data['user_profile']
        )

        # Step 3: Nutrition-based score adjustment
        nutrition = product.get('nutrition', {})
        sugar = nutrition.get('sugar_100g') or 0
        sodium = nutrition.get('sodium_100g') or 0
        sat_fat = nutrition.get('saturated_fat_100g') or 0

        nutrition_warnings = []
        if sugar > 22.5:
            nutrition_warnings.append(f"Very high sugar: {sugar}g per 100g (WHO limit: 22.5g)")
        if sodium > 0.6:
            nutrition_warnings.append(f"Very high sodium: {sodium}g per 100g (WHO limit: 0.6g)")
        if sat_fat > 5:
            nutrition_warnings.append(f"Very high saturated fat: {sat_fat}g per 100g (WHO limit: 5g)")

        # Step 4: Save to scan history if family_id + member_id provided
        family_id = data.get('family_id')
        member_id = data.get('member_id')
        print(f"DEBUG family_id: {family_id} | member_id: {member_id}")
        if family_id and member_id:
            try:
                save_result = save_scan(
                    family_id=family_id,
                    member_id=member_id,
                    product_name=product['product_name'],
                    ingredients_text=product['ingredients_text'],
                    verdict=result['final_verdict'],
                    score=result['final_score'],
                    score_label=result['score_label'],
                    flagged_count=result['flagged_count'],
                    conflict_count=result['conflict_count'],
                    flagged_ingredients=result['flagged_ingredients'],
                    source="barcode"
                )
                print(f"DEBUG save_result: {save_result}")
            except Exception as save_err:
                print(f"DEBUG save_scan ERROR: {save_err}")
        else:
            print("DEBUG: family_id or member_id missing â€” scan not saved")

        # Step 5: Return response
        return jsonify({
            "status": "success",
            "source": "barcode",
            "product_name": product['product_name'],
            "brand": product['brand'],
            "nutriscore": product['nutriscore'],
            "ingredients_text": product['ingredients_text'],
            "nutrition_per_100g": nutrition,
            "nutrition_warnings": nutrition_warnings,
            "verdict": result['final_verdict'],
            "score": result['final_score'],
            "score_label": result['score_label'],
            "flagged_count": result['flagged_count'],
            "conflict_count": result['conflict_count'],
            "flagged_ingredients": result['flagged_ingredients'],
            "medication_conflicts": result['medication_conflicts'],
            "explanation": result['explanation'],
            "layer2_prediction": result['layer2_prediction'],
            "layer2_confidence": result['layer2_confidence'],
            "ml_score": result['ml_score'],
            "proportion_score": result['proportion_score']
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
@app.route('/recommend', methods=['POST'])
def recommend():
    """
    Finds safer product alternatives for a flagged product.
    
    Request body:
    {
        "product_name": "Oreo",
        "ingredients_text": "sugar, wheat flour...",
        "category": "biscuits",      <- optional, from barcode lookup
        "user_profile": {
            "conditions": ["diabetes"],
            "medications": ["metformin"]
        }
    }
    """
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No data sent"}), 400
        if 'ingredients_text' not in data:
            return jsonify({"error": "ingredients_text is required"}), 400
        if 'user_profile' not in data:
            return jsonify({"error": "user_profile is required"}), 400

        result = get_recommendations(
            scanned_product_name=data.get("product_name", ""),
            scanned_ingredients=data["ingredients_text"],
            scanned_category=data.get("category", ""),
            user_profile=data["user_profile"],
            predict_fn=predict_safety_full,
            top_n=3
        )

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# â”€â”€ FAMILY ACCOUNT ROUTES â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@app.route('/family/register', methods=['POST'])
def family_register():
    """Create a new family account."""
    data = request.json
    if not data:
        return jsonify({"error": "No data sent"}), 400
    required = ['head_name', 'email', 'password']
    for field in required:
        if field not in data:
            return jsonify({"error": f"Missing {field}"}), 400

    result = create_family(
        data['head_name'],
        data['email'],
        data['password']
    )
    status = 200 if result['success'] else 400
    return jsonify(result), status


@app.route('/family/login', methods=['POST'])
def family_login():
    """Login to family account."""
    data = request.json
    if not data or 'email' not in data or 'password' not in data:
        return jsonify({"error": "Email and password required"}), 400

    result = login_family(data['email'], data['password'])
    status = 200 if result['success'] else 401
    return jsonify(result), status


@app.route('/family/<family_id>/members', methods=['GET'])
def get_members(family_id):
    """Get all family members."""
    members = get_family_members(family_id)
    return jsonify({"family_id": family_id, "members": members})


@app.route('/family/<family_id>/members', methods=['POST'])
def add_member(family_id):
    """Add a new family member."""
    data = request.json
    if not data or 'name' not in data:
        return jsonify({"error": "name is required"}), 400

    result = add_family_member(
        family_id=family_id,
        name=data['name'],
        age=data.get('age'),
        gender=data.get('gender'),
        relationship=data.get('relationship', 'Family Member'),
        conditions=data.get('conditions', []),
        medications=data.get('medications', []),
        allergies=data.get('allergies', [])
    )
    status = 200 if result['success'] else 400
    return jsonify(result), status


@app.route('/family/<family_id>/members/<member_id>', methods=['PUT'])
def update_member(family_id, member_id):
    """Update a family member's profile."""
    data = request.json
    if not data:
        return jsonify({"error": "No data sent"}), 400

    result = update_family_member(member_id, family_id, data)
    status = 200 if result['success'] else 400
    return jsonify(result), status


@app.route('/family/<family_id>/members/<member_id>', methods=['DELETE'])
def delete_member(family_id, member_id):
    """Remove a family member."""
    result = delete_family_member(member_id, family_id)
    status = 200 if result['success'] else 400
    return jsonify(result), status


@app.route('/family/<family_id>/dashboard', methods=['GET'])
def family_dashboard(family_id):
    """Get family health dashboard."""
    dashboard = get_family_dashboard(family_id)
    return jsonify(dashboard)


@app.route('/family/<family_id>/history', methods=['GET'])
def family_history(family_id):
    """Get scan history for entire family."""
    member_id = request.args.get('member_id')
    limit = int(request.args.get('limit', 20))
    history = get_scan_history(family_id, member_id, limit)
    return jsonify({"family_id": family_id, "history": history})

# â”€â”€ Start server â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
if __name__ == '__main__':
    print("\n" + "="*45)
    print("HealthSafe AI API starting...")
    print("URL: http://localhost:5000")
    print("="*45 + "\n")
    app.run(debug=True, port=5000)
