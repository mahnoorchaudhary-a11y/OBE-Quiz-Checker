import io
import re
import math
import textwrap
from typing import List, Dict, Tuple, Optional

import streamlit as st
import pandas as pd


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="OBE Quiz Checker",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# CONSTANTS
# ============================================================

ATTAINMENT = 75

WEIGHTS = {
    "CLO Alignment": 25,
    "PLO Alignment": 15,
    "Bloom": 15,
    "Subject Relevance": 15,
    "Clarity": 15,
    "Measurability": 15,
}

BLOOM_LEVELS = {
    "remember": 1,
    "recall": 1,
    "define": 1,
    "identify": 1,
    "list": 1,
    "name": 1,
    "state": 1,

    "understand": 2,
    "describe": 2,
    "explain": 2,
    "summarize": 2,
    "discuss": 2,
    "interpret": 2,
    "classify": 2,

    "apply": 3,
    "calculate": 3,
    "solve": 3,
    "demonstrate": 3,
    "use": 3,
    "implement": 3,
    "execute": 3,

    "analyze": 4,
    "analyse": 4,
    "compare": 4,
    "contrast": 4,
    "differentiate": 4,
    "examine": 4,
    "investigate": 4,
    "categorize": 4,

    "evaluate": 5,
    "assess": 5,
    "judge": 5,
    "critique": 5,
    "justify": 5,
    "defend": 5,
    "recommend": 5,

    "create": 6,
    "design": 6,
    "develop": 6,
    "construct": 6,
    "formulate": 6,
    "produce": 6,
    "propose": 6,
}

QUESTION_STARTERS = [
    "what",
    "why",
    "how",
    "which",
    "who",
    "when",
    "where",
    "define",
    "explain",
    "describe",
    "discuss",
    "identify",
    "calculate",
    "solve",
    "analyze",
    "analyse",
    "compare",
    "evaluate",
    "assess",
    "design",
    "develop",
    "apply",
    "demonstrate",
    "justify",
    "recommend",
    "differentiate",
    "examine",
    "interpret",
]

GENERIC_LINES = {
    "answer the following",
    "answer the questions",
    "attempt all questions",
    "read the following",
    "write your answer",
    "solve the following",
    "question",
}


# ============================================================
# SESSION STATE
# ============================================================

def initialize_state():
    defaults = {
        "analysis_done": False,
        "analysis_results": [],
        "uploaded_text": "",
        "extraction_method": "",
        "last_file_name": "",
        "overall_score": None,
        "overall_status": "Not Analyzed",
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


initialize_state()


# ============================================================
# BASIC TEXT UTILITIES
# ============================================================

def clean_text(text: str) -> str:
    if not text:
        return ""

    text = text.replace("\x00", " ")
    text = text.replace("\u00a0", " ")
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def tokenize(text: str) -> List[str]:
    words = re.findall(r"[a-zA-Z0-9]+", text.lower())

    stop_words = {
        "the", "a", "an", "and", "or", "of", "to", "in", "on",
        "for", "with", "by", "from", "is", "are", "was", "were",
        "be", "been", "being", "as", "at", "that", "this", "these",
        "those", "it", "its", "their", "they", "them", "he", "she",
        "his", "her", "you", "your", "we", "our", "will", "can",
        "may", "should", "must", "into", "through", "using"
    }

    return [
        w for w in words
        if len(w) > 2 and w not in stop_words
    ]


def unique_words(text: str) -> set:
    return set(tokenize(text))


def overlap_score(text_a: str, text_b: str) -> float:
    """
    Evidence-based lexical overlap score.
    Returns 0-100.
    """
    a = unique_words(text_a)
    b = unique_words(text_b)

    if not a or not b:
        return 0.0

    intersection = a.intersection(b)

    # Dice-like similarity, slightly lenient for natural language.
    score = (2 * len(intersection) / (len(a) + len(b))) * 100

    return round(min(100.0, score), 1)


# ============================================================
# FILE READING
# ============================================================

def read_pdf(uploaded_file):
    raw = uploaded_file.getvalue()

    if not raw:
        return "", "The uploaded PDF is empty."

    # Method 1: PyMuPDF
    try:
        import fitz

        pdf = fitz.open(stream=raw, filetype="pdf")
        pages = []

        for page_number in range(len(pdf)):
            try:
                page = pdf.load_page(page_number)
                text = page.get_text("text", sort=True)

                if text:
                    pages.append(text)
            except Exception:
                continue

        pdf.close()

        combined = clean_text("\n".join(pages))

        if len(combined) >= 30:
            return combined, "PyMuPDF"
    except Exception:
        pass

    # Method 2: pypdf
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(raw))
        pages = []

        for page in reader.pages:
            try:
                text = page.extract_text()

                if text:
                    pages.append(text)
            except Exception:
                continue

        combined = clean_text("\n".join(pages))

        if len(combined) >= 30:
            return combined, "pypdf"
    except Exception:
        pass

    # Method 3: pdfplumber
    try:
        import pdfplumber

        pages = []

        with pdfplumber.open(io.BytesIO(raw)) as pdf:
            for page in pdf.pages:
                try:
                    text = page.extract_text(
                        x_tolerance=2,
                        y_tolerance=3
                    )

                    if text:
                        pages.append(text)
                except Exception:
                    continue

        combined = clean_text("\n".join(pages))

        if len(combined) >= 30:
            return combined, "pdfplumber"
    except Exception:
        pass

    # Method 4: OCR
    try:
        import fitz
        from PIL import Image
        import pytesseract

        pdf = fitz.open(stream=raw, filetype="pdf")
        ocr_pages = []

        for page_number in range(len(pdf)):
            try:
                page = pdf.load_page(page_number)

                pix = page.get_pixmap(
                    matrix=fitz.Matrix(2.0, 2.0),
                    alpha=False
                )

                image_bytes = pix.tobytes("png")
                image = Image.open(io.BytesIO(image_bytes))

                text = pytesseract.image_to_string(
                    image,
                    config="--psm 6"
                )

                if text:
                    ocr_pages.append(text)

            except Exception:
                continue

        pdf.close()

        combined = clean_text("\n".join(ocr_pages))

        if len(combined) >= 30:
            return combined, "OCR"
    except Exception:
        pass

    return "", (
        "No readable text was extracted from this PDF. "
        "If it is a scanned PDF, install Tesseract OCR using packages.txt."
    )


def read_docx(uploaded_file):
    try:
        from docx import Document

        document = Document(
            io.BytesIO(uploaded_file.getvalue())
        )

        parts = []

        for paragraph in document.paragraphs:
            if paragraph.text.strip():
                parts.append(paragraph.text)

        for table in document.tables:
            for row in table.rows:
                cells = []

                for cell in row.cells:
                    if cell.text.strip():
                        cells.append(cell.text.strip())

                if cells:
                    parts.append(" | ".join(cells))

        text = clean_text("\n".join(parts))

        if len(text) < 20:
            return "", "DOCX contains insufficient readable text."

        return text, "DOCX"
    except Exception as exc:
        return "", f"DOCX reading error: {exc}"


def read_pptx(uploaded_file):
    try:
        from pptx import Presentation

        presentation = Presentation(
            io.BytesIO(uploaded_file.getvalue())
        )

        parts = []

        for slide in presentation.slides:
            for shape in slide.shapes:
                if hasattr(shape, "text"):
                    value = shape.text.strip()

                    if value:
                        parts.append(value)

        text = clean_text("\n".join(parts))

        if len(text) < 20:
            return "", "PPTX contains insufficient readable text."

        return text, "PPTX"
    except Exception as exc:
        return "", f"PPTX reading error: {exc}"


def read_excel(uploaded_file):
    try:
        excel = pd.ExcelFile(
            io.BytesIO(uploaded_file.getvalue())
        )

        parts = []

        for sheet in excel.sheet_names:
            try:
                df = pd.read_excel(
                    io.BytesIO(uploaded_file.getvalue()),
                    sheet_name=sheet,
                    header=None
                )

                parts.append(f"Sheet: {sheet}")

                for row in df.fillna("").astype(str).values.tolist():
                    row_text = " | ".join(
                        cell.strip()
                        for cell in row
                        if cell.strip()
                    )

                    if row_text:
                        parts.append(row_text)

            except Exception:
                continue

        text = clean_text("\n".join(parts))

        if len(text) < 20:
            return "", "Excel file contains insufficient readable text."

        return text, "Excel"
    except Exception as exc:
        return "", f"Excel reading error: {exc}"


def read_csv(uploaded_file):
    try:
        df = pd.read_csv(
            io.BytesIO(uploaded_file.getvalue()),
            header=None
        )

        parts = []

        for row in df.fillna("").astype(str).values.tolist():
            row_text = " | ".join(
                cell.strip()
                for cell in row
                if cell.strip()
            )

            if row_text:
                parts.append(row_text)

        text = clean_text("\n".join(parts))

        if len(text) < 20:
            return "", "CSV contains insufficient readable text."

        return text, "CSV"
    except Exception as exc:
        return "", f"CSV reading error: {exc}"


def read_plain_text(uploaded_file):
    try:
        raw = uploaded_file.getvalue()

        for encoding in ["utf-8", "utf-8-sig", "cp1252", "latin-1"]:
            try:
                text = raw.decode(encoding)
                text = clean_text(text)

                if len(text) >= 20:
                    return text, "Text"
            except Exception:
                continue

        return "", "Text file could not be decoded."
    except Exception as exc:
        return "", f"Text reading error: {exc}"


def read_image(uploaded_file):
    try:
        from PIL import Image
        import pytesseract

        image = Image.open(
            io.BytesIO(uploaded_file.getvalue())
        )

        text = pytesseract.image_to_string(
            image,
            config="--psm 6"
        )

        text = clean_text(text)

        if len(text) < 20:
            return "", "Image OCR did not produce enough readable text."

        return text, "OCR"
    except Exception as exc:
        return "", (
            "Image OCR failed. Make sure pytesseract and "
            "Tesseract OCR are installed. "
            f"Details: {exc}"
        )


def read_uploaded_file(uploaded_file):
    filename = uploaded_file.name.lower()

    if filename.endswith(".pdf"):
        return read_pdf(uploaded_file)

    if filename.endswith(".docx"):
        return read_docx(uploaded_file)

    if filename.endswith(".pptx"):
        return read_pptx(uploaded_file)

    if filename.endswith((".xlsx", ".xls", ".xlsm")):
        return read_excel(uploaded_file)

    if filename.endswith(".csv"):
        return read_csv(uploaded_file)

    if filename.endswith(
        (".txt", ".md", ".rtf")
    ):
        return read_plain_text(uploaded_file)

    if filename.endswith(
        (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff")
    ):
        return read_image(uploaded_file)

    return "", (
        "Unsupported file type. "
        "Upload PDF, DOCX, PPTX, XLSX, XLS, CSV, TXT, "
        "MD, RTF, PNG, JPG, JPEG, WEBP, BMP or TIFF."
    )


# ============================================================
# QUESTION EXTRACTION
# ============================================================

def clean_question_candidate(text: str) -> str:
    text = clean_text(text)

    text = re.sub(
        r"^(question\s*)?\d+\s*[\.\):\-]\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"^q\s*\d+\s*[\.\):\-]\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"^question\s+\d+\s*[:\.\)\-]\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    return text.strip()


def looks_like_question(text: str) -> bool:
    if not text:
        return False

    normalized = normalize_text(text)

    if len(normalized) < 8:
        return False

    if normalized in GENERIC_LINES:
        return False

    if len(text.split()) < 3:
        return False

    if "?" in text:
        return True

    first_word = normalized.split()[0] if normalized.split() else ""

    if first_word in QUESTION_STARTERS:
        return True

    if re.match(
        r"^(define|explain|describe|discuss|calculate|solve|"
        r"analyze|analyse|compare|evaluate|identify|state|"
        r"design|develop|apply|demonstrate|justify|recommend)\b",
        normalized
    ):
        return True

    return False


def split_numbered_questions(text: str) -> List[str]:
    patterns = [
        r"(?im)(?=^\s*(?:question\s*)?\d+\s*[\.\):\-])",
        r"(?im)(?=^\s*q\s*\d+\s*[\.\):\-])",
    ]

    best = []

    for pattern in patterns:
        pieces = re.split(pattern, text)

        candidates = []

        for piece in pieces:
            piece = clean_question_candidate(piece)

            if looks_like_question(piece):
                candidates.append(piece)

        if len(candidates) > len(best):
            best = candidates

    return best


def split_question_marks(text: str) -> List[str]:
    parts = re.split(
        r"(?<=[?])\s+",
        text
    )

    candidates = []

    for part in parts:
        part = clean_question_candidate(part)

        if looks_like_question(part):
            candidates.append(part)

    return candidates


def split_question_lines(text: str) -> List[str]:
    lines = [
        clean_question_candidate(line)
        for line in text.splitlines()
    ]

    candidates = []

    for line in lines:
        if looks_like_question(line):
            candidates.append(line)

    return candidates


def fallback_paragraphs(text: str) -> List[str]:
    paragraphs = re.split(
        r"\n\s*\n",
        text
    )

    candidates = []

    for paragraph in paragraphs:
        paragraph = clean_question_candidate(paragraph)

        if len(paragraph.split()) >= 5:
            candidates.append(paragraph)

    return candidates


def extract_questions(text: str) -> List[Dict]:
    text = clean_text(text)

    if not text:
        return []

    all_candidates = []

    # First try numbered questions.
    numbered = split_numbered_questions(text)

    if numbered:
        all_candidates.extend(numbered)

    # Then question marks.
    if len(all_candidates) < 2:
        all_candidates.extend(
            split_question_marks(text)
        )

    # Then question-like lines.
    if len(all_candidates) < 2:
        all_candidates.extend(
            split_question_lines(text)
        )

    # Last fallback.
    if len(all_candidates) < 2:
        all_candidates.extend(
            fallback_paragraphs(text)
        )

    # Remove duplicates.
    unique = []
    seen = set()

    for candidate in all_candidates:
        candidate = clean_text(candidate)

        if not candidate:
            continue

        normalized = normalize_text(candidate)

        if normalized in seen:
            continue

        seen.add(normalized)
        unique.append(candidate)

    # Limit absurdly large extraction.
    unique = unique[:100]

    results = []

    for index, question in enumerate(unique, start=1):
        results.append(
            {
                "number": index,
                "text": question,
            }
        )

    return results


# ============================================================
# LEARNING OUTCOME PARSING
# ============================================================

def parse_outcomes(raw_text: str) -> List[str]:
    if not raw_text:
        return []

    lines = []

    for line in raw_text.splitlines():
        line = line.strip()

        if not line:
            continue

        line = re.sub(
            r"^(CLO|PLO)\s*\d*\s*[:\.\)\-]?\s*",
            "",
            line,
            flags=re.IGNORECASE
        )

        line = re.sub(
            r"^\d+\s*[\.\)\-:]\s*",
            "",
            line
        )

        if len(line.split()) >= 3:
            lines.append(line.strip())

    if not lines:
        chunks = re.split(
            r"[;\n]+",
            raw_text
        )

        lines = [
            clean_text(x)
            for x in chunks
            if len(x.split()) >= 3
        ]

    return lines[:20]


# ============================================================
# BLOOM ANALYSIS
# ============================================================

def detect_bloom(question: str) -> Tuple[str, int]:
    normalized = normalize_text(question)
    words = normalized.split()

    detected = []

    for word in words:
        if word in BLOOM_LEVELS:
            detected.append(
                (word, BLOOM_LEVELS[word])
            )

    if not detected:
        if "why" in words or "how" in words:
            return "Understand", 2

        if "?" in question:
            return "Understand", 2

        return "Understand", 2

    # Highest explicit cognitive demand is used.
    highest = max(
        detected,
        key=lambda x: x[1]
    )

    word, level = highest

    names = {
        1: "Remember",
        2: "Understand",
        3: "Apply",
        4: "Analyze",
        5: "Evaluate",
        6: "Create",
    }

    return names[level], level


def target_bloom_from_outcomes(
    clo_text: str,
    plo_text: str
) -> Tuple[str, int]:
    combined = f"{clo_text} {plo_text}"

    return detect_bloom(combined)


def bloom_score(question_level: int, target_level: int) -> float:
    difference = abs(
        question_level - target_level
    )

    if difference == 0:
        return 100.0

    if difference == 1:
        return 90.0

    if difference == 2:
        return 80.0

    if difference == 3:
        return 70.0

    return 60.0


# ============================================================
# CLO / PLO SCORING
# ============================================================

def outcome_alignment_score(
    question: str,
    outcomes: List[str]
) -> Tuple[Optional[float], str, str]:

    if not outcomes:
        return None, "", ""

    best_score = 0.0
    best_outcome = ""

    for outcome in outcomes:
        score = overlap_score(
            question,
            outcome
        )

        if score > best_score:
            best_score = score
            best_outcome = outcome

    # More realistic interpretation of lexical overlap.
    if best_score >= 55:
        realistic = 95.0
    elif best_score >= 42:
        realistic = 88.0
    elif best_score >= 30:
        realistic = 78.0
    elif best_score >= 20:
        realistic = 68.0
    elif best_score >= 10:
        realistic = 58.0
    elif best_score > 0:
        realistic = 48.0
    else:
        realistic = 35.0

    return realistic, best_outcome, f"{best_score:.0f}% keyword/concept overlap"


# ============================================================
# SUBJECT / QUESTION QUALITY
# ============================================================

def subject_relevance_score(
    question: str,
    course: str,
    clo_text: str,
    plo_text: str
) -> float:

    reference = (
        f"{course} {clo_text} {plo_text}"
    ).strip()

    if not reference:
        return 70.0

    overlap = overlap_score(
        question,
        reference
    )

    if overlap >= 45:
        return 95.0

    if overlap >= 30:
        return 88.0

    if overlap >= 20:
        return 80.0

    if overlap >= 10:
        return 72.0

    return 60.0


def clarity_score(question: str) -> float:
    words = question.split()

    if not words:
        return 0.0

    score = 85.0

    if len(words) < 5:
        score -= 15

    if len(words) > 80:
        score -= 10

    if question.count("?") > 2:
        score -= 8

    if re.search(
        r"\b(etc|and so on|something|anything)\b",
        question,
        flags=re.IGNORECASE
    ):
        score -= 8

    if re.search(
        r"\b(what is|define|calculate|explain|"
        r"describe|analyze|analyse|compare|evaluate|"
        r"identify|design|develop|justify|recommend)\b",
        question,
        flags=re.IGNORECASE
    ):
        score += 8

    return max(
        40.0,
        min(100.0, score)
    )


def measurability_score(question: str) -> float:
    score = 78.0

    measurable_verbs = [
        "define",
        "identify",
        "calculate",
        "solve",
        "explain",
        "describe",
        "compare",
        "analyze",
        "analyse",
        "evaluate",
        "justify",
        "design",
        "develop",
        "recommend",
        "list",
        "state",
        "classify",
        "differentiate",
    ]

    normalized = normalize_text(question)

    if any(
        word in normalized.split()
        for word in measurable_verbs
    ):
        score += 12

    if "?" in question:
        score += 5

    if re.search(
        r"\b(discuss|comment on|write about)\b",
        normalized
    ):
        score -= 8

    if len(question.split()) > 100:
        score -= 8

    return max(
        45.0,
        min(100.0, score)
    )


# ============================================================
# QUESTION TYPE
# ============================================================

def detect_question_type(question: str) -> str:
    normalized = question.lower()

    if re.search(
        r"\b(a\)|b\)|c\)|d\)|option|choose one)\b",
        normalized
    ):
        return "MCQ"

    if "true or false" in normalized:
        return "True / False"

    if "match the following" in normalized:
        return "Matching"

    if re.search(
        r"\b(fill in the blank|fill in the blanks)\b",
        normalized
    ):
        return "Fill in the Blank"

    if re.search(
        r"\b(case|scenario|situation|given the following)\b",
        normalized
    ):
        return "Case / Application"

    if re.search(
        r"\b(calculate|compute|solve|find)\b",
        normalized
    ):
        return "Numerical / Problem"

    if re.search(
        r"\b(design|develop|construct|implement|create)\b",
        normalized
    ):
        return "Practical / Design"

    if len(question.split()) > 45:
        return "Essay / Long Answer"

    return "Short Answer"


# ============================================================
# REVISION CONCEPT EXTRACTION
# ============================================================

def extract_core_concepts(outcome: str) -> List[str]:
    if not outcome:
        return []

    text = outcome

    # Remove common outcome framing.
    text = re.sub(
        r"\b(students?|learners?)\b",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"\b(should|will be able to|able to|"
        r"demonstrate the ability to|"
        r"understand|learn|know)\b",
        "",
        text,
        flags=re.IGNORECASE
    )

    # Capture useful noun/concept phrases.
    phrases = []

    comma_parts = re.split(
        r",|;|\band\b|\bor\b",
        text,
        flags=re.IGNORECASE
    )

    for part in comma_parts:
        part = clean_text(part)

        if len(part.split()) >= 2:
            part = re.sub(
                r"^(to|the|a|an)\s+",
                "",
                part,
                flags=re.IGNORECASE
            )

            if len(part.split()) <= 12:
                phrases.append(part)

    # Also preserve the strongest complete outcome if no parts found.
    if not phrases:
        stripped = clean_text(text)

        if stripped:
            phrases.append(stripped)

    # Remove duplicates.
    unique = []
    seen = set()

    for phrase in phrases:
        key = normalize_text(phrase)

        if key and key not in seen:
            seen.add(key)
            unique.append(phrase)

    return unique[:4]


def select_revision_verb(
    outcome: str,
    original_question: str
) -> str:

    normalized = normalize_text(outcome)

    for verb in [
        "evaluate",
        "assess",
        "critique",
        "justify",
        "recommend",
        "design",
        "develop",
        "create",
        "formulate",
        "analyze",
        "analyse",
        "compare",
        "differentiate",
        "apply",
        "calculate",
        "solve",
        "demonstrate",
        "explain",
        "describe",
        "identify",
    ]:
        if verb in normalized.split():
            return verb

    original_bloom, _ = detect_bloom(
        original_question
    )

    if original_bloom == "Remember":
        return "explain"

    if original_bloom == "Understand":
        return "explain"

    if original_bloom == "Apply":
        return "apply"

    if original_bloom == "Analyze":
        return "analyze"

    if original_bloom == "Evaluate":
        return "evaluate"

    return "explain"



# ============================================================
# COMPLETE QUESTION ANALYSIS
# ============================================================

def analyze_question(
    question: str,
    course: str,
    clos: List[str],
    plos: List[str]
) -> Dict:

    bloom_name, bloom_level = detect_bloom(
        question
    )

    best_clo_score, best_clo, clo_evidence = (
        outcome_alignment_score(
            question,
            clos
        )
    )

    best_plo_score, best_plo, plo_evidence = (
        outcome_alignment_score(
            question,
            plos
        )
    )

    subject_score = subject_relevance_score(
        question,
        course,
        best_clo,
        best_plo
    )

    clarity = clarity_score(
        question
    )

    measurability = measurability_score(
        question
    )

    target_text = f"{best_clo} {best_plo}"

    _, target_level = target_bloom_from_outcomes(
        best_clo,
        best_plo
    )

    if not best_clo and not best_plo:
        bloom = 65.0
    else:
        bloom = bloom_score(
            bloom_level,
            target_level
        )

    # Do not calculate an overall alignment if CLO/PLO
    # information is absent.
    if best_clo_score is None or best_plo_score is None:
        overall = None
        status = "Awaiting CLO/PLO"
    else:
        overall = (
            best_clo_score * 0.25
            + best_plo_score * 0.15
            + bloom * 0.15
            + subject_score * 0.15
            + clarity * 0.15
            + measurability * 0.15
        )

        overall = round(
            max(0.0, min(100.0, overall)),
            1
        )

        if overall >= 85:
            status = "Strong"
        elif overall >= ATTAINMENT:
            status = "Attained"
        elif overall >= 60:
            status = "Needs Revision"
        elif overall >= 40:
            status = "Weak"
        else:
            status = "Poor"

    needs_revision = (
        overall is not None
        and (
            best_clo_score < ATTAINMENT
            or best_plo_score < ATTAINMENT
            or bloom < ATTAINMENT
            or subject_score < ATTAINMENT
            or clarity < ATTAINMENT
            or measurability < ATTAINMENT
        )
    )

    return {
        "Question": question,
        "Question Type": detect_question_type(question),
        "CLO Alignment": (
            round(best_clo_score, 1)
            if best_clo_score is not None
            else None
        ),
        "PLO Alignment": (
            round(best_plo_score, 1)
            if best_plo_score is not None
            else None
        ),
        "Bloom": round(bloom, 1),
        "Bloom Level": bloom_name,
        "Subject Relevance": round(subject_score, 1),
        "Clarity": round(clarity, 1),
        "Measurability": round(measurability, 1),
        "Overall": overall,
        "Status": status,
        "Needs Revision": needs_revision,
        "Best CLO": best_clo,
        "Best PLO": best_plo,
        "CLO Evidence": clo_evidence,
        "PLO Evidence": plo_evidence,
        "Problem": problem,
        "Revision Focus": focus,
    }



# ============================================================
# STATUS HELPERS
# ============================================================

def attainment_label(score: Optional[float]) -> str:
    if score is None:
        return "Not Analyzed"

    if score >= 85:
        return "Strong"

    if score >= 75:
        return "Attained"

    if score >= 60:
        return "Needs Revision"

    if score >= 40:
        return "Weak"

    return "Poor"


def status_icon(score: Optional[float]) -> str:
    if score is None:
        return "⏳"

    if score >= 75:
        return "🟢"

    if score >= 60:
        return "🟠"

    return "🔴"


# ============================================================
# OVERALL ASSESSMENT SCORE
# ============================================================

def calculate_overall(results: List[Dict]) -> Optional[float]:
    valid_scores = [
        r["Overall"]
        for r in results
        if r.get("Overall") is not None
    ]

    if not valid_scores:
        return None

    return round(
        sum(valid_scores) / len(valid_scores),
        1
    )


# ============================================================
# PAGE HEADER
# ============================================================

st.title("🎓 OBE Quiz Checker")
st.caption(
    "Evidence-based assessment alignment, scoring and automatic revision"
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.header("Assessment Setup")

    course = st.text_input(
        "Course / Subject",
        placeholder="e.g., Chemistry, English I, Programming"
    )

    assessment_type = st.selectbox(
        "Assessment Type",
        [
            "Quiz",
            "Assignment",
            "Test",
            "Midterm",
            "Final Exam",
            "Class Activity",
            "Other",
        ]
    )

    total_marks = st.number_input(
        "Total Marks",
        min_value=1,
        value=100,
        step=1
    )

    st.divider()

    st.subheader("Attainment Rule")
    st.write(
        "A question or assessment is considered "
        "**Attained at 75% or above**."
    )

    st.caption(
        "Scores are calculated from the actual question, "
        "CLO/PLO evidence, Bloom level, relevance, clarity "
        "and measurability."
    )


# ============================================================
# MAIN INPUTS
# ============================================================

st.header("1. Learning Outcomes")

col1, col2 = st.columns(2)

with col1:
    st.subheader("CLOs")
    clo_text = st.text_area(
        "Enter Course Learning Outcomes",
        placeholder=(
            "CLO 1: Explain the process of photosynthesis "
            "and its importance to plant growth.\n"
            "CLO 2: Analyze factors affecting plant growth."
        ),
        height=180,
        key="clo_input"
    )

with col2:
    st.subheader("PLOs")
    plo_text = st.text_area(
        "Enter Program Learning Outcomes",
        placeholder=(
            "PLO 1: Apply knowledge of scientific principles "
            "to solve discipline-related problems.\n"
            "PLO 2: Analyze problems using appropriate evidence."
        ),
        height=180,
        key="plo_input"
    )


clos = parse_outcomes(
    clo_text
)

plos = parse_outcomes(
    plo_text
)


# ============================================================
# PRE-ANALYSIS STATUS
# ============================================================

st.header("2. Upload Complete Assessment")

uploaded_file = st.file_uploader(
    "Upload the complete assessment",
    type=[
        "pdf",
        "docx",
        "pptx",
        "xlsx",
        "xls",
        "xlsm",
        "csv",
        "txt",
        "md",
        "rtf",
        "png",
        "jpg",
        "jpeg",
        "webp",
        "bmp",
        "tiff",
    ],
    help=(
        "The assessment can contain MCQs, true/false, "
        "short answers, essays, numerical problems, "
        "case studies, matching, fill-in-the-blanks "
        "or practical questions."
    )
)


# ============================================================
# CURRENT INPUT STATUS
# ============================================================

status_col1, status_col2, status_col3 = st.columns(3)

with status_col1:
    if not clos:
        st.info("⏳ CLOs not entered")
    else:
        st.success(f"✓ {len(clos)} CLO(s) entered")

with status_col2:
    if not plos:
        st.info("⏳ PLOs not entered")
    else:
        st.success(f"✓ {len(plos)} PLO(s) entered")

with status_col3:
    if uploaded_file is None:
        st.info("⏳ Assessment not uploaded")
    else:
        st.success("✓ Assessment uploaded")


# ============================================================
# ANALYZE BUTTON
# ============================================================

ready_for_analysis = (
    bool(clos)
    and bool(plos)
    and uploaded_file is not None
)

st.divider()

if not ready_for_analysis:
    st.warning(
        "⏳ Alignment cannot be determined yet. "
        "Enter at least one CLO, one PLO and upload the assessment."
    )

analyze_button = st.button(
    "🔍 Analyze Assessment",
    type="primary",
    use_container_width=True,
    disabled=not ready_for_analysis
)


# ============================================================
# PERFORM ANALYSIS
# ============================================================

if analyze_button:

    with st.spinner(
        "Reading and analyzing the assessment..."
    ):
        text, method = read_uploaded_file(
            uploaded_file
        )

    if not text:
        st.session_state.analysis_done = False
        st.session_state.analysis_results = []
        st.session_state.overall_score = None

        st.error(
            "The file could not be read. "
            "Please check that it contains readable text "
            "or upload a clearer PDF/image."
        )

        st.caption(
            method
        )

    else:
        questions = extract_questions(
            text
        )

        if not questions:
            st.session_state.analysis_done = False
            st.session_state.analysis_results = []
            st.session_state.overall_score = None

            st.error(
                "The file was read successfully, but no "
                "assessment questions could be detected."
            )

            st.info(
                "Try a file with visible question text, "
                "numbered questions, question marks, or "
                "clear question verbs such as Explain, "
                "Calculate, Analyze, Compare or Define."
            )

        else:
            results = []

            for item in questions:
                result = analyze_question(
                    item["text"],
                    course,
                    clos,
                    plos
                )

                result["Number"] = item["number"]

                results.append(
                    result
                )

            st.session_state.analysis_done = True
            st.session_state.analysis_results = results
            st.session_state.uploaded_text = text
            st.session_state.extraction_method = method
            st.session_state.last_file_name = uploaded_file.name

            overall = calculate_overall(
                results
            )

            st.session_state.overall_score = overall

            if overall is not None:
                st.session_state.overall_status = (
                    attainment_label(overall)
                )
            else:
                st.session_state.overall_status = (
                    "Not Analyzed"
                )

            st.success(
                f"Assessment analyzed successfully. "
                f"{len(results)} question(s) detected."
            )


# ============================================================
# RESULTS
# ============================================================

if st.session_state.analysis_done:

    results = st.session_state.analysis_results


    # --------------------------------------------------------
    # OVERALL SCORE
    # --------------------------------------------------------

    overall_score = calculate_overall(
        results
    )

    st.session_state.overall_score = overall_score

    st.header("3. Overall Alignment")

    if overall_score is None:
        st.warning(
            "Alignment cannot be calculated because "
            "the required learning outcomes are missing."
        )
    else:
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "Overall Score",
                f"{overall_score:.1f}%"
            )

        with col2:
            st.metric(
                "Questions",
                len(results)
            )

        with col3:
            attained_count = sum(
                1
                for result in results
                if result.get("Overall") is not None
                and result["Overall"] >= ATTAINMENT
            )

            st.metric(
                "Attained Questions",
                f"{attained_count}/{len(results)}"
            )

        if overall_score >= ATTAINMENT:
            st.success(
                f"🟢 Alignment Attained — "
                f"{overall_score:.1f}%"
            )

            if overall_score >= 80:
                st.balloons()
        else:
            st.warning(
                f"🟠 Alignment Not Yet Attained — "
                f"{overall_score:.1f}%"
            )

    # --------------------------------------------------------
    # QUESTIONS REQUIRING REVIEW
    # --------------------------------------------------------

    revision_items = [
        (index, result)
        for index, result in enumerate(results)
        if result.get("Overall") is not None
        and result["Overall"] < ATTAINMENT
    ]

    if revision_items:

        st.header("4. Questions Requiring Review")

        st.info(
            "The questions below are below the 75% attainment "
            "threshold. Review the identified problem and revision "
            "focus manually. The tool does not generate replacement "
            "questions or question suggestions."
        )

        for index, result in revision_items:

            number = result.get(
                "Number",
                index + 1
            )

            current_score = result["Overall"]

            with st.container(border=True):

                st.subheader(
                    f"Question {number} — "
                    f"{status_icon(current_score)} "
                    f"{current_score:.1f}%"
                )

                st.markdown("**Current Question**")
                st.write(
                    result["Question"]
                )

                st.markdown("**Problem Identified**")
                st.write(
                    result["Problem"]
                )

                st.markdown("**Revision Focus**")
                st.write(
                    result["Revision Focus"]
                )

    else:
        st.header("4. Review Status")

        st.success(
            "🟢 All analyzed questions have attained "
            "the 75% threshold."
        )

    # --------------------------------------------------------
    # ATTAINED QUESTIONS
    # --------------------------------------------------------

    current_results = (
        st.session_state.analysis_results
    )

    attained_items = [
        result
        for result in current_results
        if result.get("Overall") is not None
        and result["Overall"] >= ATTAINMENT
    ]

    if attained_items:

        st.header("5. Attained Questions")

        for result in attained_items:

            number = result.get(
                "Number",
                "?"
            )

            score = result["Overall"]

            with st.container(border=True):

                st.markdown(
                    f"### 🏆 Question {number} — "
                    f"Attained ({score:.1f}%)"
                )

                st.write(
                    result["Question"]
                )

    # --------------------------------------------------------
    # ALIGNMENT OVERVIEW
    # --------------------------------------------------------

    st.header("6. Alignment Overview")

    chart_rows = []

    for result in current_results:

        chart_rows.append(
            {
                "Question": (
                    f"Q{result.get('Number', '?')}"
                ),
                "Score": result.get(
                    "Overall",
                    0
                ),
            }
        )

    if chart_rows:
        chart_df = pd.DataFrame(
            chart_rows
        ).set_index(
            "Question"
        )

        st.bar_chart(
            chart_df,
            y="Score",
            height=350
        )

        st.caption(
            "Attainment threshold: 75%"
        )

    # --------------------------------------------------------
    # QUESTION OVERVIEW
    # --------------------------------------------------------

    st.header("7. Question Overview")

    overview_rows = []

    for result in current_results:

        overview_rows.append(
            {
                "Question": (
                    f"Q{result.get('Number', '?')}"
                ),
                "Type": result.get(
                    "Question Type",
                    ""
                ),
                "CLO": result.get(
                    "CLO Alignment"
                ),
                "PLO": result.get(
                    "PLO Alignment"
                ),
                "Bloom": result.get(
                    "Bloom"
                ),
                "Relevance": result.get(
                    "Subject Relevance"
                ),
                "Clarity": result.get(
                    "Clarity"
                ),
                "Measurability": result.get(
                    "Measurability"
                ),
                "Overall": result.get(
                    "Overall"
                ),
                "Status": (
                    "🏆 Attained"
                    if result.get("Overall") is not None
                    and result["Overall"] >= ATTAINMENT
                    else "🔧 Revision Required"
                ),
            }
        )

    overview_df = pd.DataFrame(
        overview_rows
    )

    st.dataframe(
        overview_df,
        use_container_width=True,
        hide_index=True
    )

    # --------------------------------------------------------
    # DETAILED ANALYSIS
    # --------------------------------------------------------

    st.header("8. Detailed Question Analysis")

    for result in current_results:

        number = result.get(
            "Number",
            "?"
        )

        score = result.get(
            "Overall"
        )

        label = attainment_label(
            score
        )

        with st.expander(
            f"Question {number} — "
            f"{status_icon(score)} "
            f"{score:.1f}% — {label}"
            if score is not None
            else
            f"Question {number} — Not Analyzed"
        ):

            st.markdown("**Question**")
            st.write(
                result["Question"]
            )

            metrics1 = st.columns(3)

            with metrics1[0]:
                st.metric(
                    "CLO Alignment",
                    (
                        f"{result['CLO Alignment']:.1f}%"
                        if result["CLO Alignment"] is not None
                        else "N/A"
                    )
                )

            with metrics1[1]:
                st.metric(
                    "PLO Alignment",
                    (
                        f"{result['PLO Alignment']:.1f}%"
                        if result["PLO Alignment"] is not None
                        else "N/A"
                    )
                )

            with metrics1[2]:
                st.metric(
                    "Bloom",
                    f"{result['Bloom']:.1f}%"
                )

            metrics2 = st.columns(4)

            with metrics2[0]:
                st.metric(
                    "Relevance",
                    f"{result['Subject Relevance']:.1f}%"
                )

            with metrics2[1]:
                st.metric(
                    "Clarity",
                    f"{result['Clarity']:.1f}%"
                )

            with metrics2[2]:
                st.metric(
                    "Measurability",
                    f"{result['Measurability']:.1f}%"
                )

            with metrics2[3]:
                if score is not None:
                    st.metric(
                        "Overall",
                        f"{score:.1f}%"
                    )
                else:
                    st.metric(
                        "Overall",
                        "N/A"
                    )

            st.markdown(
                f"**Bloom Level:** "
                f"{result['Bloom Level']}"
            )

            if result.get("Best CLO"):
                st.markdown(
                    "**Best CLO Match:**"
                )
                st.write(
                    result["Best CLO"]
                )

            if result.get("Best PLO"):
                st.markdown(
                    "**Best PLO Match:**"
                )
                st.write(
                    result["Best PLO"]
                )

            if result.get("CLO Evidence"):
                st.caption(
                    "CLO evidence: "
                    + result["CLO Evidence"]
                )

            if result.get("PLO Evidence"):
                st.caption(
                    "PLO evidence: "
                    + result["PLO Evidence"]
                )

    # --------------------------------------------------------
    # EXPORT
    # --------------------------------------------------------

    st.header("9. Export Results")

    export_rows = []

    for result in current_results:

        export_rows.append(
            {
                "Question Number": result.get(
                    "Number",
                    ""
                ),
                "Question": result.get(
                    "Question",
                    ""
                ),
                "Question Type": result.get(
                    "Question Type",
                    ""
                ),
                "CLO Alignment": result.get(
                    "CLO Alignment"
                ),
                "PLO Alignment": result.get(
                    "PLO Alignment"
                ),
                "Bloom": result.get(
                    "Bloom"
                ),
                "Bloom Level": result.get(
                    "Bloom Level",
                    ""
                ),
                "Subject Relevance": result.get(
                    "Subject Relevance"
                ),
                "Clarity": result.get(
                    "Clarity"
                ),
                "Measurability": result.get(
                    "Measurability"
                ),
                "Overall Score": result.get(
                    "Overall"
                ),
                "Status": result.get(
                    "Status",
                    ""
                ),
            }
        )

    export_df = pd.DataFrame(
        export_rows
    )

    csv_data = export_df.to_csv(
        index=False
    ).encode("utf-8")

    st.download_button(
        "⬇️ Download Results as CSV",
        data=csv_data,
        file_name="obe_quiz_checker_results.csv",
        mime="text/csv",
        use_container_width=True
    )


# ============================================================
# NO ANALYSIS STATE
# ============================================================

else:

    st.header("Assessment Status")

    if not clos or not plos:
        st.info(
            "⏳ Enter CLOs and PLOs to enable alignment analysis."
        )
    elif uploaded_file is None:
        st.info(
            "⏳ Upload the complete assessment to continue."
        )
    else:
        st.info(
            "✓ Inputs are ready. Click "
            "**Analyze Assessment**."
        )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "OBE Quiz Checker | Alignment is calculated only "
    "after CLOs, PLOs and the assessment are provided "
    "and analyzed."
)
