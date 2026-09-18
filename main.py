import difflib
import io
import re
from typing import List, Optional
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract

app = FastAPI(title="MediSafe Backend API", version="1.0.0")

# Enable CORS for GitHub Pages
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows requests from your GitHub Pages domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────────────────────────────────────
MEDS = [
    {"id": "dolo", "brand": "Dolo 650", "gen": "Paracetamol 650 mg", "cls": "analgesic", "use": "Fever and body pain", "rx": False, "mrp": 32, "jan": 12, "para": 650, "when": ["morning", "night"], "food": "any", "note": "Never cross 4000 mg of paracetamol in 24 hours from all sources put together."},
    {"id": "crocin", "brand": "Crocin Advance", "gen": "Paracetamol 500 mg", "cls": "analgesic", "use": "Fever and mild pain", "rx": False, "mrp": 30, "jan": 11, "para": 500, "when": ["morning", "night"], "food": "any"},
    {"id": "combi", "brand": "Combiflam", "gen": "Ibuprofen 400 + Paracetamol 325", "cls": "nsaid", "use": "Pain with swelling", "rx": False, "mrp": 48, "jan": 19, "para": 325, "nsaid": True, "when": ["morning", "night"], "food": "after", "note": "Contains paracetamol as well — count it towards your daily limit."},
    {"id": "brufen", "brand": "Brufen 400", "gen": "Ibuprofen 400 mg", "cls": "nsaid", "use": "Pain, swelling, period pain", "rx": False, "mrp": 45, "jan": 18, "nsaid": True, "when": ["morning", "night"], "food": "after"},
    {"id": "ecosprin", "brand": "Ecosprin 75", "gen": "Aspirin 75 mg", "cls": "antiplatelet", "use": "Thins blood after a heart problem", "rx": True, "mrp": 12, "jan": 5, "when": ["night"], "food": "after"},
    {"id": "disprin", "brand": "Disprin", "gen": "Aspirin 325 mg", "cls": "nsaid", "use": "Headache and fever", "rx": False, "mrp": 15, "jan": 6, "nsaid": True, "when": ["morning"], "food": "after"},
    {"id": "augmentin", "brand": "Augmentin 625", "gen": "Amoxicillin 500 + Clavulanate 125", "cls": "antibiotic", "abx": True, "family": "penicillin", "use": "Bacterial infection", "rx": True, "mrp": 210, "jan": 84, "when": ["morning", "night"], "food": "after", "course": 5},
    {"id": "azithral", "brand": "Azithral 500", "gen": "Azithromycin 500 mg", "cls": "antibiotic", "abx": True, "family": "macrolide", "use": "Chest and throat infection", "rx": True, "mrp": 112, "jan": 45, "when": ["morning"], "food": "any", "course": 3},
    {"id": "ciplox", "brand": "Ciplox 500", "gen": "Ciprofloxacin 500 mg", "cls": "antibiotic", "abx": True, "family": "fluoroquinolone", "use": "Urine and gut infection", "rx": True, "mrp": 88, "jan": 35, "when": ["morning", "night"], "food": "after", "course": 5},
    {"id": "cefixime", "brand": "Monocef-O 200", "gen": "Cefixime 200 mg", "cls": "antibiotic", "abx": True, "family": "cephalosporin", "use": "Typhoid, throat, urine infection", "rx": True, "mrp": 135, "jan": 54, "when": ["morning", "night"], "food": "after", "course": 5},
    {"id": "flagyl", "brand": "Flagyl 400", "gen": "Metronidazole 400 mg", "cls": "antibiotic", "abx": True, "family": "nitroimidazole", "use": "Loose motions, dental infection", "rx": True, "mrp": 38, "jan": 15, "when": ["morning", "afternoon", "night"], "food": "after", "course": 5},
    {"id": "pan", "brand": "Pan 40", "gen": "Pantoprazole 40 mg", "cls": "acid", "use": "Acidity and stomach protection", "rx": True, "mrp": 95, "jan": 38, "when": ["empty"], "food": "before"},
    {"id": "omez", "brand": "Omez 20", "gen": "Omeprazole 20 mg", "cls": "acid", "use": "Acidity and reflux", "rx": False, "mrp": 72, "jan": 29, "when": ["empty"], "food": "before"},
    {"id": "digene", "brand": "Digene", "gen": "Antacid gel with simethicone", "cls": "antacid", "use": "Quick relief from gas and burning", "rx": False, "mrp": 95, "jan": 40, "when": ["night"], "food": "after"},
    {"id": "cetzine", "brand": "Cetzine 10", "gen": "Cetirizine 10 mg", "cls": "antihistamine", "sedating": True, "use": "Allergy, sneezing, itching", "rx": False, "mrp": 28, "jan": 10, "when": ["night"], "food": "any"},
    {"id": "montair", "brand": "Montair-LC", "gen": "Montelukast 10 + Levocetirizine 5", "cls": "antihistamine", "sedating": True, "use": "Allergy and allergic asthma", "rx": True, "mrp": 185, "jan": 74, "when": ["night"], "food": "any"},
    {"id": "sinarest", "brand": "Sinarest", "gen": "Paracetamol 500 + Phenylephrine + CPM", "cls": "cold", "sedating": True, "use": "Cold, blocked nose, fever", "rx": False, "mrp": 58, "jan": 23, "para": 500, "when": ["morning", "night"], "food": "after"},
    {"id": "glycomet", "brand": "Glycomet 500", "gen": "Metformin 500 mg", "cls": "diabetes", "use": "Type 2 diabetes", "rx": True, "mrp": 42, "jan": 17, "when": ["morning", "night"], "food": "after"},
    {"id": "amaryl", "brand": "Amaryl 2", "gen": "Glimepiride 2 mg", "cls": "diabetes", "hypo": True, "use": "Type 2 diabetes", "rx": True, "mrp": 118, "jan": 47, "when": ["morning"], "food": "before"},
    {"id": "telma", "brand": "Telma 40", "gen": "Telmisartan 40 mg", "cls": "bp", "arb": True, "use": "High blood pressure", "rx": True, "mrp": 128, "jan": 51, "when": ["morning"], "food": "any"},
    {"id": "losar", "brand": "Losar 50", "gen": "Losartan 50 mg", "cls": "bp", "arb": True, "use": "High blood pressure", "rx": True, "mrp": 98, "jan": 39, "when": ["morning"], "food": "any"},
    {"id": "amlong", "brand": "Amlong 5", "gen": "Amlodipine 5 mg", "cls": "bp", "use": "High blood pressure", "rx": True, "mrp": 56, "jan": 22, "when": ["night"], "food": "any"},
    {"id": "metolar", "brand": "Metolar 50", "gen": "Metoprolol 50 mg", "cls": "bp", "beta": True, "use": "Blood pressure and heart rate", "rx": True, "mrp": 74, "jan": 30, "when": ["morning", "night"], "food": "after"},
    {"id": "atorva", "brand": "Atorva 10", "gen": "Atorvastatin 10 mg", "cls": "statin", "use": "Lowers cholesterol", "rx": True, "mrp": 88, "jan": 35, "when": ["night"], "food": "any"},
    {"id": "rosuvas", "brand": "Rosuvas 10", "gen": "Rosuvastatin 10 mg", "cls": "statin", "use": "Lowers cholesterol", "rx": True, "mrp": 142, "jan": 57, "when": ["night"], "food": "any"},
    {"id": "clopilet", "brand": "Clopilet 75", "gen": "Clopidogrel 75 mg", "cls": "antiplatelet", "use": "Prevents clots after a stent or stroke", "rx": True, "mrp": 98, "jan": 39, "when": ["morning"], "food": "any"},
    {"id": "warf", "brand": "Warf 5", "gen": "Warfarin 5 mg", "cls": "blood-thinner", "use": "Strong blood thinner", "rx": True, "mrp": 65, "jan": 26, "when": ["night"], "food": "any"},
    {"id": "eltroxin", "brand": "Eltroxin 50", "gen": "Levothyroxine 50 mcg", "cls": "thyroid", "use": "Underactive thyroid", "rx": True, "mrp": 118, "jan": 47, "when": ["empty"], "food": "before"},
    {"id": "alprax", "brand": "Alprax 0.25", "gen": "Alprazolam 0.25 mg", "cls": "sedative", "sedating": True, "use": "Anxiety and sleeplessness", "rx": True, "mrp": 35, "jan": 14, "when": ["night"], "food": "any"},
    {"id": "ultracet", "brand": "Ultracet", "gen": "Tramadol 37.5 + Paracetamol 325", "cls": "opioid", "sedating": True, "para": 325, "use": "Strong pain", "rx": True, "mrp": 165, "jan": 66, "when": ["morning", "night"], "food": "after"},
    {"id": "omnacortil", "brand": "Omnacortil 10", "gen": "Prednisolone 10 mg", "cls": "steroid", "use": "Heavy inflammation", "rx": True, "mrp": 48, "jan": 19, "when": ["morning"], "food": "after"},
    {"id": "shelcal", "brand": "Shelcal 500", "gen": "Calcium 500 + Vitamin D3", "cls": "supplement", "cal": True, "use": "Bone strength", "rx": False, "mrp": 110, "jan": 44, "when": ["night"], "food": "after"},
    {"id": "zincovit", "brand": "Zincovit", "gen": "Multivitamin with zinc", "cls": "supplement", "use": "General supplement", "rx": False, "mrp": 105, "jan": 42, "when": ["morning"], "food": "after"}
]

PAIRS = [
    {"a": "warf", "b": "ecosprin", "sev": "high", "t": "Warfarin with aspirin", "why": "Both thin blood by different routes. Bleeding risk rises sharply.", "do": "Do not take both unless explicitly monitored with INR."},
    {"a": "warf", "b": "brufen", "sev": "high", "t": "Warfarin with ibuprofen", "why": "Ibuprofen irritates stomach lining while warfarin prevents clotting.", "do": "Use paracetamol for pain instead."},
    {"a": "warf", "b": "combi", "sev": "high", "t": "Warfarin with Combiflam", "why": "Combiflam contains ibuprofen, which sharply raises bleeding risk.", "do": "Switch to plain paracetamol."},
    {"a": "warf", "b": "flagyl", "sev": "high", "t": "Warfarin with metronidazole", "why": "Metronidazole slows liver clearance of warfarin.", "do": "INR must be tested during antibiotic course."},
    {"a": "clopilet", "b": "omez", "sev": "high", "t": "Clopidogrel with omeprazole", "why": "Omeprazole blocks the liver enzyme activating clopidogrel.", "do": "Ask if pantoprazole can replace omeprazole."},
    {"a": "brufen", "b": "omnacortil", "sev": "high", "t": "Ibuprofen with prednisolone", "why": "Stripped stomach lining + steroid creates severe bleeding ulcer risk.", "do": "Requires stomach protection."},
    {"a": "disprin", "b": "omnacortil", "sev": "high", "t": "Aspirin with prednisolone", "why": "Sharply raises stomach ulcer risk.", "do": "Consult doctor for stomach protection."},
    {"a": "ciplox", "b": "shelcal", "sev": "mid", "t": "Ciprofloxacin with calcium", "why": "Calcium chelates the antibiotic in the gut, blocking absorption.", "do": "Keep a 2-hour gap before and 6-hour gap after the antibiotic."},
    {"a": "eltroxin", "b": "shelcal", "sev": "mid", "t": "Thyroid tablet with calcium", "why": "Calcium blocks thyroid hormone absorption.", "do": "Thyroid tablet in the morning, calcium at night."}
]

# ─────────────────────────────────────────────────────────────────────────────
# MODELS
# ─────────────────────────────────────────────────────────────────────────────
class CheckRequest(BaseModel):
    meds: List[str]
    conditions: Optional[List[str]] = []
    allergies: Optional[List[str]] = []
    age: Optional[int] = 0

# ─────────────────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────
def get_med_by_id(med_id: str):
    return next((m for m in MEDS if m["id"] == med_id), None)

def preprocess_image(img: Image.Image) -> Image.Image:
    """Preprocess image to maximize OCR accuracy on handwriting/printed slips."""
    img = img.convert("L")  # Grayscale
    img = ImageEnhance.Contrast(img).enhance(2.0)  # Enhance contrast
    img = img.filter(ImageFilter.SHARPEN)  # Sharpen
    # Simple binary thresholding
    threshold = 140
    img = img.point(lambda p: 255 if p > threshold else 0)
    return img

def match_medicines_from_text(raw_text: str):
    """Fuzzy-matches scanned tokens against known medicine brand/salt names."""
    tokens = re.findall(r"[A-Za-z0-9\-]+", raw_text)
    matched_ids = set()
    matches_detail = []

    for med in MEDS:
        brand_clean = med["brand"].lower().split()[0]
        gen_words = [w.lower() for w in re.findall(r"[A-Za-z]+", med["gen"])]

        best_score = 0.0
        best_token = ""

        for token in tokens:
            t = token.lower()
            if len(t) < 3:
                continue

            # Check similarity with brand name
            ratio_brand = difflib.SequenceMatcher(None, t, brand_clean).ratio()
            if ratio_brand > best_score:
                best_score = ratio_brand
                best_token = token

            # Check similarity with generic names
            for gw in gen_words:
                if len(gw) >= 4:
                    ratio_gen = difflib.SequenceMatcher(None, t, gw).ratio()
                    if ratio_gen > best_score:
                        best_score = ratio_gen
                        best_token = token

        # Threshold for OCR spelling errors (78% match)
        if best_score >= 0.78:
            matched_ids.add(med["id"])
            matches_detail.append({
                "id": med["id"],
                "brand": med["brand"],
                "matched_token": best_token,
                "confidence": round(best_score * 100, 1)
            })

    return list(matched_ids), matches_detail

# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {"status": "ok", "app": "MediSafe Backend running"}

@app.get("/api/meds")
def list_medicines(q: Optional[str] = ""):
    """Returns database medicines, optionally filtered by search query."""
    if not q:
        return MEDS
    term = q.strip().lower()
    return [
        m for m in MEDS
        if term in f"{m['brand']} {m['gen']} {m['use']} {m['cls']}".lower()
    ]

@app.post("/api/scan")
async def scan_prescription(file: UploadFile = File(...)):
    """Receives prescription image, performs OCR, and fuzzy matches medicines."""
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Uploaded file is not an image.")

    contents = await file.read()
    image = Image.open(io.BytesIO(contents))
    processed = preprocess_image(image)

    # Run Tesseract OCR (config: assume single uniform block of text)
    extracted_text = pytesseract.image_to_string(processed, config="--psm 6")
    matched_ids, details = match_medicines_from_text(extracted_text)

    return {
        "success": True,
        "extracted_text": extracted_text.strip(),
        "detected_ids": matched_ids,
        "matches": details
    }

@app.post("/api/check")
def check_safety(payload: CheckRequest):
    """Checks selected medicines for drug-drug, condition, and dosage clashes."""
    selected_meds = [get_med_by_id(mid) for mid in payload.meds if get_med_by_id(mid)]
    findings = []

    # 1. Pairwise drug interactions
    for p in PAIRS:
        if p["a"] in payload.meds and p["b"] in payload.meds:
            findings.append({
                "sev": p["sev"],
                "title": p["t"],
                "why": p["why"],
                "action": p["do"],
                "kind": "Interaction",
                "pair": [get_med_by_id(p["a"])["brand"], get_med_by_id(p["b"])["brand"]]
            })

    # 2. Cumulative Paracetamol check
    paras = [m for m in selected_meds if m.get("para")]
    if len(paras) > 1:
        total_para = sum(m["para"] * 2 for m in paras)
        findings.append({
            "sev": "high" if total_para > 4000 else "mid",
            "title": f"{len(paras)} medicines contain paracetamol",
            "why": f"Total estimated daily dose is {total_para} mg against 4000 mg ceiling.",
            "action": "Avoid taking duplicate paracetamol products.",
            "kind": "Duplicate",
            "pair": [m["brand"] for m in paras]
        })

    # 3. Duplicate NSAID check
    nsaids = [m for m in selected_meds if m.get("nsaid")]
    if len(nsaids) > 1:
        findings.append({
            "sev": "high",
            "title": f"{len(nsaids)} painkillers of the same NSAID class",
            "why": "Taking multiple NSAIDs multiplies gastric ulcer and kidney risks without added relief.",
            "action": "Keep only one painkiller and consult doctor.",
            "kind": "Duplicate",
            "pair": [m["brand"] for m in nsaids]
        })

    return {
        "count": len(selected_meds),
        "findings": findings,
        "is_safe": len([f for f in findings if f["sev"] == "high"]) == 0
    }