import requests

OPENFOODFACTS_URL = "https://world.openfoodfacts.org/api/v0/product/{barcode}.json"

def lookup_barcode(barcode: str) -> dict:
    """
    Look up a product by barcode using Open Food Facts API.
    Returns ingredients text and product info if found.
    """
    try:
        url = OPENFOODFACTS_URL.format(barcode=barcode)
        response = requests.get(url, timeout=10, headers={
    "User-Agent": "HealthSafeAI/1.0 (contact: ambusrivastava965@gmail.com)"
})
        data = response.json()

        if data.get("status") != 1:
            return {
                "success": False,
                "error": "Product not found in database",
                "barcode": barcode
            }

        product = data.get("product", {})

        # Extract ingredients text
        ingredients_text = (
            product.get("ingredients_text_en") or
            product.get("ingredients_text") or
            ""
        ).strip()

        if not ingredients_text:
            return {
                "success": False,
                "error": "Product found but no ingredient data available",
                "barcode": barcode,
                "product_name": product.get("product_name", "Unknown")
            }

        return {
            "success": True,
            "barcode": barcode,
            "product_name": product.get("product_name", "Unknown"),
            "brand": product.get("brands", "Unknown"),
            "category": product.get("categories", ""),
            "ingredients_text": ingredients_text,
            "nutriscore": product.get("nutriscore_grade", "unknown").upper(),
            "image_url": product.get("image_url", ""),
            "nutrition": {
                "energy_kcal": product.get("nutriments", {}).get("energy-kcal_100g"),
                "sugar_100g": product.get("nutriments", {}).get("sugars_100g"),
                "sodium_100g": product.get("nutriments", {}).get("sodium_100g"),
                "fat_100g": product.get("nutriments", {}).get("fat_100g"),
                "saturated_fat_100g": product.get("nutriments", {}).get("saturated-fat_100g"),
            }
        }

    except requests.exceptions.Timeout:
        return {"success": False, "error": "Request timed out — check internet connection"}
    except Exception as e:
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    # Test with Oreo barcode
    result = lookup_barcode("7622210449283")
    if result["success"]:
        print(f"Product: {result['product_name']}")
        print(f"Brand: {result['brand']}")
        print(f"Nutriscore: {result['nutriscore']}")
        print(f"\nIngredients:\n{result['ingredients_text']}")
        print(f"\nNutrition per 100g:")
        for k, v in result['nutrition'].items():
            print(f"  {k}: {v}")
    else:
        print(f"Error: {result['error']}")