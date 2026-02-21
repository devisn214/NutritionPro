import csv
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

def load_genes():
    path = os.path.join(DATA_DIR, "genes.csv")
    genes = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            genes.append(row["full_name"])
    return sorted(set(genes))

def load_biomarkers():
    path = os.path.join(DATA_DIR, "biomarkers.csv")
    biomarkers = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            biomarkers.append(row["name"])
    return sorted(set(biomarkers))
