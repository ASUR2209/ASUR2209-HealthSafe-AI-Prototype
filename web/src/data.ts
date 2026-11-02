// Vocabulary mirrored from backend/app.py (INGREDIENT_RULES / MEDICATION_CONFLICTS).

export const CONDITION_GROUPS: { label: string; items: string[] }[] = [
  { label: "Blood sugar", items: ["diabetes", "prediabetes", "pcos"] },
  { label: "Heart & pressure", items: ["hypertension", "heart_disease", "high_cholesterol", "heart_arrhythmia"] },
  { label: "Kidney & liver", items: ["kidney_disease", "kidney_stones", "liver_disease", "fatty_liver", "gout", "high_uric_acid"] },
  { label: "Thyroid", items: ["hypothyroidism", "hyperthyroidism"] },
  {
    label: "Allergies & intolerances",
    items: [
      "peanut_allergy", "tree_nut_allergy", "dairy_allergy", "lactose_intolerance", "egg_allergy",
      "wheat_allergy", "celiac_disease", "shellfish_allergy", "fish_allergy", "sesame_allergy",
      "mustard_allergy", "sulphite_sensitivity",
    ],
  },
  { label: "Other", items: ["asthma", "hyperactivity"] },
];

export const MEDICATIONS = [
  "metformin", "glipizide", "glimepiride", "glyburide", "insulin", "sitagliptin", "empagliflozin",
  "dapagliflozin", "lisinopril", "enalapril", "losartan", "telmisartan", "amlodipine", "nifedipine",
  "metoprolol", "atenolol", "propranolol", "hydrochlorothiazide", "furosemide", "statins", "atorvastatin",
  "rosuvastatin", "simvastatin", "levothyroxine", "carbimazole", "warfarin", "aspirin", "clopidogrel",
  "ciprofloxacin", "amoxicillin", "azithromycin", "doxycycline", "metronidazole", "omeprazole",
  "pantoprazole", "ranitidine", "sertraline", "fluoxetine", "alprazolam", "ibuprofen", "paracetamol",
  "diclofenac",
];

export const pretty = (s: string) => {
  const t = s.replace(/_/g, " ");
  return t.charAt(0).toUpperCase() + t.slice(1);
};

// The backend source was saved with a double-encoded em dash; repair it for display.
export const fixText = (s: string | undefined | null) =>
  (s ?? "").replace(/â€”/g, "—").replace(/â€“/g, "–").replace(/â€™/g, "’");

export const SAMPLES: { name: string; text: string }[] = [
  {
    name: "Cream biscuit",
    text: "Refined wheat flour (maida), sugar, palm oil, invert sugar syrup, cocoa solids, leavening agents (sodium bicarbonate, ammonium bicarbonate), iodised salt, emulsifier (soy lecithin), artificial flavour",
  },
  {
    name: "Instant noodles",
    text: "Wheat flour, palm oil, salt, tapioca starch, monosodium glutamate, disodium inosinate, sugar, garlic powder, onion powder, chilli powder, turmeric, potassium carbonate",
  },
  {
    name: "Rolled oats",
    text: "Whole grain rolled oats",
  },
  {
    name: "Milk chocolate",
    text: "Sugar, cocoa butter, milk solids, cocoa solids, whey powder, emulsifier (soy lecithin), vanilla flavour, peanut traces",
  },
];

type Rule = { risk: "HIGH" | "MEDIUM"; conditions: string[]; reason: string };

// Subset of the backend rules, used only by the offline demo engine.
export const DEMO_RULES: Record<string, Rule> = {
  sugar: { risk: "HIGH", conditions: ["diabetes", "prediabetes", "pcos"], reason: "Direct blood glucose spike." },
  "invert sugar": { risk: "HIGH", conditions: ["diabetes", "prediabetes"], reason: "Rapidly raises blood glucose." },
  "corn syrup": { risk: "HIGH", conditions: ["diabetes", "prediabetes"], reason: "High glycemic index." },
  dextrose: { risk: "HIGH", conditions: ["diabetes", "prediabetes"], reason: "Direct blood sugar raiser." },
  maltodextrin: { risk: "HIGH", conditions: ["diabetes", "prediabetes"], reason: "Higher GI than table sugar." },
  glucose: { risk: "HIGH", conditions: ["diabetes", "prediabetes"], reason: "Direct blood glucose spike." },
  maida: { risk: "HIGH", conditions: ["diabetes", "prediabetes", "pcos"], reason: "Refined flour — very high glycemic index." },
  "refined wheat flour": { risk: "HIGH", conditions: ["diabetes", "prediabetes", "pcos"], reason: "Refined flour spikes blood sugar fast." },
  salt: { risk: "HIGH", conditions: ["hypertension", "kidney_disease"], reason: "Primary sodium source — raises blood pressure." },
  sodium: { risk: "HIGH", conditions: ["hypertension", "kidney_disease"], reason: "Raises blood pressure." },
  "monosodium glutamate": { risk: "HIGH", conditions: ["hypertension"], reason: "High sodium — raises blood pressure." },
  disodium: { risk: "HIGH", conditions: ["hypertension", "kidney_disease"], reason: "Sodium-based additive." },
  "sodium bicarbonate": { risk: "MEDIUM", conditions: ["hypertension", "kidney_disease"], reason: "High sodium content." },
  "palm oil": { risk: "HIGH", conditions: ["heart_disease", "high_cholesterol"], reason: "High saturated fat — raises LDL cholesterol." },
  hydrogenated: { risk: "HIGH", conditions: ["heart_disease", "high_cholesterol"], reason: "Trans fat — significantly raises cardiovascular risk." },
  butter: { risk: "MEDIUM", conditions: ["heart_disease", "high_cholesterol"], reason: "High saturated fat and cholesterol." },
  potassium: { risk: "HIGH", conditions: ["kidney_disease"], reason: "High potassium is dangerous for kidney patients." },
  phosphate: { risk: "HIGH", conditions: ["kidney_disease"], reason: "Kidneys cannot filter phosphates — bone disease risk." },
  soy: { risk: "MEDIUM", conditions: ["hypothyroidism"], reason: "Interferes with thyroid medication absorption." },
  alcohol: { risk: "HIGH", conditions: ["liver_disease", "fatty_liver"], reason: "Directly toxic to liver cells." },
  peanut: { risk: "HIGH", conditions: ["peanut_allergy"], reason: "Severe anaphylaxis risk." },
  wheat: { risk: "HIGH", conditions: ["celiac_disease", "wheat_allergy"], reason: "Contains gluten — triggers immune attack." },
  oats: { risk: "MEDIUM", conditions: ["celiac_disease"], reason: "Often cross-contaminated with gluten." },
  milk: { risk: "HIGH", conditions: ["lactose_intolerance", "dairy_allergy"], reason: "Contains lactose and dairy proteins." },
  whey: { risk: "HIGH", conditions: ["dairy_allergy"], reason: "Dairy protein — triggers allergic reaction." },
  egg: { risk: "HIGH", conditions: ["egg_allergy"], reason: "Triggers allergic reaction in egg allergy." },
};

export const DEMO_MED_CONFLICTS: Record<string, Record<string, string>> = {
  metformin: {
    alcohol: "HIGH — alcohol + metformin causes dangerous lactic acidosis",
    sugar: "MEDIUM — directly counteracts blood glucose control",
    maida: "MEDIUM — high GI flour counteracts metformin",
  },
  insulin: {
    alcohol: "HIGH — alcohol causes dangerous hypoglycemia with insulin",
    sugar: "HIGH — directly raises blood glucose, counteracts insulin",
  },
  levothyroxine: { soy: "HIGH — soy blocks levothyroxine absorption" },
  warfarin: { alcohol: "HIGH — increases bleeding risk" },
  lisinopril: { potassium: "HIGH — dangerous potassium buildup", salt: "MEDIUM — counteracts blood pressure control" },
};
