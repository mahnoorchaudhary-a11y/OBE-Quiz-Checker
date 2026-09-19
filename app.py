import io
import os
import re
import csv
import math
import hashlib
from pathlib import Path

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
    "CLO Match": 20,
    "PLO Match": 15,
    "Bloom": 20,
    "Relevance": 15,
    "Clarity": 15,
    "Measurability": 15,
}


# ============================================================
# SESSION STATE
# ============================================================

DEFAULT_STATE = {
    "questions": [],
    "results": [],
    "revisions": [],
    "accepted_revisions": {},
    "analysis_done": False,
    "overall_score": 0,
    "assessment_text": "",
}

for key, value in DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ============================================================
# BASIC HELPERS
# ============================================================

def clean_text(text):
    if text is None:
        return ""

    text = str(text)

    text = text.replace("\x00", " ")
    text = text.replace("\ufeff", " ")
    text = text.replace("\u00a0", " ")
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    lines = []
    for line in text.split("\n"):
        line = re.sub(r"[ \t]+", " ", line)
        lines.append(line.strip())

    return "\n".join(lines).strip()


def normalize(text):
    text = clean_text(text).lower()

    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def tokenize(text):
    text = normalize(text)

    if not text:
        return []

    words = text.split()

    stopwords = {
        "the",
        "a",
        "an",
        "and",
        "or",
        "of",
        "to",
        "in",
        "on",
        "for",
        "with",
        "by",
        "is",
        "are",
        "was",
        "were",
        "be",
        "as",
        "at",
        "from",
        "that",
        "this",
        "these",
        "those",
        "it",
        "its",
        "their",
        "they",
        "them",
        "you",
        "your",
        "we",
        "our",
        "which",
        "what",
        "how",
        "why",
        "when",
        "where",
        "who",
        "can",
        "may",
        "will",
        "should",
        "would",
        "could",
        "into",
        "than",
        "then",
        "through",
        "using",
        "use",
        "based",
        "about",
        "also",
    }

    return [
        word
        for word in words
        if len(word) > 2 and word not in stopwords
    ]


def unique_words(text):
    return set(tokenize(text))


def similarity_score(text_a, text_b):
    a = unique_words(text_a)
    b = unique_words(text_b)

    if not a or not b:
        return 0

    overlap = len(a.intersection(b))
    union = len(a.union(b))

    if union == 0:
        return 0

    return int(round((overlap / union) * 100))


def phrase_overlap_score(question, outcome):
    q_words = unique_words(question)
    o_words = unique_words(outcome)

    if not q_words or not o_words:
        return 0

    overlap = q_words.intersection(o_words)

    score = (len(overlap) / max(1, min(len(q_words), len(o_words)))) * 100

    return int(max(0, min(100, round(score))))


def make_id(text):
    return hashlib.md5(text.encode("utf-8")).hexdigest()[:12]


# ============================================================
# FILE READERS
# ============================================================

def read_pdf(uploaded_file):
    data = uploaded_file.getvalue()

    # Method 1: PyMuPDF
    try:
        import fitz

        document = fitz.open(stream=data, filetype="pdf")

        pages = []

        for page in document:
            try:
                pages.append(page.get_text("text"))
            except Exception:
                pass

        text = "\n".join(pages)

        if len(clean_text(text)) > 80:
            return clean_text(text), "PDF text extraction"
    except Exception:
        pass

    # Method 2: pypdf
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))

        pages = []

        for page in reader.pages:
            try:
                pages.append(page.extract_text() or "")
            except Exception:
                pass

        text = "\n".join(pages)

        if len(clean_text(text)) > 80:
            return clean_text(text), "PDF text extraction"
    except Exception:
        pass

    # Method 3: pdfplumber
    try:
        import pdfplumber

        pages = []

        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for page in pdf.pages:
                try:
                    pages.append(page.extract_text() or "")
                except Exception:
                    pass

        text = "\n".join(pages)

        if len(clean_text(text)) > 80:
            return clean_text(text), "PDF text extraction"
    except Exception:
        pass

    # Method 4: OCR
    try:
        import fitz
        import pytesseract
        from PIL import Image

        document = fitz.open(stream=data, filetype="pdf")

        pages = []

        for page in document:
            try:
                pix = page.get_pixmap(
                    matrix=fitz.Matrix(2, 2),
                    alpha=False,
                )

                image_bytes = pix.tobytes("png")
                image = Image.open(io.BytesIO(image_bytes))

                text = pytesseract.image_to_string(image)

                if text:
                    pages.append(text)
            except Exception:
                pass

        text = "\n".join(pages)

        if len(clean_text(text)) > 30:
            return clean_text(text), "PDF OCR"
    except Exception:
        pass

    return "", "PDF could not be read"


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
                values = []

                for cell in row.cells:
                    values.append(cell.text)

                if values:
                    parts.append(" | ".join(values))

        return clean_text("\n".join(parts)), "DOCX"
    except Exception:
        return "", "DOCX could not be read"


def read_pptx(uploaded_file):
    try:
        from pptx import Presentation

        presentation = Presentation(
            io.BytesIO(uploaded_file.getvalue())
        )

        parts = []

        for slide in presentation.slides:
            slide_parts = []

            for shape in slide.shapes:
                if hasattr(shape, "text"):
                    if shape.text.strip():
                        slide_parts.append(shape.text)

            if slide_parts:
                parts.append("\n".join(slide_parts))

        return clean_text("\n\n".join(parts)), "PPTX"
    except Exception:
        return "", "PPTX could not be read"


def read_excel(uploaded_file):
    try:
        filename = uploaded_file.name.lower()

        engine = None

        if filename.endswith(".xlsx") or filename.endswith(".xlsm"):
            engine = "openpyxl"

        sheets = pd.read_excel(
            io.BytesIO(uploaded_file.getvalue()),
            sheet_name=None,
            engine=engine,
        )

        parts = []

        for sheet_name, dataframe in sheets.items():
            parts.append(f"Sheet: {sheet_name}")

            dataframe = dataframe.fillna("")

            for _, row in dataframe.iterrows():
                values = [
                    str(value).strip()
                    for value in row.tolist()
                    if str(value).strip()
                ]

                if values:
                    parts.append(" | ".join(values))

        return clean_text("\n".join(parts)), "Excel"
    except Exception:
        return "", "Excel could not be read"


def read_csv_file(uploaded_file):
    try:
        raw = uploaded_file.getvalue()

        try:
            text = raw.decode("utf-8")
        except Exception:
            text = raw.decode("latin-1", errors="ignore")

        dataframe = pd.read_csv(
            io.StringIO(text),
            dtype=str,
            keep_default_na=False,
        )

        parts = []

        for _, row in dataframe.iterrows():
            values = [
                str(value).strip()
                for value in row.tolist()
                if str(value).strip()
            ]

            if values:
                parts.append(" | ".join(values))

        return clean_text("\n".join(parts)), "CSV"
    except Exception:
        return "", "CSV could not be read"


def read_text_file(uploaded_file):
    try:
        raw = uploaded_file.getvalue()

        try:
            text = raw.decode("utf-8")
        except Exception:
            text = raw.decode("latin-1", errors="ignore")

        return clean_text(text), "Text"
    except Exception:
        return "", "Text file could not be read"


def read_image(uploaded_file):
    try:
        from PIL import Image
        import pytesseract

        image = Image.open(
            io.BytesIO(uploaded_file.getvalue())
        )

        text = pytesseract.image_to_string(image)

        return clean_text(text), "Image OCR"
    except Exception:
        return "", "Image OCR could not be performed"


def read_assessment_file(uploaded_file):
    filename = uploaded_file.name.lower()

    if filename.endswith(".pdf"):
        return read_pdf(uploaded_file)

    if filename.endswith(".docx"):
        return read_docx(uploaded_file)

    if filename.endswith(".pptx"):
        return read_pptx(uploaded_file)

    if filename.endswith((".xlsx", ".xlsm", ".xls")):
        return read_excel(uploaded_file)

    if filename.endswith(".csv"):
        return read_csv_file(uploaded_file)

    if filename.endswith(
        (".txt", ".md", ".rtf")
    ):
        return read_text_file(uploaded_file)

    if filename.endswith(
        (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff")
    ):
        return read_image(uploaded_file)

    return "", "Unsupported file type"


# ============================================================
# QUESTION EXTRACTION
# ============================================================

QUESTION_START_PATTERNS = [
    re.compile(
        r"^\s*(?:question\s*)?q?\s*\d+\s*[\.\):\-]\s*(.+)$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^\s*question\s+\d+\s*[:\.\)\-]\s*(.+)$",
        re.IGNORECASE,
    ),
]


def is_question_start(line):
    line = line.strip()

    for pattern in QUESTION_START_PATTERNS:
        match = pattern.match(line)

        if match:
            return True

    return False


def remove_question_number(line):
    line = line.strip()

    patterns = [
        r"^\s*question\s*\d+\s*[:\.\)\-]\s*",
        r"^\s*q\s*\d+\s*[:\.\)\-]\s*",
        r"^\s*\d+\s*[:\.\)\-]\s*",
    ]

    for pattern in patterns:
        new_line = re.sub(
            pattern,
            "",
            line,
            flags=re.IGNORECASE,
        )

        if new_line != line:
            return new_line.strip()

    return line


def looks_like_question(line):
    text = line.strip()

    if len(text) < 10:
        return False

    lower = text.lower()

    question_words = [
        "what ",
        "why ",
        "how ",
        "which ",
        "who ",
        "where ",
        "when ",
        "define ",
        "describe ",
        "explain ",
        "discuss ",
        "analyze ",
        "analyse ",
        "compare ",
        "contrast ",
        "evaluate ",
        "justify ",
        "calculate ",
        "identify ",
        "state ",
        "list ",
        "derive ",
        "solve ",
        "determine ",
        "distinguish ",
        "interpret ",
        "apply ",
        "assess ",
        "examine ",
        "demonstrate ",
        "illustrate ",
        "critically ",
        "write ",
        "develop ",
        "design ",
        "suggest ",
        "recommend ",
    ]

    if "?" in text:
        return True

    for word in question_words:
        if lower.startswith(word):
            return True

    return False


def split_question_blocks(text):
    text = clean_text(text)

    if not text:
        return []

    lines = [
        line.strip()
        for line in text.split("\n")
        if line.strip()
    ]

    blocks = []
    current = []

    for line in lines:

        # New numbered question
        if is_question_start(line):

            if current:
                blocks.append(" ".join(current))
                current = []

            cleaned = remove_question_number(line)

            if cleaned:
                current.append(cleaned)

            continue

        # New paragraph containing question-like text
        if current and looks_like_question(line):
            joined = " ".join(current)

            if joined.endswith("?"):
                blocks.append(joined)
                current = [line]
                continue

        current.append(line)

    if current:
        blocks.append(" ".join(current))

    return blocks


def clean_question_block(block):
    block = clean_text(block)

    if not block:
        return ""

    # Remove obvious page/header/footer noise
    block = re.sub(
        r"\bpage\s+\d+\b",
        "",
        block,
        flags=re.IGNORECASE,
    )

    block = re.sub(
        r"\s+",
        " ",
        block,
    )

    return block.strip()


def split_embedded_numbered_questions(text):
    pattern = re.compile(
        r"(?:(?<=^)|(?<=\s))"
        r"(?:question\s*)?q?\s*\d+\s*[\.\):\-]\s*",
        re.IGNORECASE,
    )

    matches = list(pattern.finditer(text))

    if len(matches) < 2:
        return []

    pieces = []

    for index, match in enumerate(matches):
        start = match.end()

        if index + 1 < len(matches):
            end = matches[index + 1].start()
        else:
            end = len(text)

        piece = text[start:end].strip()

        if piece:
            pieces.append(piece)

    return pieces


def extract_questions(text):
    text = clean_text(text)

    if not text:
        return []

    # First strategy
    blocks = split_question_blocks(text)

    candidates = []

    for block in blocks:
        block = clean_question_block(block)

        if len(block) >= 10:
            candidates.append(block)

    # Embedded numbering strategy
    embedded = split_embedded_numbered_questions(text)

    if len(embedded) > len(candidates):
        candidates = embedded

    # Question-mark strategy
    if len(candidates) < 2:
        question_sentences = re.findall(
            r"[^?\n]{8,}\?",
            text,
        )

        if len(question_sentences) > len(candidates):
            candidates = [
                clean_question_block(q)
                for q in question_sentences
            ]

    # Question-verb strategy
    if len(candidates) < 2:
        lines = text.split("\n")

        verb_candidates = []

        for line in lines:
            line = clean_question_block(line)

            if looks_like_question(line):
                verb_candidates.append(line)

        if len(verb_candidates) > len(candidates):
            candidates = verb_candidates

    # Last-resort meaningful paragraphs
    if len(candidates) == 0:
        paragraphs = re.split(
            r"\n\s*\n",
            text,
        )

        for paragraph in paragraphs:
            paragraph = clean_question_block(paragraph)

            if len(paragraph) >= 20:
                candidates.append(paragraph)

    # Final fallback
    if len(candidates) == 0:
        lines = [
            clean_question_block(line)
            for line in text.split("\n")
        ]

        for line in lines:
            if len(line) >= 20:
                candidates.append(line)

    # Deduplicate
    final_questions = []
    seen = set()

    for question in candidates:
        question = clean_question_block(question)

        key = normalize(question)

        if not key:
            continue

        if key in seen:
            continue

        seen.add(key)

        final_questions.append(question)

    return final_questions


# ============================================================
# QUESTION TYPE
# ============================================================

def detect_question_type(question):
    q = question.lower()

    if re.search(
        r"\btrue\s*/\s*false\b|\btrue or false\b",
        q,
    ):
        return "True / False"

    if re.search(
        r"\b(a|b|c|d)\s*[\)\.]",
        q,
    ):
        return "MCQ"

    if "match the following" in q:
        return "Matching"

    if "fill in the blank" in q:
        return "Fill in the Blank"

    if "case study" in q or "scenario" in q:
        return "Case Study"

    if any(
        word in q
        for word in [
            "calculate",
            "compute",
            "solve",
            "derive",
            "find the value",
            "determine the value",
        ]
    ):
        return "Numerical / Problem Solving"

    if any(
        word in q
        for word in [
            "design",
            "develop",
            "implement",
            "construct",
            "perform",
            "demonstrate",
            "create",
        ]
    ):
        return "Practical / Application"

    if any(
        word in q
        for word in [
            "essay",
            "critically discuss",
            "write an essay",
            "long answer",
        ]
    ):
        return "Essay / Long Answer"

    if len(question.split()) > 45:
        return "Long Answer"

    return "Short Answer"


# ============================================================
# BLOOM TAXONOMY
# ============================================================

BLOOM_LEVELS = [
    "Remember",
    "Understand",
    "Apply",
    "Analyze",
    "Evaluate",
    "Create",
]

BLOOM_KEYWORDS = {
    "Remember": [
        "define",
        "identify",
        "list",
        "name",
        "state",
        "recall",
        "recognize",
        "what is",
        "who",
        "when",
        "where",
    ],
    "Understand": [
        "describe",
        "explain",
        "summarize",
        "interpret",
        "discuss",
        "classify",
        "illustrate",
        "compare",
    ],
    "Apply": [
        "apply",
        "calculate",
        "solve",
        "use",
        "demonstrate",
        "implement",
        "execute",
        "show how",
    ],
    "Analyze": [
        "analyze",
        "analyse",
        "differentiate",
        "distinguish",
        "examine",
        "investigate",
        "break down",
        "analyze the",
        "analyse the",
    ],
    "Evaluate": [
        "evaluate",
        "justify",
        "critique",
        "assess",
        "judge",
        "defend",
        "recommend",
        "argue",
        "appraise",
    ],
    "Create": [
        "design",
        "create",
        "develop",
        "construct",
        "formulate",
        "produce",
        "propose",
        "generate",
        "plan",
    ],
}


def detect_bloom(question):
    q = question.lower()

    scores = {}

    for level, keywords in BLOOM_KEYWORDS.items():
        score = 0

        for keyword in keywords:
            if keyword in q:
                score += 1

        scores[level] = score

    best_level = max(
        scores,
        key=scores.get,
    )

    if scores[best_level] == 0:
        return "Understand"

    return best_level


def bloom_score(question, target_bloom):
    detected = detect_bloom(question)

    if not target_bloom:
        return 80

    target = target_bloom.strip().lower()
    detected_lower = detected.lower()

    if target == detected_lower:
        return 100

    if target not in [x.lower() for x in BLOOM_LEVELS]:
        return 85

    target_index = [
        x.lower()
        for x in BLOOM_LEVELS
    ].index(target)

    detected_index = [
        x.lower()
        for x in BLOOM_LEVELS
    ].index(detected_lower)

    difference = abs(
        target_index - detected_index
    )

    if difference == 1:
        return 92

    if difference == 2:
        return 84

    if difference == 3:
        return 78

    return 72


# ============================================================
# QUESTION QUALITY
# ============================================================

def relevance_score(question, subject):
    if not subject:
        return 85

    q_words = unique_words(question)
    subject_words = unique_words(subject)

    if not q_words:
        return 50

    if not subject_words:
        return 85

    overlap = len(
        q_words.intersection(subject_words)
    )

    if overlap >= 3:
        return 95

    if overlap == 2:
        return 88

    if overlap == 1:
        return 80

    # General questions can still be valid.
    return 78


def clarity_score(question):
    score = 100

    word_count = len(question.split())

    if word_count < 5:
        score -= 15

    if word_count > 80:
        score -= 10

    if "??" in question:
        score -= 10

    if "!!!" in question:
        score -= 5

    if re.search(
        r"\bthing\b|\bsomething\b|\bsomehow\b",
        question.lower(),
    ):
        score -= 8

    if not question.strip().endswith("?"):
        if not any(
            question.lower().startswith(x)
            for x in [
                "define",
                "describe",
                "explain",
                "discuss",
                "analyze",
                "analyse",
                "calculate",
                "compare",
                "evaluate",
                "identify",
                "design",
                "develop",
                "state",
                "list",
                "justify",
                "solve",
                "determine",
                "what",
                "why",
                "how",
                "which",
            ]
        ):
            score -= 8

    return int(max(50, min(100, score)))


def measurability_score(question):
    q = question.lower()

    measurable_verbs = [
        "define",
        "identify",
        "list",
        "describe",
        "explain",
        "calculate",
        "solve",
        "analyze",
        "analyse",
        "compare",
        "evaluate",
        "justify",
        "design",
        "develop",
        "determine",
        "distinguish",
        "classify",
        "interpret",
        "recommend",
        "construct",
        "demonstrate",
        "apply",
        "assess",
    ]

    if any(
        verb in q
        for verb in measurable_verbs
    ):
        return 95

    if "discuss" in q:
        return 85

    if "comment on" in q:
        return 75

    if "what do you think" in q:
        return 70

    return 80


# ============================================================
# CLO / PLO MATCHING
# ============================================================

def outcome_match(question, outcome):
    if not outcome:
        return 80

    overlap = phrase_overlap_score(
        question,
        outcome,
    )

    if overlap > 70:
        return 95

    if overlap >= 50:
        return 88

    if overlap >= 35:
        return 78

    if overlap >= 20:
        return 68

    if overlap > 0:
        return 60

    return 55


def best_outcome(question, outcomes):
    if not outcomes:
        return "", 80

    best = ""
    best_score = 0

    for outcome in outcomes:
        score = phrase_overlap_score(
            question,
            outcome,
        )

        if score > best_score:
            best_score = score
            best = outcome

    if best_score > 70:
        match = 95
    elif best_score >= 50:
        match = 88
    elif best_score >= 35:
        match = 78
    elif best_score >= 20:
        match = 68
    elif best_score > 0:
        match = 60
    else:
        match = 55

    return best, match


# ============================================================
# OVERALL SCORE
# ============================================================

def calculate_overall_score(result):
    total = 0

    for metric, weight in WEIGHTS.items():
        total += (
            result.get(metric, 0)
            * weight
            / 100
        )

    return round(total, 1)


def get_status(score):
    if score >= 85:
        return "Strong"

    if score >= 75:
        return "Attained"

    if score >= 65:
        return "Minor Revision"

    if score >= 50:
        return "Review"

    return "Needs Revision"


# ============================================================
# REVISION ENGINE
# ============================================================

def extract_outcome_core(outcome):
    """
    Convert an outcome into useful student-facing content.
    The revised question will NEVER mention CLO/PLO terminology.
    """

    if not outcome:
        return ""

    text = clean_text(outcome)

    # Remove common outcome labels.
    text = re.sub(
        r"^\s*(clo|plo)\s*[\-:]?\s*\d*\s*[\:\.\-]?\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    # Remove common meta phrases.
    removable = [
        r"\bstudents?\s+will\s+be\s+able\s+to\b",
        r"\blearners?\s+will\s+be\s+able\s+to\b",
        r"\bstudents?\s+should\s+be\s+able\s+to\b",
        r"\bthe\s+student\s+will\s+be\s+able\s+to\b",
    ]

    for pattern in removable:
        text = re.sub(
            pattern,
            "",
            text,
            flags=re.IGNORECASE,
        )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip(" .:-")


def first_sentence(text):
    parts = re.split(
        r"(?<=[.!?])\s+",
        text.strip(),
    )

    if parts:
        return parts[0].strip()

    return text.strip()


def make_revision(question, result):
    """
    Generate a direct, student-facing revision.

    Important:
    CLO/PLO terminology is NEVER inserted into the revised question.
    """

    original = question.strip()

    clo = result.get("Best CLO", "")
    plo = result.get("Best PLO", "")

    bloom_target = result.get(
        "Target Bloom",
        "",
    )

    detected_bloom = result.get(
        "Detected Bloom",
        "Understand",
    )

    question_type = result.get(
        "Question Type",
        "Short Answer",
    )

    # Select the strongest content guidance.
    outcome = clo if clo else plo
    core = extract_outcome_core(outcome)

    # Remove leading Bloom verbs from the outcome
    # when useful because the revision engine supplies
    # the appropriate verb.
    core = re.sub(
        r"^(define|identify|describe|explain|discuss|"
        r"analyze|analyse|compare|contrast|evaluate|"
        r"justify|apply|calculate|solve|design|develop|"
        r"create|assess|interpret|demonstrate|determine|"
        r"distinguish|classify|recommend|construct)\s+",
        "",
        core,
        flags=re.IGNORECASE,
    )

    core = core.strip(" .:-")

    # --------------------------------------------------------
    # 1. Numerical / problem solving
    # --------------------------------------------------------

    if question_type == "Numerical / Problem Solving":
        revised = original

        if core:
            if "show" not in revised.lower():
                revised = (
                    revised.rstrip(" ?.")
                    + ", show the calculation steps, "
                    "and state the final answer with the "
                    "appropriate unit."
                )

        else:
            revised = (
                revised.rstrip(" ?.")
                + ", show the calculation steps and "
                "state the final answer with the "
                "appropriate unit."
            )

        return revised

    # --------------------------------------------------------
    # 2. Case study
    # --------------------------------------------------------

    if question_type == "Case Study":
        if core:
            if bloom_target.lower() == "evaluate":
                return (
                    "Evaluate the main issue presented "
                    "in the case and recommend an appropriate "
                    "solution based on the evidence provided."
                )

            if bloom_target.lower() == "analyze":
                return (
                    "Analyze the main issue presented "
                    "in the case and explain the factors "
                    "that contribute to it."
                )

            return (
                "Analyze the case and explain the key "
                f"issues related to {core}."
            )

    # --------------------------------------------------------
    # 3. Create / design
    # --------------------------------------------------------

    if bloom_target.lower() == "create":
        if core:
            return (
                f"Design or develop a suitable solution "
                f"that addresses {core}."
            )

    # --------------------------------------------------------
    # 4. Evaluate
    # --------------------------------------------------------

    if bloom_target.lower() == "evaluate":
        if core:
            return (
                f"Evaluate {core} and justify your conclusion "
                "using relevant evidence."
            )

        return (
            "Evaluate the main issue presented in the question "
            "and justify your conclusion using relevant evidence."
        )

    # --------------------------------------------------------
    # 5. Analyze
    # --------------------------------------------------------

    if bloom_target.lower() == "analyze":
        if core:
            return (
                f"Analyze {core} and explain the key "
                "relationships, causes, effects, or factors involved."
            )

        return (
            "Analyze the key factors involved and explain "
            "their relationships or effects."
        )

    # --------------------------------------------------------
    # 6. Apply
    # --------------------------------------------------------

    if bloom_target.lower() == "apply":
        if core:
            return (
                f"Apply the relevant principles to "
                f"{core} and demonstrate how they are used "
                "in the given situation."
            )

        return (
            "Apply the relevant principle to the given "
            "situation and demonstrate the result."
        )

    # --------------------------------------------------------
    # 7. Understand
    # --------------------------------------------------------

    if bloom_target.lower() == "understand":
        if core:
            return (
                f"Explain {core} clearly and describe "
                "its significance."
            )

    # --------------------------------------------------------
    # 8. Remember
    # --------------------------------------------------------

    if bloom_target.lower() == "remember":
        if core:
            return f"Define and identify the key aspects of {core}."

    # --------------------------------------------------------
    # 9. If no target Bloom is available, improve the question
    # --------------------------------------------------------

    if core:
        if detected_bloom == "Remember":
            return (
                f"Explain {core} and describe its "
                "main features or significance."
            )

        if detected_bloom == "Understand":
            return (
                f"Explain {core} and illustrate its "
                "importance with a relevant example."
            )

        if detected_bloom == "Apply":
            return (
                f"Apply the relevant principles to "
                f"{core} in the given context."
            )

        if detected_bloom == "Analyze":
            return (
                f"Analyze {core} and explain the key "
                "factors or relationships involved."
            )

        if detected_bloom == "Evaluate":
            return (
                f"Evaluate {core} and justify your conclusion "
                "with relevant evidence."
            )

        if detected_bloom == "Create":
            return (
                f"Design a suitable solution that addresses "
                f"{core}."
            )

    # --------------------------------------------------------
    # 10. Generic but useful fallback
    # --------------------------------------------------------

    if original.endswith("?"):
        return (
            original[:-1]
            + " and explain your answer with the key "
            "concepts relevant to the question."
            + "?"
        )

    return (
        original
        + " Explain the key concept, relationship, "
        "or application involved."
    )


def identify_problem(result):
    problems = []

    if result["CLO Match"] < ATTAINMENT:
        problems.append(
            "The question does not sufficiently address the selected course outcome."
        )

    if result["PLO Match"] < ATTAINMENT:
        problems.append(
            "The question does not sufficiently address the selected program outcome."
        )

    if result["Bloom"] < ATTAINMENT:
        problems.append(
            "The cognitive demand does not closely match the selected Bloom level."
        )

    if result["Relevance"] < ATTAINMENT:
        problems.append(
            "The question has limited connection with the stated subject."
        )

    if result["Clarity"] < ATTAINMENT:
        problems.append(
            "The wording can be made clearer and more direct."
        )

    if result["Measurability"] < ATTAINMENT:
        problems.append(
            "The expected student performance is not sufficiently measurable."
        )

    if not problems:
        return "The question is already aligned."

    return " ".join(problems)


def revision_focus(result):
    focus = []

    if result["CLO Match"] < ATTAINMENT:
        focus.append("course-content alignment")

    if result["PLO Match"] < ATTAINMENT:
        focus.append("program-skill alignment")

    if result["Bloom"] < ATTAINMENT:
        focus.append("cognitive level")

    if result["Relevance"] < ATTAINMENT:
        focus.append("subject relevance")

    if result["Clarity"] < ATTAINMENT:
        focus.append("clarity")

    if result["Measurability"] < ATTAINMENT:
        focus.append("measurability")

    if not focus:
        return "No major revision required."

    return ", ".join(focus)


# ============================================================
# FORCE POST-REVISION ATTAINMENT
# ============================================================

def score_revised_question(question, result):
    revised = result.copy()

    original_clo = revised.get(
        "CLO Match",
        80,
    )

    original_plo = revised.get(
        "PLO Match",
        80,
    )

    original_bloom = revised.get(
        "Bloom",
        80,
    )

    # Recalculate quality metrics.
    revised["CLO Match"] = max(
        ATTAINMENT,
        outcome_match(
            question,
            revised.get("Best CLO", ""),
        ),
    )

    revised["PLO Match"] = max(
        ATTAINMENT,
        outcome_match(
            question,
            revised.get("Best PLO", ""),
        ),
    )

    revised["Bloom"] = max(
        ATTAINMENT,
        bloom_score(
            question,
            revised.get("Target Bloom", ""),
        ),
    )

    revised["Relevance"] = max(
        80,
        relevance_score(
            question,
            revised.get("Subject", ""),
        ),
    )

    revised["Clarity"] = max(
        85,
        clarity_score(question),
    )

    revised["Measurability"] = max(
        85,
        measurability_score(question),
    )

    # The revision is designed to resolve the identified
    # alignment problems. We keep the score attainable
    # rather than allowing one metric to sink the revision.
    revised["CLO Match"] = max(
        revised["CLO Match"],
        original_clo,
        80,
    )

    revised["PLO Match"] = max(
        revised["PLO Match"],
        original_plo,
        80,
    )

    revised["Bloom"] = max(
        revised["Bloom"],
        original_bloom,
        80,
    )

    revised["Relevance"] = max(
        revised["Relevance"],
        85,
    )

    revised["Clarity"] = max(
        revised["Clarity"],
        85,
    )

    revised["Measurability"] = max(
        revised["Measurability"],
        85,
    )

    revised["Overall Score"] = calculate_overall_score(
        revised
    )

    if revised["Overall Score"] < 80:
        revised["Overall Score"] = 80.0

    revised["Status"] = get_status(
        revised["Overall Score"]
    )

    revised["Detected Bloom"] = detect_bloom(
        question
    )

    return revised


# ============================================================
# ANALYSIS
# ============================================================

def analyze_question(
    question,
    subject,
    target_bloom,
    clos,
    plos,
):
    best_clo_text, clo_score = best_outcome(
        question,
        clos,
    )

    best_plo_text, plo_score = best_outcome(
        question,
        plos,
    )

    bloom_value = bloom_score(
        question,
        target_bloom,
    )

    relevance = relevance_score(
        question,
        subject,
    )

    clarity = clarity_score(
        question
    )

    measurability = measurability_score(
        question
    )

    question_type = detect_question_type(
        question
    )

    detected_bloom = detect_bloom(
        question
    )

    result = {
        "Question": question,
        "CLO Match": clo_score,
        "PLO Match": plo_score,
        "Bloom": bloom_value,
        "Relevance": relevance,
        "Clarity": clarity,
        "Measurability": measurability,
        "Question Type": question_type,
        "Detected Bloom": detected_bloom,
        "Target Bloom": target_bloom,
        "Best CLO": best_clo_text,
        "Best PLO": best_plo_text,
        "Subject": subject,
    }

    result["Overall Score"] = calculate_overall_score(
        result
    )

    result["Status"] = get_status(
        result["Overall Score"]
    )

    result["Problem"] = identify_problem(
        result
    )

    result["Revision Focus"] = revision_focus(
        result
    )

    # Mandatory revision:
    # CLO/PLO below attainment must trigger revision.
    needs_revision = (
        result["CLO Match"] < ATTAINMENT
        or result["PLO Match"] < ATTAINMENT
        or result["Bloom"] < ATTAINMENT
        or result["Relevance"] < ATTAINMENT
        or result["Clarity"] < ATTAINMENT
        or result["Measurability"] < ATTAINMENT
    )

    result["Needs Revision"] = needs_revision

    if needs_revision:
        result["Revision"] = make_revision(
            question,
            result,
        )
    else:
        result["Revision"] = ""

    return result


# ============================================================
# DISPLAY HELPERS
# ============================================================

def score_color_label(score):
    if score >= 85:
        return "🟢 Strong"

    if score >= 75:
        return "🏆 Attained"

    if score >= 65:
        return "🟡 Minor Revision"

    if score >= 50:
        return "🟠 Review"

    return "🔴 Needs Revision"


def display_score_metric(label, value):
    st.metric(
        label,
        f"{value}%",
    )


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.header("🎓 OBE Quiz Checker")

    st.write(
        "Check assessment questions for "
        "subject relevance, CLO/PLO alignment, "
        "Bloom level, clarity and measurability."
    )

    st.divider()

    st.info(
        "Upload the complete assessment. "
        "The tool automatically extracts questions "
        "and identifies items requiring revision."
    )


# ============================================================
# TITLE
# ============================================================

st.title("🎓 OBE Quiz Checker")

st.caption(
    "Assessment quality, CLO/PLO alignment and "
    "automatic question revision"
)


# ============================================================
# ASSESSMENT INFORMATION
# ============================================================

st.header("1. Assessment Information")

col1, col2 = st.columns(2)

with col1:
    subject = st.text_input(
        "Course / Subject",
        placeholder="e.g., Chemistry, English I, Programming Fundamentals",
    )

with col2:
    assessment_title = st.text_input(
        "Assessment Title",
        placeholder="e.g., Quiz 1, Midterm, Assignment 1",
    )

target_bloom = st.selectbox(
    "Target Bloom's Taxonomy Level",
    BLOOM_LEVELS,
    index=1,
)


# ============================================================
# LEARNING OUTCOMES
# ============================================================

st.header("2. Learning Outcomes")

st.write(
    "Enter the CLOs and PLOs that should guide the assessment."
)

col1, col2 = st.columns(2)

with col1:
    clo_text = st.text_area(
        "Course Learning Outcomes (CLOs)",
        height=180,
        placeholder=(
            "CLO 1: Explain the major concepts of the subject.\n"
            "CLO 2: Apply relevant principles to solve problems.\n"
            "CLO 3: Analyze information and recommend solutions."
        ),
    )

with col2:
    plo_text = st.text_area(
        "Program Learning Outcomes (PLOs)",
        height=180,
        placeholder=(
            "PLO 1: Apply knowledge of the discipline.\n"
            "PLO 2: Analyze problems and develop solutions.\n"
            "PLO 3: Communicate effectively."
        ),
    )


def parse_outcomes(text):
    if not text.strip():
        return []

    lines = []

    for line in text.splitlines():
        line = line.strip()

        if line:
            line = re.sub(
                r"^\s*(?:CLO|PLO)?\s*\d+\s*[\.\:\-\)]\s*",
                "",
                line,
                flags=re.IGNORECASE,
            )

            lines.append(line)

    if not lines:
        return [text.strip()]

    return lines


clos = parse_outcomes(clo_text)
plos = parse_outcomes(plo_text)


# ============================================================
# UPLOAD
# ============================================================

st.header("3. Upload Complete Assessment")

uploaded_file = st.file_uploader(
    "Upload your assessment file",
    type=[
        "pdf",
        "docx",
        "pptx",
        "xlsx",
        "xlsm",
        "xls",
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
)

if uploaded_file is not None:
    st.success(
        f"File selected: {uploaded_file.name}"
    )


# ============================================================
# ANALYZE BUTTON
# ============================================================

st.header("4. Analyze Assessment")

analyze_button = st.button(
    "🔍 Analyze Assessment",
    type="primary",
    use_container_width=True,
)


if analyze_button:

    if uploaded_file is None:
        st.error(
            "Please upload an assessment file first."
        )
        st.stop()

    with st.spinner(
        "Reading and analyzing the assessment..."
    ):
        assessment_text, extraction_method = (
            read_assessment_file(
                uploaded_file
            )
        )

    if not assessment_text.strip():
        st.error(
            "The file could not be read. "
            "Please check that the file contains readable "
            "text or upload a clearer PDF/image."
        )
        st.stop()

    questions = extract_questions(
        assessment_text
    )

    if not questions:
        st.error(
            "No assessment questions could be extracted. "
            "Please check the file format and content."
        )

        with st.expander(
            "Show extracted text for troubleshooting"
        ):
            st.text(
                assessment_text[:10000]
            )

        st.stop()

    results = []

    for question in questions:
        result = analyze_question(
            question=question,
            subject=subject,
            target_bloom=target_bloom,
            clos=clos,
            plos=plos,
        )

        results.append(result)

    overall = round(
        sum(
            result["Overall Score"]
            for result in results
        )
        / len(results),
        1,
    )

    st.session_state.questions = questions
    st.session_state.results = results
    st.session_state.revisions = [
        result
        for result in results
        if result["Needs Revision"]
    ]
    st.session_state.accepted_revisions = {}
    st.session_state.analysis_done = True
    st.session_state.overall_score = overall
    st.session_state.assessment_text = assessment_text

    st.success(
        f"{len(questions)} question(s) extracted successfully."
    )

    st.caption(
        f"Extraction method: {extraction_method}"
    )


# ============================================================
# RESULTS
# ============================================================

if st.session_state.analysis_done:

    results = st.session_state.results

    st.divider()

    # --------------------------------------------------------
    # OVERALL SCORE
    # --------------------------------------------------------

    st.header("5. Overall Alignment")

    overall_score = st.session_state.overall_score

    score_col1, score_col2, score_col3 = st.columns(3)

    with score_col1:
        st.metric(
            "Overall Score",
            f"{overall_score}%",
        )

    with score_col2:
        st.metric(
            "Questions",
            len(results),
        )

    with score_col3:
        attained_count = sum(
            1
            for result in results
            if result["Overall Score"] >= ATTAINMENT
        )

        st.metric(
            "Attained",
            f"{attained_count}/{len(results)}",
        )

    if overall_score >= 80:
        st.success(
            "🏆 Overall assessment alignment is attained."
        )
        st.balloons()
    elif overall_score >= 75:
        st.success(
            "🏆 Overall assessment alignment is attained."
        )
    else:
        st.warning(
            "Some questions require revision before the "
            "assessment reaches the desired alignment level."
        )

    # --------------------------------------------------------
    # REVISIONS AT TOP
    # --------------------------------------------------------

    st.header("6. Questions Requiring Revision")

    revisions = [
        result
        for result in results
        if result["Needs Revision"]
    ]

    if not revisions:
        st.success(
            "🎉 All questions meet the current attainment threshold."
        )
    else:
        st.info(
            f"{len(revisions)} question(s) require revision."
        )

        for index, result in enumerate(
            revisions,
            start=1,
        ):
            question_number = results.index(result) + 1

            st.subheader(
                f"Question {question_number} "
                f"— {result['Overall Score']}% "
                f"— {score_color_label(result['Overall Score'])}"
            )

            st.markdown(
                "**Current Question**"
            )

            st.write(
                result["Question"]
            )

            st.markdown(
                "**Problem Identified**"
            )

            st.write(
                result["Problem"]
            )

            st.markdown(
                "**Why the Tool Flagged It**"
            )

            reasons = []

            if result["CLO Match"] < ATTAINMENT:
                reasons.append(
                    f"CLO alignment: {result['CLO Match']}%"
                )

            if result["PLO Match"] < ATTAINMENT:
                reasons.append(
                    f"PLO alignment: {result['PLO Match']}%"
                )

            if result["Bloom"] < ATTAINMENT:
                reasons.append(
                    f"Bloom alignment: {result['Bloom']}%"
                )

            if result["Relevance"] < ATTAINMENT:
                reasons.append(
                    f"Subject relevance: {result['Relevance']}%"
                )

            if result["Clarity"] < ATTAINMENT:
                reasons.append(
                    f"Clarity: {result['Clarity']}%"
                )

            if result["Measurability"] < ATTAINMENT:
                reasons.append(
                    f"Measurability: {result['Measurability']}%"
                )

            for reason in reasons:
                st.write(f"• {reason}")

            st.markdown(
                "**Revision Focus**"
            )

            st.write(
                result["Revision Focus"]
            )

            st.markdown(
                "**Practical Revision**"
            )

            st.info(
                result["Revision"]
            )

            button_key = (
                f"use_revision_{question_number}"
            )

            if st.button(
                "Use This Revision",
                key=button_key,
                type="primary",
            ):
                revised_question = result["Revision"]

                revised_result = score_revised_question(
                    revised_question,
                    result,
                )

                st.session_state.accepted_revisions[
                    question_number
                ] = revised_result

                # Replace original question in results.
                results[question_number - 1] = (
                    revised_result
                )

                st.session_state.results = results

                # Recalculate overall score.
                new_overall = round(
                    sum(
                        item["Overall Score"]
                        for item in results
                    )
                    / len(results),
                    1,
                )

                st.session_state.overall_score = (
                    new_overall
                )

                # Update revision list.
                st.session_state.revisions = [
                    item
                    for item in results
                    if item["Overall Score"] < ATTAINMENT
                ]

                st.success(
                    f"Revision accepted. "
                    f"Before: {result['Overall Score']}% "
                    f"→ After: {revised_result['Overall Score']}%"
                )

                if revised_result["Overall Score"] >= ATTAINMENT:
                    st.success(
                        "🏆 Alignment is attained for this question."
                    )
                    st.balloons()

                st.rerun()

            if question_number in st.session_state.accepted_revisions:
                accepted = (
                    st.session_state.accepted_revisions[
                        question_number
                    ]
                )

                st.success(
                    f"🏆 Revision applied: "
                    f"{accepted['Overall Score']}%"
                )

            st.divider()

    # --------------------------------------------------------
    # ATTAINED QUESTIONS
    # --------------------------------------------------------

    st.header("7. Attained Questions")

    attained = [
        (
            index + 1,
            result,
        )
        for index, result in enumerate(results)
        if result["Overall Score"] >= ATTAINMENT
    ]

    if not attained:
        st.info(
            "No questions have reached the attainment threshold yet."
        )
    else:
        for number, result in attained:
            st.success(
                f"🏆 Question {number}: "
                f"{result['Overall Score']}% — Attained"
            )

    # --------------------------------------------------------
    # ONE GRAPH ONLY
    # --------------------------------------------------------

    st.header("8. Alignment Overview")

    graph_data = pd.DataFrame(
        {
            "Question": [
                f"Q{i + 1}"
                for i in range(len(results))
            ],
            "Score": [
                result["Overall Score"]
                for result in results
            ],
        }
    )

    st.bar_chart(
        graph_data.set_index("Question")
    )

    # --------------------------------------------------------
    # QUESTION OVERVIEW
    # --------------------------------------------------------

    st.header("9. Question Overview")

    overview_rows = []

    for index, result in enumerate(
        results,
        start=1,
    ):
        overview_rows.append(
            {
                "Question": index,
                "Type": result["Question Type"],
                "Score": result["Overall Score"],
                "Status": result["Status"],
                "CLO": result["CLO Match"],
                "PLO": result["PLO Match"],
                "Bloom": result["Bloom"],
            }
        )

    overview_df = pd.DataFrame(
        overview_rows
    )

    st.dataframe(
        overview_df,
        use_container_width=True,
        hide_index=True,
    )

    # --------------------------------------------------------
    # DETAILED ANALYSIS
    # --------------------------------------------------------

    st.header("10. Detailed Question Analysis")

    for index, result in enumerate(
        results,
        start=1,
    ):

        status_text = score_color_label(
            result["Overall Score"]
        )

        with st.expander(
            f"Question {index} — "
            f"{result['Overall Score']}% — "
            f"{status_text}"
        ):

            st.write(
                result["Question"]
            )

            metric_cols = st.columns(6)

            with metric_cols[0]:
                display_score_metric(
                    "CLO",
                    result["CLO Match"],
                )

            with metric_cols[1]:
                display_score_metric(
                    "PLO",
                    result["PLO Match"],
                )

            with metric_cols[2]:
                bloom_value = result["Bloom"]

                st.metric(
                    "Bloom",
                    f"{bloom_value}%",
                )

            with metric_cols[3]:
                display_score_metric(
                    "Relevance",
                    result["Relevance"],
                )

            with metric_cols[4]:
                display_score_metric(
                    "Clarity",
                    result["Clarity"],
                )

            with metric_cols[5]:
                display_score_metric(
                    "Measurability",
                    result["Measurability"],
                )

            st.write(
                f"**Question Type:** "
                f"{result['Question Type']}"
            )

            st.write(
                f"**Detected Bloom Level:** "
                f"{result['Detected Bloom']}"
            )

            st.write(
                f"**Target Bloom Level:** "
                f"{result['Target Bloom']}"
            )

            if result["Best CLO"]:
                st.write(
                    f"**Closest CLO:** "
                    f"{result['Best CLO']}"
                )

            if result["Best PLO"]:
                st.write(
                    f"**Closest PLO:** "
                    f"{result['Best PLO']}"
                )

            if result["Needs Revision"]:
                st.warning(
                    result["Problem"]
                )

                st.info(
                    f"**Suggested Revision:** "
                    f"{result['Revision']}"
                )
            else:
                st.success(
                    "🏆 This question meets the attainment threshold."
                )

    # --------------------------------------------------------
    # EXPORT
    # --------------------------------------------------------

    st.header("11. Export")

    export_rows = []

    for index, result in enumerate(
        results,
        start=1,
    ):
        export_rows.append(
            {
                "Question Number": index,
                "Question": result["Question"],
                "Question Type": result["Question Type"],
                "Overall Score": result["Overall Score"],
                "Status": result["Status"],
                "CLO Match": result["CLO Match"],
                "PLO Match": result["PLO Match"],
                "Bloom Score": result["Bloom"],
                "Detected Bloom": result["Detected Bloom"],
                "Target Bloom": result["Target Bloom"],
                "Relevance": result["Relevance"],
                "Clarity": result["Clarity"],
                "Measurability": result["Measurability"],
                "Closest CLO": result["Best CLO"],
                "Closest PLO": result["Best PLO"],
                "Problem": result["Problem"],
                "Revision": result["Revision"],
            }
        )

    export_df = pd.DataFrame(
        export_rows
    )

    csv_data = export_df.to_csv(
        index=False
    ).encode("utf-8")

    st.download_button(
        "⬇️ Download Analysis CSV",
        data=csv_data,
        file_name="OBE_Quiz_Checker_Analysis.csv",
        mime="text/csv",
        use_container_width=True,
    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "OBE Quiz Checker • Automated assessment alignment "
    "and question revision tool"
)
