import requests
import re

OPENFOODFACTS_SEARCH = "https://world.openfoodfacts.org/cgi/search.pl"

HEADERS = {
    "User-Agent": "HealthSafeAI/1.0 (contact: ambusrivastava965@gmail.com)"
}

def get_category_from_ingredients(ingredients_text: str, product_name: str = "") -> str:
    """
    Guess product category from product name or ingredients.
    Used when barcode lookup doesn't return a category.
    """
    text = (product_name + " " + ingredients_text).lower()

    if any(w in text for w in ["biscuit", "cookie", "cracker", "wafer"]):
        return "biscuits"
    elif any(w in text for w in ["chips", "crisps", "namkeen", "snack"]):
        return "chips-and-crisps"
    elif any(w in text for w in ["chocolate", "cocoa"]):
        return "chocolates"
    elif any(w in text for w in ["bread", "toast", "roti"]):
        return "breads"
    elif any(w in text for w in ["juice", "drink", "beverage", "cola", "soda"]):
        return "beverages"
    elif any(w in text for w in ["milk", "dairy", "yogurt", "curd"]):
        return "dairy"
    elif any(w in text for w in ["noodles", "pasta", "maggi"]):
        return "pastas"
    elif any(w in text for w in ["cereal", "oats", "granola", "muesli"]):
        return "cereals"
    elif any(w in text for w in ["sauce", "ketchup", "mayo", "dressing"]):
        return "sauces"
    elif any(w in text for w in ["jam", "jelly", "spread", "butter"]):
        return "spreads"
    else:
        return "snacks"

def search_alternatives(category: str, max_results: int = 100) -> list:
    """
    Search multiple pages of Open Food Facts for English-language products.
    Falls back to local Indian product database if OFF is unavailable.
    """
    category_map = {
        "biscuits": "biscuits-and-cakes",
        "chips-and-crisps": "chips-and-crisps",
        "chocolates": "chocolates",
        "breads": "breads",
        "beverages": "beverages",
        "dairy": "dairy",
        "pastas": "pastas",
        "cereals": "cereals",
        "sauces": "sauces",
        "spreads": "spreads",
        "snacks": "snacks",
    }

    off_category = category_map.get(category, category)
    all_products = []

    # Try Open Food Facts first
    for page in range(1, 5):
        try:
            url = f"https://world.openfoodfacts.org/category/{off_category}/{page}.json"
            response = requests.get(url, headers=HEADERS, timeout=10)

            if response.status_code != 200:
                print(f"OFF returned {response.status_code} — switching to local database")
                break

            data = response.json()
            products = data.get("products", [])

            if not products:
                break

            for p in products:
                ingredients = (
                    p.get("ingredients_text_en") or
                    p.get("ingredients_text") or ""
                ).strip()

                if not ingredients or len(ingredients) < 10:
                    continue

                ascii_ratio = sum(1 for c in ingredients if ord(c) < 128) / len(ingredients)
                if ascii_ratio < 0.85:
                    continue

                all_products.append(p)

            print(f"  Page {page}: {len(all_products)} English products so far")

            if len(all_products) >= max_results:
                break

        except Exception as e:
            print(f"Page {page} failed: {e} — switching to local database")
            break

    # Fallback to local Indian product database if OFF returned nothing
    if not all_products:
        print("Using local Indian product database as fallback")
        from local_product_db import get_local_alternatives
        local = get_local_alternatives(category)
        all_products = [{
            "product_name": p["product_name"],
            "brands": p["brand"],
            "ingredients_text": p["ingredients_text"],
            "nutriscore_grade": p["nutriscore"],
            "nutriments": {}
        } for p in local]
        print(f"  Local database: {len(all_products)} products found")

    return all_products[:max_results]
def score_product_for_user(product: dict, user_profile: dict,
                            predict_fn) -> dict | None:
    """
    Score a candidate product for a specific user.
    Returns scored product dict or None if ingredients unavailable.
    """
    ingredients_text = (
        product.get("ingredients_text_en") or
        product.get("ingredients_text") or
        ""
    ).strip()

    if not ingredients_text or len(ingredients_text) < 10:
        return None

    product_name = product.get("product_name", "Unknown Product")
    brand = product.get("brands", "Unknown Brand")
    nutriscore = product.get("nutriscore_grade", "?").upper()

    # Run full safety analysis
    try:
        result = predict_fn(ingredients_text, user_profile)
    except Exception:
        return None

    # Get nutrition
    nutriments = product.get("nutriments", {})
    sugar = nutriments.get("sugars_100g", 0) or 0
    sodium = nutriments.get("sodium_100g", 0) or 0
    sat_fat = nutriments.get("saturated-fat_100g", 0) or 0

    return {
        "product_name": product_name,
        "brand": brand,
        "nutriscore": nutriscore,
        "verdict": result["final_verdict"],
        "score": result["final_score"],
        "score_label": result["score_label"],
        "flagged_count": result["flagged_count"],
        "conflict_count": result["conflict_count"],
        "ingredients_text": ingredients_text,
        "nutrition_per_100g": {
            "sugar_100g": round(sugar, 1),
            "sodium_100g": round(sodium, 3),
            "saturated_fat_100g": round(sat_fat, 1),
        }
    }
def get_recommendations(
    scanned_product_name: str,
    scanned_ingredients: str,
    scanned_category: str,
    user_profile: dict,
    predict_fn,
    top_n: int = 3
) -> dict:
    """
    Main function — finds safer alternatives for a flagged product.
    """
    # Determine category
    category = scanned_category or get_category_from_ingredients(
        scanned_ingredients, scanned_product_name
    )

    # Search for candidates
    candidates = search_alternatives(category, max_results=100)

    if not candidates:
        return {
            "success": False,
            "error": "No alternatives found in database",
            "category": category,
            "alternatives": []
        }

    print(f"\nScoring {len(candidates)} candidates for category: {category}")

    # Score each candidate
    scored = []
    for product in candidates:
        scored_product = score_product_for_user(product, user_profile, predict_fn)
        if scored_product is None:
            continue

        # Skip if same product name
        if scored_product["product_name"].lower() == scanned_product_name.lower():
            continue

        # Debug
        print(f"  {scored_product['product_name'][:35]:<35} → {scored_product['verdict']:<8} | {scored_product['score']}/100 | flags: {scored_product['flagged_count']}")

        scored.append(scored_product)

    print(f"\nTotal scored: {len(scored)} products")

    if not scored:
        return {
            "success": False,
            "error": f"No alternatives found in {category} category",
            "category": category,
            "alternatives": []
        }

    # Sort by score descending — highest score = safest relative option
    scored.sort(key=lambda x: x["score"], reverse=True)

    # Tag each alternative
    for alt in scored:
        alt["safer_than_scanned"] = True
        alt["note"] = "Relatively safer option — consult your doctor before consuming"

    top_alternatives = scored[:top_n]

    return {
        "success": True,
        "category": category,
        "total_candidates_checked": len(scored),
        "disclaimer": "These are relatively safer options compared to the scanned product. Always consult your doctor.",
        "alternatives": top_alternatives
    }