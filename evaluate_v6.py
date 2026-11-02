import gc
import pickle
import re
from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix
)

# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

DATASET = "en.openfoodfacts.org.products.csv.gz"
MODEL = "healthsafe_model_v6.pkl"
CHUNK_SIZE = 100000

# --------------------------------------------------
# CLEANING FUNCTION
# --------------------------------------------------

def clean_ingredients(text):
    text = str(text).lower()
    text = re.sub(r'\d+(\.\d+)?\s*%', '', text)
    text = re.sub(r'[^a-zA-Z\s,]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


# --------------------------------------------------
# DATASET RECONSTRUCTION
# --------------------------------------------------

def filtered_chunks():

    for chunk in pd.read_csv(
        DATASET,
        sep="\t",
        usecols=["ingredients_text", "nutriscore_grade"],
        chunksize=CHUNK_SIZE,
        low_memory=False,
        on_bad_lines="skip"
    ):

        chunk = chunk.dropna(
            subset=["ingredients_text", "nutriscore_grade"]
        )

        chunk = chunk[
            chunk["ingredients_text"].str.len() > 10
        ]

        ascii_ratio = chunk["ingredients_text"].apply(
            lambda x: sum(1 for c in str(x) if ord(c) < 128)
            / len(str(x)) > 0.85
        )

        chunk = chunk[ascii_ratio]

        chunk["ingredients_clean"] = (
            chunk["ingredients_text"].apply(clean_ingredients)
        )

        grade_map = {
            "a": 0,
            "b": 1,
            "c": 2,
            "d": 3,
            "e": 4
        }

        grades = (
            chunk["nutriscore_grade"]
            .str.lower()
            .str.strip()
            .map(grade_map)
        )

        valid = grades.notna()

        # Correct v6 mapping:
        # A/B = Safe (0)
        # C/D/E = Unsafe (1)

        labels = (
            grades.loc[valid].astype(int).to_numpy() > 1
        ).astype(np.int8)

        texts = (
            chunk.loc[valid, "ingredients_clean"]
            .to_numpy()
        )

        yield texts, labels

        del chunk, grades, valid, labels, texts
        gc.collect()


# --------------------------------------------------
# CHECK FILES
# --------------------------------------------------

if not Path(DATASET).exists():
    raise FileNotFoundError(DATASET)

if not Path(MODEL).exists():
    raise FileNotFoundError(MODEL)

print("Loading saved v6 model...")

with open(MODEL, "rb") as f:
    pipeline = pickle.load(f)


# --------------------------------------------------
# PASS 1: RECONSTRUCT LABELS
# --------------------------------------------------

print("\nPASS 1: Reconstructing dataset...")

label_parts = []

for texts, labels in filtered_chunks():
    label_parts.append(labels)

y = np.concatenate(label_parts)

del label_parts
gc.collect()

print("\nTotal rows:", len(y))
print("Safe:", int((y == 0).sum()))
print("Unsafe:", int((y == 1).sum()))

EXPECTED_SAFE = 207964
EXPECTED_UNSAFE = 625207

if (
    int((y == 0).sum()) != EXPECTED_SAFE
    or int((y == 1).sum()) != EXPECTED_UNSAFE
):
    raise ValueError(
        "Dataset counts do not match original v6 dataset. "
        "Stop evaluation and investigate preprocessing."
    )

# Recreate original split

_, test_indices = train_test_split(
    np.arange(len(y)),
    test_size=0.2,
    random_state=42,
    stratify=y
)

y_test = y[test_indices]

print("Test rows:", len(test_indices))


# --------------------------------------------------
# PASS 2: PREDICT ON ORIGINAL TEST ROWS
# --------------------------------------------------

print("\nPASS 2: Evaluating v6 model...")

test_indices.sort()

probability_parts = []
actual_parts = []

offset = 0

for texts, labels in filtered_chunks():

    end = offset + len(labels)

    positions = np.flatnonzero(
        (test_indices >= offset)
        & (test_indices < end)
    )

    if len(positions) > 0:

        local_indices = test_indices[positions] - offset

        test_texts = texts[local_indices]

        probabilities = pipeline.predict_proba(test_texts)

        unsafe_column = list(pipeline.classes_).index(1)

        probability_parts.append(
            probabilities[:, unsafe_column]
        )

        actual_parts.append(labels[local_indices])

    offset = end

    del texts, labels
    gc.collect()

y_actual = np.concatenate(actual_parts)
unsafe_prob = np.concatenate(probability_parts)

# --------------------------------------------------
# BASELINE EVALUATION
# --------------------------------------------------

print("\n========== V6 BASELINE ==========")

y_pred = (unsafe_prob >= 0.50).astype(int)

print("Accuracy:", accuracy_score(y_actual, y_pred))

print("\nConfusion Matrix:")
print(confusion_matrix(y_actual, y_pred))

print("\nClassification Report:")
print(
    classification_report(
        y_actual,
        y_pred,
        target_names=["Safe", "Unsafe"]
    )
)


# --------------------------------------------------
# THRESHOLD COMPARISON
# --------------------------------------------------

print("\n========== THRESHOLD ANALYSIS ==========")

for threshold in [0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70]:

    predictions = (unsafe_prob >= threshold).astype(int)

    print(f"\nThreshold: {threshold}")

    print(
        classification_report(
            y_actual,
            predictions,
            target_names=["Safe", "Unsafe"],
            digits=4
        )
    )

print("\nV6 evaluation completed.")