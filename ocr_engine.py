import pytesseract
from PIL import Image, ImageEnhance, ImageFilter

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def preprocess_image(img):
    img = img.resize((img.width * 3, img.height * 3), Image.LANCZOS)
    img = img.convert('L')
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(3.0)
    enhancer2 = ImageEnhance.Sharpness(img)
    img = enhancer2.enhance(2.0)
    img = img.filter(ImageFilter.MedianFilter())
    return img

def extract_text_from_image(image_path):
    img = Image.open(image_path)
    img = preprocess_image(img)
    text = pytesseract.image_to_string(img, config='--psm 6')
    return text

def parse_ingredients(raw_text):
    text = raw_text.lower()
    if "ingredients" not in text:
        return []
    start = text.index("ingredients") + len("ingredients")
    section = raw_text[start:].strip(": \n")
    low = section.lower()
    for stop_word in ["allergen", "may contain", "contains wheat", "numbers in brackets"]:
        if stop_word in low:
            section = section[:low.index(stop_word)]
            break
    section = " ".join(section.splitlines())
    ingredients = []
    for item in section.split(","):
        cleaned = ''.join(c for c in item if c.isalpha() or c in " ()%.")
        cleaned = cleaned.strip().lower()
        if len(cleaned) > 2:
            ingredients.append(cleaned)
    return ingredients

if __name__ == "__main__":
    text = extract_text_from_image("test_label.jpg")
    print("Raw text:\n", text)
    print("\nIngredients:", parse_ingredients(text))
