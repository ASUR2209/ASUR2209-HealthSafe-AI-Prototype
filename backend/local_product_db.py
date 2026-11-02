# Local database of common Indian packaged foods
# Used as fallback when Open Food Facts API is unavailable

LOCAL_PRODUCTS = [
    # ── BISCUITS ──────────────────────────────────────────────
    {
        "product_name": "Digestive Biscuits",
        "brand": "McVitie's",
        "category": "biscuits",
        "ingredients_text": "whole wheat flour, sugar, vegetable oil, oatmeal, malt extract, raising agents, salt",
        "nutriscore": "C",
    },
    {
        "product_name": "Marie Biscuits",
        "brand": "Britannia",
        "category": "biscuits",
        "ingredients_text": "wheat flour, sugar, vegetable oil, invert syrup, milk solids, raising agents, salt, dough conditioner",
        "nutriscore": "C",
    },
    {
        "product_name": "Oat Cookies",
        "brand": "Unibic",
        "category": "biscuits",
        "ingredients_text": "whole oats, wheat flour, brown sugar, vegetable oil, honey, raisins, cinnamon, salt, raising agents",
        "nutriscore": "B",
    },
    {
        "product_name": "Ragi Biscuits",
        "brand": "Patanjali",
        "category": "biscuits",
        "ingredients_text": "ragi flour, whole wheat flour, jaggery, vegetable oil, milk solids, cardamom, raising agents, salt",
        "nutriscore": "B",
    },
    {
        "product_name": "Multigrain Crackers",
        "brand": "Britannia",
        "category": "biscuits",
        "ingredients_text": "whole wheat flour, oats, ragi, corn, vegetable oil, sugar, salt, raising agents, sesame seeds",
        "nutriscore": "B",
    },
    {
        "product_name": "Glucose Biscuits",
        "brand": "Parle-G",
        "category": "biscuits",
        "ingredients_text": "wheat flour, sugar, partially hydrogenated vegetable oil, invert syrup, milk solids, leavening agents, salt",
        "nutriscore": "D",
    },

    # ── SNACKS ────────────────────────────────────────────────
    {
        "product_name": "Roasted Almonds",
        "brand": "Happilo",
        "category": "snacks",
        "ingredients_text": "almonds, salt",
        "nutriscore": "A",
    },
    {
        "product_name": "Roasted Makhana",
        "brand": "Go Healthy",
        "category": "snacks",
        "ingredients_text": "fox nuts, rock salt, ghee",
        "nutriscore": "A",
    },
    {
        "product_name": "Baked Wheat Puffs",
        "brand": "Yoga Bar",
        "category": "snacks",
        "ingredients_text": "whole wheat flour, oats, sunflower oil, rock salt, herbs, spices",
        "nutriscore": "B",
    },
    {
        "product_name": "Roasted Chana",
        "brand": "Haldirams",
        "category": "snacks",
        "ingredients_text": "chickpeas, vegetable oil, salt, spices, lemon",
        "nutriscore": "A",
    },
    {
        "product_name": "Baked Chips",
        "brand": "Bingo",
        "category": "snacks",
        "ingredients_text": "potato, sunflower oil, salt, spices, starch",
        "nutriscore": "C",
    },

    # ── CEREALS ───────────────────────────────────────────────
    {
        "product_name": "Rolled Oats",
        "brand": "Quaker",
        "category": "cereals",
        "ingredients_text": "whole grain rolled oats",
        "nutriscore": "A",
    },
    {
        "product_name": "Muesli No Added Sugar",
        "brand": "Yoga Bar",
        "category": "cereals",
        "ingredients_text": "rolled oats, almonds, raisins, sunflower seeds, pumpkin seeds, flaxseeds, dried cranberries",
        "nutriscore": "A",
    },
    {
        "product_name": "Cornflakes",
        "brand": "Kelloggs",
        "category": "cereals",
        "ingredients_text": "milled corn, sugar, salt, malt flavoring, vitamins, iron",
        "nutriscore": "B",
    },
    {
        "product_name": "Wheat Bran Flakes",
        "brand": "Kelloggs",
        "category": "cereals",
        "ingredients_text": "whole wheat flour, wheat bran, sugar, salt, malt extract, vitamins, iron",
        "nutriscore": "B",
    },

    # ── BEVERAGES ─────────────────────────────────────────────
    {
        "product_name": "Green Tea",
        "brand": "Tetley",
        "category": "beverages",
        "ingredients_text": "green tea leaves",
        "nutriscore": "A",
    },
    {
        "product_name": "Coconut Water",
        "brand": "Raw Pressery",
        "category": "beverages",
        "ingredients_text": "100% natural coconut water",
        "nutriscore": "A",
    },
    {
        "product_name": "Nimbu Pani Mix No Sugar",
        "brand": "Paper Boat",
        "category": "beverages",
        "ingredients_text": "lemon juice, rock salt, cumin, black pepper, mint",
        "nutriscore": "A",
    },

    # ── DAIRY ─────────────────────────────────────────────────
    {
        "product_name": "Low Fat Yogurt Plain",
        "brand": "Amul",
        "category": "dairy",
        "ingredients_text": "skimmed milk, milk solids, live cultures",
        "nutriscore": "A",
    },
    {
        "product_name": "Paneer Low Fat",
        "brand": "Mother Dairy",
        "category": "dairy",
        "ingredients_text": "skimmed milk, citric acid",
        "nutriscore": "B",
    },

    # ── SPREADS ───────────────────────────────────────────────
    {
        "product_name": "Peanut Butter Natural",
        "brand": "Pintola",
        "category": "spreads",
        "ingredients_text": "roasted peanuts",
        "nutriscore": "A",
    },
    {
        "product_name": "Almond Butter",
        "brand": "Alpino",
        "category": "spreads",
        "ingredients_text": "dry roasted almonds",
        "nutriscore": "A",
    },

    # ── CHOCOLATES ────────────────────────────────────────────
    {
        "product_name": "Dark Chocolate 85%",
        "brand": "Amul",
        "category": "chocolates",
        "ingredients_text": "cocoa mass, cocoa butter, sugar, vanilla",
        "nutriscore": "B",
    },
    {
        "product_name": "Dark Chocolate 70%",
        "brand": "Lindt",
        "category": "chocolates",
        "ingredients_text": "cocoa mass, sugar, cocoa butter, vanilla extract",
        "nutriscore": "B",
    },
        # Add these to LOCAL_PRODUCTS in the biscuits section
    {
        "product_name": "Nutrichoice Hi-Fibre Digestive",
        "brand": "Britannia",
        "category": "biscuits",
        "ingredients_text": "whole wheat flour, oat bran, vegetable oil, invert syrup, malt extract, salt, raising agents",
        "nutriscore": "B",
    },
    {
        "product_name": "Sugarfree Oat Biscuits",
        "brand": "Sunfeast",
        "category": "biscuits",
        "ingredients_text": "whole oats, whole wheat flour, vegetable oil, maltitol, inulin fibre, salt, raising agents",
        "nutriscore": "B",
    },
    {
        "product_name": "Ragi Almond Cookies Sugarfree",
        "brand": "Early Foods",
        "category": "biscuits",
        "ingredients_text": "ragi flour, almond flour, coconut oil, stevia, cardamom, salt",
        "nutriscore": "A",
    },
    {
        "product_name": "Multigrain Sugarfree Biscuits",
        "brand": "Diabetic Food",
        "category": "biscuits",
        "ingredients_text": "whole wheat flour, oat flour, ragi flour, soya flour, vegetable oil, stevia, inulin, salt, raising agents",
        "nutriscore": "A",
    },
]


def get_local_alternatives(category: str) -> list:
    """Returns local products matching the given category."""
    return [p for p in LOCAL_PRODUCTS if p["category"] == category]