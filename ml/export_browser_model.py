"""
Export the HealthSafe pipeline for the in-browser engine (frontend/src/engine).

Writes:
  frontend/public/engine/model.json   TF-IDF vocabulary + idf and the XGBoost trees
  frontend/src/engine/rules.json      INGREDIENT_RULES and MEDICATION_CONFLICTS from backend/app.py
  frontend/src/engine/products.json   LOCAL_PRODUCTS from backend/local_product_db.py

Re-run after retraining the model or editing the rules:
  python ml/export_browser_model.py
"""
import ast
import json
import os
import pickle
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def export_model():
    pipeline = pickle.load(open(os.path.join(ROOT, "ml", "healthsafe_model_v6.pkl"), "rb"))
    tfidf = pipeline.named_steps["tfidf"]
    clf = pipeline.named_steps["model"]

    assert tfidf.analyzer == "word" and tfidf.lowercase and tfidf.norm == "l2"
    assert tfidf.sublinear_tf and tfidf.use_idf and tfidf.stop_words is None

    vocab = [None] * len(tfidf.vocabulary_)
    for term, idx in tfidf.vocabulary_.items():
        vocab[idx] = term

    # The JSON model format keeps full float32 precision for thresholds and leaves.
    booster = clf.get_booster()
    raw = json.loads(booster.save_raw("json").decode())
    learner = raw["learner"]
    base_score = learner["learner_model_param"]["base_score"]
    base_score = float(json.loads(base_score)[0] if base_score.startswith("[") else base_score)
    objective = learner["objective"]["name"]
    assert objective == "binary:logistic", objective

    trees = []
    for t in learner["gradient_booster"]["model"]["trees"]:
        trees.append({
            "l": t["left_children"],
            "r": t["right_children"],
            "f": t["split_indices"],
            "c": t["split_conditions"],
            "d": [int(x) for x in t["default_left"]],
        })

    model = {
        "tfidf": {
            "vocab": vocab,
            "idf": [float(x) for x in tfidf.idf_],
            "ngram": list(tfidf.ngram_range),
            "token_pattern": tfidf.token_pattern,
        },
        "xgb": {"base_score": base_score, "classes": [int(c) for c in clf.classes_], "trees": trees},
    }
    out = os.path.join(ROOT, "frontend", "public", "engine", "model.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(model, f, separators=(",", ":"))
    print(f"model.json  {os.path.getsize(out) / 1e6:.2f} MB  ({len(trees)} trees, {len(vocab)} terms)")


def literal_assignments(path, names):
    """Evaluate top-level `NAME = <literal>` assignments without importing the module."""
    tree = ast.parse(open(path, encoding="utf-8-sig").read())
    found = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name) and target.id in names:
                found[target.id] = ast.literal_eval(node.value)
    missing = set(names) - set(found)
    assert not missing, f"{path}: missing {missing}"
    return found


def export_rules_and_products():
    rules = literal_assignments(os.path.join(ROOT, "backend", "app.py"), ["INGREDIENT_RULES", "MEDICATION_CONFLICTS"])
    out = os.path.join(ROOT, "frontend", "src", "engine", "rules.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(rules, f, ensure_ascii=False, indent=1)
    print(f"rules.json  {len(rules['INGREDIENT_RULES'])} ingredient rules, {len(rules['MEDICATION_CONFLICTS'])} medicines")

    products = literal_assignments(os.path.join(ROOT, "backend", "local_product_db.py"), ["LOCAL_PRODUCTS"])["LOCAL_PRODUCTS"]
    out = os.path.join(ROOT, "frontend", "src", "engine", "products.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=1)
    print(f"products.json  {len(products)} products")


if __name__ == "__main__":
    export_model()
    export_rules_and_products()
    sys.exit(0)
