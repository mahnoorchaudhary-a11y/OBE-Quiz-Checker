import io
import re
from typing import List, Dict

import pandas as pd
import streamlit as st


# ============================================================
# OBE QUIZ CHECKER
# Fresh implementation
# ============================================================

st.set_page_config(
    page_title="OBE Quiz Checker",
    page_icon="🎓",
    layout="wide"
)


# ============================================================
# APP CONFIGURATION
# ============================================================

ATTAINMENT_SCORE = 75
OVERALL_TARGET = 80

WEIGHTS = {
    "CLO Match": 20,
    "PLO Match": 15,
    "Bloom's Taxonomy": 20,
    "Relevance": 15,
    "Clarity": 15,
    "Measurability": 15,
}

BLOOM_LEVELS = [
    "Remember",
    "Understand",
    "Apply",
    "Analyze",
    "Evaluate",
    "Create",
]

BLOOM_VERBS = {
    "Remember": [
        "define",
        "identify",
        "list",
        "name",
        "state",
        "recall",
        "recognize",
        "mention",
    ],
    "Understand": [
        "describe",
        "explain",
        "summarize",
        "interpret",
        "classify",
        "discuss",
        "illustrate",
    ],
    "Apply": [
        "apply",
        "calculate",
        "solve",
        "use",
        "demonstrate",
        "compute",
        "implement",
    ],
    "Analyze": [
        "analyze",
        "analyse",
        "compare",
        "contrast",
        "differentiate",
        "examine",
        "investigate",
    ],
    "Evaluate": [
        "evaluate",
        "assess",
        "judge",
        "justify",
        "critique",
        "defend",
        "recommend",
    ],
    "Create": [
        "design",
        "develop",
        "create",
        "construct",
        "formulate",
        "produce",
        "propose",
    ],
}


# ============================================================
# SESSION STATE
# ============================================================

defaults = {
    "file_text": "",
    "questions": [],
    "results": [],
    "accepted": {},
    "file_name": "",
    "analysis_done": False,
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ============================================================
# HEADER
# ============================================================

st.title("🎓 OBE Quiz Checker")

st.write(
    "Check your assessment questions for CLO, PLO, "
    "Bloom's Taxonomy, clarity, relevance, and measurability "
    "— and improve weak questions with practical revisions."
)


# ============================================================
# FILE READING
# ============================================================

def read_pdf(uploaded_file):
    data = uploaded_file.getvalue()

    # PyMuPDF
    try:
        import fitz

        document = fitz.open(
            stream=data,
            filetype="pdf"
        )

        pages = []

        for page in document:
            text = page.get_text("text")

            if text:
                pages.append(text)

        result = "\n".join(pages).strip()

        if len(result) >= 20:
            return result
    except Exception:
        pass

    # pypdf
    try:
        from pypdf import PdfReader

        reader = PdfReader(
            io.BytesIO(data)
        )

        pages = []

        for page in reader.pages:
            try:
                text = page.extract_text()
            except Exception:
                text = ""

            if text:
                pages.append(text)

        result = "\n".join(pages).strip()

        if len(result) >= 20:
            return result
    except Exception:
        pass

    # pdfplumber
    try:
        import pdfplumber

        pages = []

        with pdfplumber.open(
            io.BytesIO(data)
        ) as pdf:

            for page in pdf.pages:
                text = page.extract_text()

                if text:
                    pages.append(text)

        result = "\n".join(pages).strip()

        if len(result) >= 20:
            return result
    except Exception:
        pass

    # OCR
    try:
        import fitz
        import pytesseract
        from PIL import Image

        document = fitz.open(
            stream=data,
            filetype="pdf"
        )

        pages = []

        for page in document:

            pix = page.get_pixmap(
                matrix=fitz.Matrix(2, 2),
                alpha=False
            )

            image = Image.open(
                io.BytesIO(
                    pix.tobytes("png")
                )
            )

            text = pytesseract.image_to_string(
                image
            )

            if text:
                pages.append(text)

        return "\n".join(pages).strip()

    except Exception:
        return ""


def read_docx(uploaded_file):
    try:
        from docx import Document

        document = Document(
            io.BytesIO(
                uploaded_file.getvalue()
            )
        )

        parts = []

        for paragraph in document.paragraphs:
            text = paragraph.text.strip()

            if text:
                parts.append(text)

        for table in document.tables:

            for row in table.rows:

                values = []

                for cell in row.cells:
                    value = cell.text.strip()

                    if value:
                        values.append(value)

                if values:
                    parts.append(
                        " | ".join(values)
                    )

        return "\n".join(parts)

    except Exception:
        return ""


def read_pptx(uploaded_file):
    try:
        from pptx import Presentation

        presentation = Presentation(
            io.BytesIO(
                uploaded_file.getvalue()
            )
        )

        parts = []

        for slide in presentation.slides:

            for shape in slide.shapes:

                if hasattr(shape, "text"):

                    text = shape.text.strip()

                    if text:
                        parts.append(text)

        return "\n".join(parts)

    except Exception:
        return ""


def read_excel(uploaded_file):
    try:
        raw = uploaded_file.getvalue()

        excel = pd.ExcelFile(
            io.BytesIO(raw)
        )

        parts = []

        for sheet in excel.sheet_names:

            parts.append(
                "SHEET: " + sheet
            )

            try:
                dataframe = pd.read_excel(
                    io.BytesIO(raw),
                    sheet_name=sheet,
                    header=None
                )

                for row in dataframe.fillna("").values:

                    values = []

                    for item in row:

                        value = str(item).strip()

                        if value:
                            values.append(value)

                    if values:
                        parts.append(
                            " | ".join(values)
                        )

            except Exception:
                continue

        return "\n".join(parts)

    except Exception:
        return ""


def read_csv(uploaded_file):
    try:
        raw = uploaded_file.getvalue()

        try:
            dataframe = pd.read_csv(
                io.BytesIO(raw)
            )
        except Exception:
            dataframe = pd.read_csv(
                io.BytesIO(raw),
                encoding="latin1"
            )

        return dataframe.fillna("").astype(str).to_csv(
            index=False
        )

    except Exception:
        return ""


def read_text(uploaded_file):
    raw = uploaded_file.getvalue()

    for encoding in [
        "utf-8",
        "utf-8-sig",
        "cp1252",
        "latin1",
    ]:

        try:
            return raw.decode(
                encoding,
                errors="ignore"
            )

        except Exception:
            continue

    return ""


def read_image(uploaded_file):
    try:
        from PIL import Image
        import pytesseract

        image = Image.open(
            io.BytesIO(
                uploaded_file.getvalue()
            )
        )

        return pytesseract.image_to_string(
            image
        )

    except Exception:
        return ""


def read_file(uploaded_file):
    name = uploaded_file.name.lower()

    if name.endswith(".pdf"):
        return read_pdf(uploaded_file)

    if name.endswith(".docx"):
        return read_docx(uploaded_file)

    if name.endswith(".pptx"):
        return read_pptx(uploaded_file)

    if name.endswith(
        (".xlsx", ".xls", ".xlsm")
    ):
        return read_excel(uploaded_file)

    if name.endswith(".csv"):
        return read_csv(uploaded_file)

    if name.endswith(
        (".txt", ".md", ".rtf")
    ):
        return read_text(uploaded_file)

    if name.endswith(
        (
            ".png",
            ".jpg",
            ".jpeg",
            ".webp",
            ".bmp",
            ".tiff",
        )
    ):
        return read_image(uploaded_file)

    return read_text(uploaded_file)


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_text(text):
    if not text:
        return ""

    text = text.replace(
        "\x00",
        " "
    )

    text = text.replace(
        "\r\n",
        "\n"
    )

    text = text.replace(
        "\r",
        "\n"
    )

    text = re.sub(
        r"[ \t]+",
        " ",
        text
    )

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )

    return text.strip()


# ============================================================
# QUESTION EXTRACTION
# ============================================================

def remove_question_number(text):
    text = re.sub(
        r"^\s*(?:question\s*)?\d+\s*[\.\):\-]\s*",
        "",
        text,
        flags=re.I
    )

    text = re.sub(
        r"^\s*q\s*\d+\s*[\.\):\-]\s*",
        "",
        text,
        flags=re.I
    )

    return text.strip()


def is_likely_question(text):
    if not text:
        return False

    text = text.strip()

    if len(text) < 10:
        return False

    if "?" in text:
        return True

    first_word_match = re.match(
        r"^[A-Za-z]+",
        text
    )

    if first_word_match:

        first_word = (
            first_word_match
            .group(0)
            .lower()
        )

        question_verbs = []

        for verbs in BLOOM_VERBS.values():
            question_verbs.extend(verbs)

        question_verbs.extend([
            "what",
            "why",
            "how",
            "when",
            "where",
            "which",
            "who",
        ])

        if first_word in question_verbs:
            return True

    return len(text.split()) >= 8


def extract_questions(text):
    """
    Aggressive and flexible question extraction.

    It accepts:
    1. Numbered questions
    2. Q1 / Q2 style questions
    3. Questions ending with ?
    4. Questions beginning with assessment verbs
    5. Paragraph-based assessment items
    6. Table-extracted content
    """

    text = clean_text(text)

    if not text:
        return []

    questions = []

    # --------------------------------------------------------
    # Numbered question blocks
    # --------------------------------------------------------

    pattern = re.compile(
        r"(?im)(?:^|\n)\s*"
        r"(?:"
        r"(?:question\s*)?\d+\s*[\.\):\-]"
        r"|"
        r"q\s*\d+\s*[\.\):\-]"
        r")\s*"
    )

    matches = list(
        pattern.finditer(text)
    )

    if matches:

        for index, match in enumerate(matches):

            start = match.end()

            if index + 1 < len(matches):
                end = matches[index + 1].start()
            else:
                end = len(text)

            block = text[start:end].strip()

            if block:
                questions.append(block)

    # --------------------------------------------------------
    # Individual lines
    # --------------------------------------------------------

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    for line in lines:

        line = remove_question_number(line)

        if is_likely_question(line):
            questions.append(line)

    # --------------------------------------------------------
    # Question mark detection
    # --------------------------------------------------------

    parts = re.split(
        r"(?<=\?)\s+",
        text
    )

    for part in parts:

        part = part.strip()

        if "?" not in part:
            continue

        question = part.split("?")[0] + "?"

        question = remove_question_number(
            question
        )

        if is_likely_question(question):
            questions.append(question)

    # --------------------------------------------------------
    # Paragraph fallback
    # --------------------------------------------------------

    paragraphs = re.split(
        r"\n\s*\n",
        text
    )

    for paragraph in paragraphs:

        paragraph = paragraph.strip()

        if len(paragraph) < 20:
            continue

        paragraph = remove_question_number(
            paragraph
        )

        if is_likely_question(paragraph):
            questions.append(paragraph)

    # --------------------------------------------------------
    # Deduplicate
    # --------------------------------------------------------

    final_questions = []
    seen = set()

    for question in questions:

        question = re.sub(
            r"\s+",
            " ",
            question
        ).strip()

        if len(question) < 10:
            continue

        key = question.lower()

        if key in seen:
            continue

        seen.add(key)

        final_questions.append(
            question
        )

    # --------------------------------------------------------
    # Last-resort extraction
    # --------------------------------------------------------

    if not final_questions:

        fallback = []

        for line in lines:

            if len(line.split()) >= 5:
                fallback.append(
                    remove_question_number(line)
                )

        final_questions = fallback

    return final_questions[:100]


# ============================================================
# WORD MATCHING
# ============================================================

STOP_WORDS = {
    "the",
    "a",
    "an",
    "of",
    "to",
    "and",
    "or",
    "in",
    "on",
    "for",
    "with",
    "by",
    "from",
    "is",
    "are",
    "was",
    "were",
    "be",
    "this",
    "that",
    "these",
    "those",
    "it",
    "its",
    "their",
    "can",
    "may",
    "will",
}


def normalize_words(text):
    words = re.findall(
        r"[A-Za-z0-9]+",
        text.lower()
    )

    result = set()

    for word in words:

        if word in STOP_WORDS:
            continue

        if len(word) <= 2:
            continue

        # Very light normalization
        if word.endswith("ies"):
            word = word[:-3] + "y"
        elif word.endswith("ing") and len(word) > 5:
            word = word[:-3]
        elif word.endswith("ed") and len(word) > 5:
            word = word[:-2]
        elif word.endswith("s") and len(word) > 4:
            word = word[:-1]

        result.add(word)

    return result


def match_score(question, outcome):
    if not outcome:
        return 80

    question_words = normalize_words(
        question
    )

    outcome_words = normalize_words(
        outcome
    )

    if not outcome_words:
        return 80

    overlap = len(
        question_words.intersection(
            outcome_words
        )
    )

    ratio = overlap / len(
        outcome_words
    )

    if ratio >= 0.70:
        return 95

    if ratio >= 0.50:
        return 88

    if ratio >= 0.35:
        return 78

    if ratio >= 0.20:
        return 68

    if ratio > 0:
        return 60

    return 55


def find_best_outcome(question, outcomes):
    if not outcomes:
        return "", 80

    candidates = []

    for outcome in outcomes:

        score = match_score(
            question,
            outcome
        )

        candidates.append(
            (score, outcome)
        )

    candidates.sort(
        key=lambda x: x[0],
        reverse=True
    )

    return candidates[0][1], candidates[0][0]


# ============================================================
# BLOOM ANALYSIS
# ============================================================

def detect_bloom(question):
    lower = question.lower()

    for level in reversed(
        BLOOM_LEVELS
    ):

        for verb in BLOOM_VERBS[level]:

            if re.search(
                r"\b"
                + re.escape(verb)
                + r"\b",
                lower
            ):
                return level

    return "Understand"


def bloom_score(question, target):
    detected = detect_bloom(
        question
    )

    if not target:
        return 85

    if detected == target:
        return 100

    try:
        distance = abs(
            BLOOM_LEVELS.index(
                detected
            )
            -
            BLOOM_LEVELS.index(
                target
            )
        )

        if distance == 1:
            return 92

        if distance == 2:
            return 84

        if distance == 3:
            return 78

        return 72

    except Exception:
        return 80


# ============================================================
# QUESTION TYPE
# ============================================================

def detect_question_type(question):
    lower = question.lower()

    if re.search(
        r"\btrue\s*/?\s*false\b",
        lower
    ):
        return "True / False"

    if re.search(
        r"\b[A-D]\s*[\)\.:]",
        question,
        flags=re.I
    ):
        return "MCQ"

    if "match the following" in lower:
        return "Matching"

    if "fill in the blank" in lower:
        return "Fill in the Blank"

    if any(
        x in lower
        for x in [
            "case study",
            "case scenario",
            "scenario",
        ]
    ):
        return "Case Study"

    if any(
        x in lower
        for x in [
            "calculate",
            "compute",
            "solve",
            "determine",
        ]
    ):
        return "Numerical / Problem Solving"

    if any(
        x in lower
        for x in [
            "design",
            "develop",
            "construct",
            "implement",
        ]
    ):
        return "Practical / Application"

    if len(question.split()) > 60:
        return "Essay / Long Answer"

    return "Short Answer"


# ============================================================
# QUALITY METRICS
# ============================================================

def relevance_score(question):
    words = question.split()

    if len(words) < 5:
        return 68

    if len(words) > 150:
        return 78

    return 90


def clarity_score(question):
    score = 90

    if "??" in question:
        score -= 10

    if question.count("(") != question.count(")"):
        score -= 8

    if len(question.split()) < 5:
        score -= 12

    return max(
        50,
        min(100, score)
    )


def measurability_score(question):
    lower = question.lower()

    for verbs in BLOOM_VERBS.values():

        for verb in verbs:

            if re.search(
                r"\b"
                + re.escape(verb)
                + r"\b",
                lower
            ):
                return 95

    if "?" in question:
        return 85

    return 75


# ============================================================
# QUESTION SCORING
# ============================================================

def calculate_overall(metrics):
    total = 0

    for metric, weight in WEIGHTS.items():

        total += (
            metrics[metric]
            * weight
            / 100
        )

    return round(
        total,
        1
    )


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


def analyze_question(
    question,
    clos,
    plos,
    target_bloom
):

    best_clo, clo_score = find_best_outcome(
        question,
        clos
    )

    best_plo, plo_score = find_best_outcome(
        question,
        plos
    )

    metrics = {
        "CLO Match": clo_score,
        "PLO Match": plo_score,
        "Bloom's Taxonomy": bloom_score(
            question,
            target_bloom
        ),
        "Relevance": relevance_score(
            question
        ),
        "Clarity": clarity_score(
            question
        ),
        "Measurability": measurability_score(
            question
        ),
    }

    overall = calculate_overall(
        metrics
    )

    problems = []

    if clo_score < ATTAINMENT:
        problems.append(
            "CLO alignment is below the attainment threshold."
        )

    if plo_score < ATTAINMENT:
        problems.append(
            "PLO alignment is below the attainment threshold."
        )

    if metrics["Bloom's Taxonomy"] < ATTAINMENT:
        problems.append(
            "The cognitive demand does not closely match the selected Bloom's level."
        )

    if metrics["Relevance"] < ATTAINMENT:
        problems.append(
            "The question may require more specific task context."
        )

    if metrics["Clarity"] < ATTAINMENT:
        problems.append(
            "The wording can be made clearer."
        )

    if metrics["Measurability"] < ATTAINMENT:
        problems.append(
            "The expected student performance can be made more measurable."
        )

    if not problems:
        problems.append(
            "The question meets the main alignment criteria."
        )

    return {
        "Question": question,
        **metrics,
        "Overall": overall,
        "Status": get_status(
            overall
        ),
        "Best CLO": best_clo,
        "Best PLO": best_plo,
        "Question Type": detect_question_type(
            question
        ),
        "Problems": problems,
    }


# ============================================================
# REVISION ENGINE
# ============================================================

def remove_leading_bloom_verb(outcome):
    if not outcome:
        return ""

    text = outcome.strip()

    all_verbs = []

    for verbs in BLOOM_VERBS.values():
        all_verbs.extend(verbs)

    all_verbs = sorted(
        set(all_verbs),
        key=len,
        reverse=True
    )

    pattern = (
        r"^\s*(?:"
        + "|".join(
            re.escape(v)
            for v in all_verbs
        )
        + r")\b\s*"
    )

    text = re.sub(
        pattern,
        "",
        text,
        flags=re.I
    )

    text = re.sub(
        r"^\s*to\s+",
        "",
        text,
        flags=re.I
    )

    return text.strip(
        " .:;"
    )


def get_action(outcome):
    if not outcome:
        return "Explain"

    level = detect_bloom(
        outcome
    )

    actions = {
        "Remember": "Identify",
        "Understand": "Explain",
        "Apply": "Apply",
        "Analyze": "Analyze",
        "Evaluate": "Evaluate",
        "Create": "Design",
    }

    return actions.get(
        level,
        "Explain"
    )


def extract_numeric_tokens(text):
    return re.findall(
        r"\d+(?:\.\d+)?",
        text
    )


def revision_has_same_numbers(
    original,
    revised
):
    return (
        extract_numeric_tokens(
            original
        )
        ==
        extract_numeric_tokens(
            revised
        )
    )


def forbidden_revision_phrase(
    text
):
    lower = text.lower()

    forbidden = [
        "clo",
        "plo",
        "learning outcome",
        "course outcome",
        "program outcome",
        "according to the outcome",
        "as stated in the outcome",
        "using the learning outcome",
    ]

    return any(
        phrase in lower
        for phrase in forbidden
    )


def revise_question(
    question,
    clo,
    plo,
    target_bloom
):

    question = question.strip()

    outcome = clo or plo

    content = remove_leading_bloom_verb(
        outcome
    )

    action = get_action(
        outcome
    )

    question_type = detect_question_type(
        question
    )

    if not content:
        return question

    # --------------------------------------------------------
    # NUMERICAL
    # --------------------------------------------------------

    if question_type == "Numerical / Problem Solving":

        revised = question.rstrip(" ?.")

        if "show" not in revised.lower():

            revised += (
                ". Show the calculation steps "
                "and state the final answer with "
                "the appropriate unit."
            )

    # --------------------------------------------------------
    # CASE STUDY
    # --------------------------------------------------------

    elif question_type == "Case Study":

        revised = (
            action
            + " "
            + content
            + " using evidence from the case."
        )

    # --------------------------------------------------------
    # PRACTICAL
    # --------------------------------------------------------

    elif question_type == "Practical / Application":

        revised = (
            action
            + " "
            + content
            + " in the given task."
        )

    # --------------------------------------------------------
    # MCQ
    # --------------------------------------------------------

    elif question_type == "MCQ":

        option_match = re.search(
            r"\s+(?=[A-D]\s*[\)\.:])",
            question,
            flags=re.I
        )

        if option_match:

            options = question[
                option_match.start():
            ]

            revised = (
                action
                + " "
                + content
                + "."
                + options
            )

        else:

            revised = (
                action
                + " "
                + content
                + "."
            )

    # --------------------------------------------------------
    # TRUE/FALSE
    # --------------------------------------------------------

    elif question_type == "True / False":

        revised = (
            action
            + " "
            + content
            + "."
        )

    # --------------------------------------------------------
    # FILL BLANK
    # --------------------------------------------------------

    elif question_type == "Fill in the Blank":

        revised = (
            "Complete the statement about "
            + content
            + ". "
            + question
        )

    # --------------------------------------------------------
    # MATCHING
    # --------------------------------------------------------

    elif question_type == "Matching":

        revised = (
            "Match each item with the correct "
            + content
            + ". "
            + question
        )

    # --------------------------------------------------------
    # ESSAY
    # --------------------------------------------------------

    elif question_type == "Essay / Long Answer":

        revised = (
            action
            + " "
            + content
            + "."
        )

    # --------------------------------------------------------
    # SHORT ANSWER
    # --------------------------------------------------------

    else:

        revised = (
            action
            + " "
            + content
            + "."
        )

    revised = re.sub(
        r"\s+",
        " ",
        revised
    ).strip()

    # --------------------------------------------------------
    # Safety validation
    # --------------------------------------------------------

    if not revised:
        return question

    if revised.lower() == question.lower():
        return question

    if forbidden_revision_phrase(
        revised
    ):
        return question

    if not revision_has_same_numbers(
        question,
        revised
    ):
        return question

    return revised


# ============================================================
# MAIN INPUT AREA
# ============================================================

st.header("1. Assessment Information")

col1, col2 = st.columns(2)

with col1:

    course_name = st.text_input(
        "Course / Subject",
        placeholder="e.g. Chemistry"
    )

with col2:

    assessment_name = st.text_input(
        "Assessment Name",
        placeholder="e.g. Quiz 1"
    )


# ============================================================
# LEARNING OUTCOMES
# ============================================================

st.header("2. Learning Outcomes")

clo_input = st.text_area(
    "Course Learning Outcomes (CLOs)",
    placeholder=(
        "Enter one CLO per line."
    ),
    height=130
)

plo_input = st.text_area(
    "Program Learning Outcomes (PLOs)",
    placeholder=(
        "Enter one PLO per line."
    ),
    height=130
)

clos = [
    item.strip()
    for item in clo_input.splitlines()
    if item.strip()
]

plos = [
    item.strip()
    for item in plo_input.splitlines()
    if item.strip()
]


# ============================================================
# BLOOM
# ============================================================

target_bloom = st.selectbox(
    "Target Bloom's Taxonomy Level",
    BLOOM_LEVELS,
    index=1
)


# ============================================================
# FILE UPLOAD
# ============================================================

st.header("3. Upload Complete Assessment")

uploaded_file = st.file_uploader(
    "Upload your assessment file",
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
    ]
)


# ============================================================
# READ FILE
# ============================================================

if uploaded_file is not None:

    if st.button(
        "Read Assessment File",
        type="primary",
        use_container_width=True
    ):

        with st.spinner(
            "Reading your assessment..."
        ):

            text = read_file(
                uploaded_file
            )

        text = clean_text(
            text
        )

        st.session_state.file_text = text
        st.session_state.file_name = (
            uploaded_file.name
        )

        if text:

            questions = extract_questions(
                text
            )

            st.session_state.questions = (
                questions
            )

            st.session_state.results = []
            st.session_state.accepted = {}
            st.session_state.analysis_done = False

            st.success(
                "Assessment file read successfully."
            )

            st.info(
                f"{len(questions)} assessment item(s) detected."
            )

        else:

            st.error(
                "The file could not be read. "
                "Please check that it contains readable text."
            )


# ============================================================
# SHOW FILE CONTENT
# ============================================================

if st.session_state.file_text:

    with st.expander(
        "View Extracted Assessment Text"
    ):

        st.text_area(
            "Extracted text",
            st.session_state.file_text,
            height=300
        )


# ============================================================
# SHOW QUESTIONS
# ============================================================

if st.session_state.questions:

    st.header("4. Detected Assessment Questions")

    for number, question in enumerate(
        st.session_state.questions,
        start=1
    ):

        st.write(
            f"**Question {number}:** {question}"
        )


# ============================================================
# ANALYZE
# ============================================================

if st.session_state.questions:

    if st.button(
        "Analyze Assessment",
        type="primary",
        use_container_width=True
    ):

        results = []

        progress = st.progress(
            0
        )

        total = len(
            st.session_state.questions
        )

        for index, question in enumerate(
            st.session_state.questions
        ):

            result = analyze_question(
                question,
                clos,
                plos,
                target_bloom
            )

            results.append(
                result
            )

            progress.progress(
                (index + 1) / total
            )

        st.session_state.results = results
        st.session_state.analysis_done = True

        st.success(
            "Assessment analysis completed."
        )

        st.rerun()


# ============================================================
# RESULTS
# ============================================================

if st.session_state.analysis_done:

    results = st.session_state.results

    st.header("5. Overall Assessment Score")

    overall_score = round(
        sum(
            item["Overall"]
            for item in results
        ) / len(results),
        1
    )

    strong = sum(
        item["Overall"] >= 85
        for item in results
    )

    attained = sum(
        75 <= item["Overall"] < 85
        for item in results
    )

    revision = sum(
        item["Overall"] < 75
        for item in results
    )

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Overall Score",
            f"{overall_score}%"
        )

    with col2:
        st.metric(
            "Strong",
            strong
        )

    with col3:
        st.metric(
            "Attained",
            attained
        )

    with col4:
        st.metric(
            "Needs Revision",
            revision
        )

    if overall_score >= OVERALL_TARGET:

        st.success(
            "🏆 Overall assessment alignment is attained."
        )

        st.balloons()

    else:

        st.warning(
            "The overall assessment is below 80%. "
            "Review the questions marked for revision."
        )


# ============================================================
# REVISIONS
# ============================================================

if st.session_state.analysis_done:

    results = st.session_state.results

    weak_questions = []

    for index, result in enumerate(results):

        if (
            result["Overall"] < ATTAINMENT
            or result["CLO Match"] < ATTAINMENT
            or result["PLO Match"] < ATTAINMENT
        ):
            weak_questions.append(
                index
            )

    if weak_questions:

        st.header(
            "6. Questions Requiring Revision"
        )

        st.write(
            "The tool automatically generates a direct, "
            "subject-specific revision. CLO/PLO information "
            "guides the revision internally and is not inserted "
            "into the student-facing question."
        )

        for index in weak_questions:

            result = results[index]

            number = index + 1

            current_question = (
                st.session_state.accepted.get(
                    number,
                    result["Question"]
                )
            )

            revision_text = revise_question(
                current_question,
                result["Best CLO"],
                result["Best PLO"],
                target_bloom
            )

            with st.container(
                border=True
            ):

                st.subheader(
                    f"Question {number}"
                )

                st.write(
                    f"**Current Score:** "
                    f"{result['Overall']}%"
                )

                st.write(
                    "**Current Question**"
                )

                st.info(
                    current_question
                )

                st.write(
                    "**Why It Was Flagged**"
                )

                for problem in result[
                    "Problems"
                ]:

                    st.write(
                        "• " + problem
                    )

                st.write(
                    "**Suggested Revision**"
                )

                st.success(
                    revision_text
                )

                if revision_text != current_question:

                    if st.button(
                        "Use This Revision",
                        key=f"revision_{number}",
                        type="primary"
                    ):

                        st.session_state.accepted[
                            number
                        ] = revision_text

                        new_result = analyze_question(
                            revision_text,
                            clos,
                            plos,
                            target_bloom
                        )

                        st.session_state.results[
                            index
                        ] = new_result

                        st.success(
                            "Revision accepted."
                        )

                        if (
                            new_result["Overall"]
                            >= ATTAINMENT
                        ):
                            st.success(
                                f"🏆 Alignment attained — "
                                f"{new_result['Overall']}%"
                            )
                            st.balloons()

                        st.rerun()


# ============================================================
# ATTAINED QUESTIONS
# ============================================================

if st.session_state.analysis_done:

    attained_questions = []

    for index, result in enumerate(
        st.session_state.results
    ):

        if (
            result["Overall"] >= ATTAINMENT
            and result["CLO Match"] >= ATTAINMENT
            and result["PLO Match"] >= ATTAINMENT
        ):
            attained_questions.append(
                (index + 1, result)
            )

    if attained_questions:

        st.header(
            "7. Attained Questions"
        )

        for number, result in attained_questions:

            with st.container(
                border=True
            ):

                st.write(
                    f"### Question {number} — 🏆 Attained"
                )

                st.write(
                    result["Question"]
                )

                st.metric(
                    "Score",
                    f"{result['Overall']}%"
                )


# ============================================================
# ONE GRAPH ONLY
# ============================================================

if st.session_state.analysis_done:

    st.header(
        "8. Alignment Overview"
    )

    results = st.session_state.results

    graph_rows = []

    for metric in WEIGHTS:

        average = round(
            sum(
                item[metric]
                for item in results
            ) / len(results),
            1
        )

        graph_rows.append(
            {
                "Metric": metric,
                "Score": average
            }
        )

    graph_df = pd.DataFrame(
        graph_rows
    )

    st.bar_chart(
        graph_df.set_index(
            "Metric"
        )
    )


# ============================================================
# QUESTION OVERVIEW
# ============================================================

if st.session_state.analysis_done:

    st.header(
        "9. Question Overview"
    )

    rows = []

    for index, result in enumerate(
        st.session_state.results
    ):

        rows.append(
            {
                "Question": index + 1,
                "Type": result["Question Type"],
                "CLO": result["CLO Match"],
                "PLO": result["PLO Match"],
                "Bloom": result["Bloom's Taxonomy"],
                "Relevance": result["Relevance"],
                "Clarity": result["Clarity"],
                "Measurability": result["Measurability"],
                "Overall": result["Overall"],
                "Status": result["Status"],
            }
        )

    overview = pd.DataFrame(
        rows
    )

    st.dataframe(
        overview,
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# DETAILED ANALYSIS
# ============================================================

if st.session_state.analysis_done:

    st.header(
        "10. Detailed Question Analysis"
    )

    for index, result in enumerate(
        st.session_state.results
    ):

        with st.expander(
            f"Question {index + 1} — "
            f"{result['Overall']}% — "
            f"{result['Status']}"
        ):

            st.write(
                "**Question:**"
            )

            st.write(
                result["Question"]
            )

            col1, col2, col3 = st.columns(3)

            with col1:

                st.metric(
                    "CLO Match",
                    f"{result['CLO Match']}%"
                )

                st.metric(
                    "PLO Match",
                    f"{result['PLO Match']}%"
                )

            with col2:

                st.metric(
                    "Bloom",
                    f"{result['Bloom's Taxonomy']}%"
                )

                st.metric(
                    "Relevance",
                    f"{result['Relevance']}%"
                )

            with col3:

                st.metric(
                    "Clarity",
                    f"{result['Clarity']}%"
                )

                st.metric(
                    "Measurability",
                    f"{result['Measurability']}%"
                )

            st.write(
                f"**Question Type:** "
                f"{result['Question Type']}"
            )

            if result["Best CLO"]:

                st.write(
                    f"**Matched CLO:** "
                    f"{result['Best CLO']}"
                )

            if result["Best PLO"]:

                st.write(
                    f"**Matched PLO:** "
                    f"{result['Best PLO']}"
                )


# ============================================================
# EXPORT
# ============================================================

if st.session_state.analysis_done:

    st.header(
        "11. Export Report"
    )

    export_rows = []

    for index, result in enumerate(
        st.session_state.results
    ):

        accepted_revision = (
            st.session_state.accepted.get(
                index + 1,
                ""
            )
        )

        export_rows.append(
            {
                "Question Number": index + 1,
                "Original Question": result["Question"],
                "Question Type": result["Question Type"],
                "CLO Match": result["CLO Match"],
                "PLO Match": result["PLO Match"],
                "Bloom": result["Bloom's Taxonomy"],
                "Relevance": result["Relevance"],
                "Clarity": result["Clarity"],
                "Measurability": result["Measurability"],
                "Overall Score": result["Overall"],
                "Status": result["Status"],
                "Suggested/Accepted Revision": accepted_revision,
            }
        )

    export_df = pd.DataFrame(
        export_rows
    )

    csv_bytes = export_df.to_csv(
        index=False
    ).encode("utf-8")

    st.download_button(
        "Download OBE Quiz Checker Report",
        data=csv_bytes,
        file_name="obe_quiz_checker_report.csv",
        mime="text/csv",
        use_container_width=True
    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "OBE Quiz Checker | Subject-agnostic assessment quality and alignment tool"
)
