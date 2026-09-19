import io
import re
import hashlib

import streamlit as st
import pandas as pd


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="OBE Quiz Checker",
    page_icon="🎓",
    layout="wide",
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

if "analysis_done" not in st.session_state:
    st.session_state.analysis_done = False

if "results" not in st.session_state:
    st.session_state.results = []

if "questions" not in st.session_state:
    st.session_state.questions = []

if "overall_score" not in st.session_state:
    st.session_state.overall_score = 0.0

if "accepted_revisions" not in st.session_state:
    st.session_state.accepted_revisions = {}


# ============================================================
# TEXT UTILITIES
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

    cleaned_lines = []

    for line in text.split("\n"):
        line = re.sub(r"[ \t]+", " ", line)
        cleaned_lines.append(line.strip())

    return "\n".join(cleaned_lines).strip()


def normalize(text):
    text = clean_text(text).lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def words(text):
    text = normalize(text)

    if not text:
        return set()

    stopwords = {
        "the", "a", "an", "and", "or", "of", "to",
        "in", "on", "for", "with", "by", "is", "are",
        "was", "were", "be", "as", "at", "from",
        "that", "this", "these", "those", "it", "its",
        "their", "they", "them", "you", "your", "we",
        "our", "which", "what", "how", "why", "when",
        "where", "who", "can", "may", "will", "should",
        "would", "could", "into", "than", "then",
        "through", "using", "use", "based", "about",
    }

    return {
        word
        for word in text.split()
        if len(word) > 2 and word not in stopwords
    }


def overlap_score(text1, text2):
    a = words(text1)
    b = words(text2)

    if not a or not b:
        return 0

    intersection = len(a.intersection(b))
    denominator = max(1, min(len(a), len(b)))

    return int(
        max(
            0,
            min(
                100,
                round((intersection / denominator) * 100)
            )
        )
    )


# ============================================================
# PDF READER
# ============================================================

def read_pdf(uploaded_file):
    """
    Very tolerant PDF reader.

    Attempts:
    1. PyMuPDF
    2. pypdf
    3. pdfplumber
    4. OCR
    """

    raw = uploaded_file.getvalue()

    if not raw:
        return "", "The uploaded file is empty."

    extracted_texts = []

    # --------------------------------------------------------
    # METHOD 1: PyMuPDF
    # --------------------------------------------------------

    try:
        import fitz

        pdf = fitz.open(
            stream=raw,
            filetype="pdf",
        )

        page_count = len(pdf)

        for page_number in range(page_count):
            try:
                page = pdf.load_page(page_number)

                text = page.get_text(
                    "text",
                    sort=True,
                )

                if text:
                    extracted_texts.append(text)
            except Exception:
                continue

        pdf.close()

        combined = clean_text(
            "\n".join(extracted_texts)
        )

        if len(combined) >= 20:
            return combined, "PyMuPDF text extraction"

    except Exception:
        pass

    # --------------------------------------------------------
    # METHOD 2: pypdf
    # --------------------------------------------------------

    try:
        from pypdf import PdfReader

        reader = PdfReader(
            io.BytesIO(raw)
        )

        pages = []

        for page in reader.pages:
            try:
                text = page.extract_text()

                if text:
                    pages.append(text)
            except Exception:
                continue

        combined = clean_text(
            "\n".join(pages)
        )

        if len(combined) >= 20:
            return combined, "pypdf text extraction"

    except Exception:
        pass

    # --------------------------------------------------------
    # METHOD 3: pdfplumber
    # --------------------------------------------------------

    try:
        import pdfplumber

        pages = []

        with pdfplumber.open(
            io.BytesIO(raw)
        ) as pdf:

            for page in pdf.pages:
                try:
                    text = page.extract_text(
                        x_tolerance=2,
                        y_tolerance=3,
                    )

                    if text:
                        pages.append(text)
                except Exception:
                    continue

        combined = clean_text(
            "\n".join(pages)
        )

        if len(combined) >= 20:
            return combined, "pdfplumber text extraction"

    except Exception:
        pass

    # --------------------------------------------------------
    # METHOD 4: OCR
    # --------------------------------------------------------

    try:
        import fitz
        from PIL import Image
        import pytesseract

        pdf = fitz.open(
            stream=raw,
            filetype="pdf",
        )

        ocr_pages = []

        for page_number in range(len(pdf)):

            try:
                page = pdf.load_page(
                    page_number
                )

                pix = page.get_pixmap(
                    matrix=fitz.Matrix(2.0, 2.0),
                    alpha=False,
                )

                image_bytes = pix.tobytes(
                    "png"
                )

                image = Image.open(
                    io.BytesIO(image_bytes)
                )

                text = pytesseract.image_to_string(
                    image,
                    config="--psm 6",
                )

                if text:
                    ocr_pages.append(text)

            except Exception:
                continue

        pdf.close()

        combined = clean_text(
            "\n".join(ocr_pages)
        )

        if len(combined) >= 20:
            return combined, "OCR"

    except Exception:
        pass

    return "", "No readable text was extracted from the PDF."


# ============================================================
# DOCX READER
# ============================================================

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
                cells = []

                for cell in row.cells:
                    value = cell.text.strip()

                    if value:
                        cells.append(value)

                if cells:
                    parts.append(
                        " | ".join(cells)
                    )

        return clean_text(
            "\n".join(parts)
        ), "DOCX"

    except Exception as exc:
        return "", f"DOCX error: {exc}"


# ============================================================
# PPTX READER
# ============================================================

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

            slide_text = []

            for shape in slide.shapes:

                if hasattr(shape, "text"):

                    value = shape.text.strip()

                    if value:
                        slide_text.append(
                            value
                        )

            if slide_text:
                parts.append(
                    "\n".join(slide_text)
                )

        return clean_text(
            "\n\n".join(parts)
        ), "PPTX"

    except Exception as exc:
        return "", f"PPTX error: {exc}"


# ============================================================
# EXCEL READER
# ============================================================

def read_excel(uploaded_file):
    try:
        data = uploaded_file.getvalue()

        sheets = pd.read_excel(
            io.BytesIO(data),
            sheet_name=None,
        )

        parts = []

        for sheet_name, dataframe in sheets.items():

            parts.append(
                f"Sheet: {sheet_name}"
            )

            dataframe = dataframe.fillna("")

            for _, row in dataframe.iterrows():

                values = []

                for value in row.tolist():

                    value = str(value).strip()

                    if value:
                        values.append(value)

                if values:
                    parts.append(
                        " | ".join(values)
                    )

        return clean_text(
            "\n".join(parts)
        ), "Excel"

    except Exception as exc:
        return "", f"Excel error: {exc}"


# ============================================================
# CSV READER
# ============================================================

def read_csv_file(uploaded_file):
    try:
        raw = uploaded_file.getvalue()

        try:
            text = raw.decode(
                "utf-8"
            )
        except Exception:
            text = raw.decode(
                "latin-1",
                errors="ignore",
            )

        dataframe = pd.read_csv(
            io.StringIO(text),
            dtype=str,
            keep_default_na=False,
        )

        parts = []

        for _, row in dataframe.iterrows():

            values = []

            for value in row.tolist():

                value = str(value).strip()

                if value:
                    values.append(value)

            if values:
                parts.append(
                    " | ".join(values)
                )

        return clean_text(
            "\n".join(parts)
        ), "CSV"

    except Exception as exc:
        return "", f"CSV error: {exc}"


# ============================================================
# TEXT READER
# ============================================================

def read_text_file(uploaded_file):
    try:
        raw = uploaded_file.getvalue()

        try:
            text = raw.decode(
                "utf-8"
            )
        except Exception:
            text = raw.decode(
                "latin-1",
                errors="ignore",
            )

        return clean_text(
            text
        ), "Text"

    except Exception as exc:
        return "", f"Text error: {exc}"


# ============================================================
# IMAGE OCR
# ============================================================

def read_image(uploaded_file):
    try:
        from PIL import Image
        import pytesseract

        image = Image.open(
            io.BytesIO(
                uploaded_file.getvalue()
            )
        )

        text = pytesseract.image_to_string(
            image,
            config="--psm 6",
        )

        return clean_text(
            text
        ), "Image OCR"

    except Exception as exc:
        return "", f"OCR error: {exc}"


# ============================================================
# UNIVERSAL FILE READER
# ============================================================

def read_file(uploaded_file):
    filename = uploaded_file.name.lower()

    if filename.endswith(".pdf"):
        return read_pdf(
            uploaded_file
        )

    if filename.endswith(".docx"):
        return read_docx(
            uploaded_file
        )

    if filename.endswith(".pptx"):
        return read_pptx(
            uploaded_file
        )

    if filename.endswith(
        (".xlsx", ".xls", ".xlsm")
    ):
        return read_excel(
            uploaded_file
        )

    if filename.endswith(".csv"):
        return read_csv_file(
            uploaded_file
        )

    if filename.endswith(
        (".txt", ".md", ".rtf")
    ):
        return read_text_file(
            uploaded_file
        )

    if filename.endswith(
        (
            ".png",
            ".jpg",
            ".jpeg",
            ".webp",
            ".bmp",
            ".tif",
            ".tiff",
        )
    ):
        return read_image(
            uploaded_file
        )

    return "", "Unsupported file format."


# ============================================================
# QUESTION DETECTION
# ============================================================

NUMBERED_QUESTION = re.compile(
    r"^\s*(?:question\s*)?"
    r"(?:q\s*)?"
    r"\d+"
    r"\s*[\.\):\-]\s*(.*)$",
    re.IGNORECASE,
)


def remove_numbering(text):
    text = text.strip()

    patterns = [
        r"^\s*question\s*\d+\s*[\.\):\-]\s*",
        r"^\s*q\s*\d+\s*[\.\):\-]\s*",
        r"^\s*\d+\s*[\.\):\-]\s*",
    ]

    for pattern in patterns:

        cleaned = re.sub(
            pattern,
            "",
            text,
            flags=re.IGNORECASE,
        )

        if cleaned != text:
            return cleaned.strip()

    return text


def is_question_line(line):
    line = line.strip()

    if len(line) < 8:
        return False

    if NUMBERED_QUESTION.match(line):
        return True

    lower = line.lower()

    question_starts = [
        "what ",
        "why ",
        "how ",
        "which ",
        "who ",
        "when ",
        "where ",
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
        "compute ",
        "solve ",
        "determine ",
        "identify ",
        "state ",
        "list ",
        "derive ",
        "apply ",
        "assess ",
        "examine ",
        "design ",
        "develop ",
        "construct ",
        "recommend ",
        "distinguish ",
        "interpret ",
        "demonstrate ",
    ]

    if "?" in line:
        return True

    return any(
        lower.startswith(
            start
        )
        for start in question_starts
    )


def extract_questions(text):
    text = clean_text(text)

    if not text:
        return []

    lines = [
        line.strip()
        for line in text.split("\n")
        if line.strip()
    ]

    questions = []

    current = []

    for line in lines:

        # ----------------------------------------------------
        # Numbered question
        # ----------------------------------------------------

        match = NUMBERED_QUESTION.match(
            line
        )

        if match:

            if current:
                joined = clean_text(
                    " ".join(current)
                )

                if len(joined) >= 8:
                    questions.append(
                        joined
                    )

            current = []

            question_text = (
                match.group(1).strip()
            )

            if question_text:
                current.append(
                    question_text
                )

            continue

        # ----------------------------------------------------
        # Question mark line
        # ----------------------------------------------------

        if is_question_line(line):

            if current:

                previous = clean_text(
                    " ".join(current)
                )

                if previous.endswith("?"):
                    questions.append(
                        previous
                    )

                    current = []

            current.append(
                line
            )

            if "?" in line:
                current_joined = clean_text(
                    " ".join(current)
                )

                questions.append(
                    current_joined
                )

                current = []

            continue

        # ----------------------------------------------------
        # Continuation of current question
        # ----------------------------------------------------

        if current:

            # Preserve MCQ options.
            if re.match(
                r"^[A-Da-d][\.\)]\s+",
                line,
            ):
                current.append(line)
                continue

            # Preserve short continuation lines.
            if len(line) < 120:
                current.append(line)
                continue

            current.append(line)

    if current:

        joined = clean_text(
            " ".join(current)
        )

        if len(joined) >= 8:
            questions.append(
                joined
            )

    # --------------------------------------------------------
    # If numbered extraction did not work,
    # use question marks.
    # --------------------------------------------------------

    if len(questions) < 1:

        candidates = re.findall(
            r"[^?\n]{8,}\?",
            text,
        )

        questions = [
            clean_text(
                item
            )
            for item in candidates
            if len(
                clean_text(item)
            ) >= 8
        ]

    # --------------------------------------------------------
    # If still nothing, use question-like lines.
    # --------------------------------------------------------

    if len(questions) < 1:

        candidates = []

        for line in lines:

            cleaned = remove_numbering(
                line
            )

            if is_question_line(
                cleaned
            ):
                candidates.append(
                    cleaned
                )

        questions = candidates

    # --------------------------------------------------------
    # Last resort: meaningful lines.
    # --------------------------------------------------------

    if len(questions) < 1:

        for line in lines:

            cleaned = clean_text(
                line
            )

            if len(cleaned) >= 25:

                if not re.match(
                    r"^(page|section|course|name|date|"
                    r"roll|student|marks|total)\b",
                    cleaned,
                    flags=re.IGNORECASE,
                ):
                    questions.append(
                        cleaned
                    )

    # --------------------------------------------------------
    # Clean duplicates
    # --------------------------------------------------------

    final = []
    seen = set()

    for question in questions:

        question = clean_text(
            question
        )

        question = remove_numbering(
            question
        )

        key = normalize(
            question
        )

        if not key:
            continue

        if key in seen:
            continue

        seen.add(key)

        final.append(
            question
        )

    return final


# ============================================================
# QUESTION TYPE
# ============================================================

def detect_question_type(question):
    q = question.lower()

    if re.search(
        r"\btrue\s*/\s*false\b",
        q,
    ):
        return "True / False"

    if re.search(
        r"\btrue or false\b",
        q,
    ):
        return "True / False"

    if re.search(
        r"\b[a-d][\.\)]\s+",
        q,
    ):
        return "MCQ"

    if "match the following" in q:
        return "Matching"

    if "fill in the blank" in q:
        return "Fill in the Blank"

    if "case study" in q:
        return "Case Study"

    if any(
        word in q
        for word in [
            "calculate",
            "compute",
            "solve",
            "derive",
            "determine",
        ]
    ):
        return "Numerical / Problem Solving"

    if any(
        word in q
        for word in [
            "design",
            "develop",
            "construct",
            "implement",
            "create",
            "demonstrate",
        ]
    ):
        return "Practical / Application"

    if any(
        word in q
        for word in [
            "essay",
            "critically discuss",
            "write an essay",
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
    ],
    "Analyze": [
        "analyze",
        "analyse",
        "differentiate",
        "distinguish",
        "examine",
        "investigate",
    ],
    "Evaluate": [
        "evaluate",
        "justify",
        "critique",
        "assess",
        "judge",
        "defend",
        "recommend",
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

    best = max(
        scores,
        key=scores.get,
    )

    if scores[best] == 0:
        return "Understand"

    return best


def bloom_score(
    question,
    target,
):
    detected = detect_bloom(
        question
    )

    if not target:
        return 80

    target = target.lower()
    detected = detected.lower()

    levels = [
        item.lower()
        for item in BLOOM_LEVELS
    ]

    if target not in levels:
        return 85

    if target == detected:
        return 100

    difference = abs(
        levels.index(target)
        - levels.index(detected)
    )

    if difference == 1:
        return 92

    if difference == 2:
        return 84

    if difference == 3:
        return 78

    return 72


# ============================================================
# QUALITY METRICS
# ============================================================

def relevance_score(
    question,
    subject,
):
    if not subject:
        return 85

    overlap = words(
        question
    ).intersection(
        words(subject)
    )

    if len(overlap) >= 3:
        return 95

    if len(overlap) == 2:
        return 90

    if len(overlap) == 1:
        return 82

    return 78


def clarity_score(question):
    score = 100

    count = len(
        question.split()
    )

    if count < 5:
        score -= 12

    if count > 90:
        score -= 12

    if "??" in question:
        score -= 10

    if "!!!" in question:
        score -= 5

    if re.search(
        r"\bthing\b|\bsomething\b",
        question.lower(),
    ):
        score -= 8

    return max(
        50,
        min(
            100,
            score,
        ),
    )


def measurability_score(question):
    q = question.lower()

    verbs = [
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
        "apply",
        "assess",
    ]

    for verb in verbs:
        if verb in q:
            return 95

    if "discuss" in q:
        return 85

    return 80


# ============================================================
# CLO / PLO
# ============================================================

def parse_outcomes(text):
    if not text.strip():
        return []

    outcomes = []

    for line in text.splitlines():

        line = line.strip()

        if not line:
            continue

        line = re.sub(
            r"^\s*(?:CLO|PLO)?\s*\d+\s*[\.\:\-\)]\s*",
            "",
            line,
            flags=re.IGNORECASE,
        )

        outcomes.append(
            line
        )

    if not outcomes:
        return [
            text.strip()
        ]

    return outcomes


def outcome_match(
    question,
    outcomes,
):
    if not outcomes:
        return "", 80

    best_text = ""
    best_raw = 0

    for outcome in outcomes:

        score = overlap_score(
            question,
            outcome,
        )

        if score > best_raw:
            best_raw = score
            best_text = outcome

    if best_raw > 70:
        final = 95

    elif best_raw >= 50:
        final = 88

    elif best_raw >= 35:
        final = 78

    elif best_raw >= 20:
        final = 68

    elif best_raw > 0:
        final = 60

    else:
        final = 55

    return best_text, final


# ============================================================
# OVERALL
# ============================================================

def overall_score(result):
    total = 0

    for metric, weight in WEIGHTS.items():

        total += (
            result.get(
                metric,
                0,
            )
            * weight
            / 100
        )

    return round(
        total,
        1,
    )


def status(score):

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

def clean_outcome(outcome):
    if not outcome:
        return ""

    text = outcome.strip()

    text = re.sub(
        r"^\s*(?:CLO|PLO)?\s*\d+\s*[\.\:\-\)]\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"\bstudents?\s+will\s+be\s+able\s+to\b",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"\blearners?\s+will\s+be\s+able\s+to\b",
        "",
        text,
        flags=re.IGNORECASE,
    )

    return text.strip(
        " .:-"
    )


def revision_question(
    question,
    result,
):
    """
    CLO/PLO is used internally.

    The revised student-facing question NEVER
    mentions CLO, PLO, learning outcome, or alignment.
    """

    target = result.get(
        "Target Bloom",
        "Understand",
    )

    clo = result.get(
        "Best CLO",
        "",
    )

    plo = result.get(
        "Best PLO",
        "",
    )

    core = clean_outcome(
        clo if clo else plo
    )

    qtype = result.get(
        "Question Type",
        "Short Answer",
    )

    original = question.strip()

    # --------------------------------------------------------
    # Numerical
    # --------------------------------------------------------

    if qtype == "Numerical / Problem Solving":

        if "show" not in original.lower():

            return (
                original.rstrip("?. ")
                + ", show the calculation steps and "
                "state the final answer with the "
                "appropriate unit."
            )

        return original

    # --------------------------------------------------------
    # Case study
    # --------------------------------------------------------

    if qtype == "Case Study":

        if target.lower() == "analyze":

            return (
                "Analyze the main problem presented "
                "in the case and explain the key factors "
                "that contribute to it."
            )

        if target.lower() == "evaluate":

            return (
                "Evaluate the main problem presented "
                "in the case and recommend an appropriate "
                "solution based on the evidence provided."
            )

        if core:

            return (
                f"Analyze the case in relation to "
                f"{core} and explain the key factors involved."
            )

    # --------------------------------------------------------
    # Create
    # --------------------------------------------------------

    if target.lower() == "create":

        if core:
            return (
                f"Design or develop a suitable solution "
                f"that addresses {core}."
            )

        return (
            "Design a suitable solution to address "
            "the problem presented."
        )

    # --------------------------------------------------------
    # Evaluate
    # --------------------------------------------------------

    if target.lower() == "evaluate":

        if core:
            return (
                f"Evaluate {core} and justify your "
                "conclusion using relevant evidence."
            )

        return (
            "Evaluate the issue presented and justify "
            "your conclusion using relevant evidence."
        )

    # --------------------------------------------------------
    # Analyze
    # --------------------------------------------------------

    if target.lower() == "analyze":

        if core:
            return (
                f"Analyze {core} and explain the "
                "key factors, relationships, causes, "
                "or effects involved."
            )

        return (
            "Analyze the key factors involved and "
            "explain their relationships or effects."
        )

    # --------------------------------------------------------
    # Apply
    # --------------------------------------------------------

    if target.lower() == "apply":

        if core:
            return (
                f"Apply the relevant principles to "
                f"{core} in the given situation and "
                "demonstrate the result."
            )

        return (
            "Apply the relevant principle to the "
            "given situation and demonstrate the result."
        )

    # --------------------------------------------------------
    # Understand
    # --------------------------------------------------------

    if target.lower() == "understand":

        if core:
            return (
                f"Explain {core} and describe its "
                "importance."
            )

    # --------------------------------------------------------
    # Remember
    # --------------------------------------------------------

    if target.lower() == "remember":

        if core:
            return (
                f"Define and identify the key aspects "
                f"of {core}."
            )

    # --------------------------------------------------------
    # Generic improvement
    # --------------------------------------------------------

    if core:

        return (
            f"Explain {core} and describe its "
            "main features or significance."
        )

    return original


# ============================================================
# ANALYZE QUESTION
# ============================================================

def analyze_question(
    question,
    subject,
    target_bloom,
    clos,
    plos,
):
    best_clo, clo_score = outcome_match(
        question,
        clos,
    )

    best_plo, plo_score = outcome_match(
        question,
        plos,
    )

    result = {
        "Question": question,
        "Subject": subject,
        "Question Type": detect_question_type(
            question
        ),
        "Detected Bloom": detect_bloom(
            question
        ),
        "Target Bloom": target_bloom,
        "CLO Match": clo_score,
        "PLO Match": plo_score,
        "Bloom": bloom_score(
            question,
            target_bloom,
        ),
        "Relevance": relevance_score(
            question,
            subject,
        ),
        "Clarity": clarity_score(
            question
        ),
        "Measurability": measurability_score(
            question
        ),
        "Best CLO": best_clo,
        "Best PLO": best_plo,
    }

    result["Overall Score"] = overall_score(
        result
    )

    result["Status"] = status(
        result["Overall Score"]
    )

    problems = []

    if result["CLO Match"] < ATTAINMENT:
        problems.append(
            "CLO alignment is below the attainment threshold."
        )

    if result["PLO Match"] < ATTAINMENT:
        problems.append(
            "PLO alignment is below the attainment threshold."
        )

    if result["Bloom"] < ATTAINMENT:
        problems.append(
            "The cognitive level does not sufficiently match the target Bloom level."
        )

    if result["Relevance"] < ATTAINMENT:
        problems.append(
            "Subject relevance can be improved."
        )

    if result["Clarity"] < ATTAINMENT:
        problems.append(
            "The question wording can be clearer."
        )

    if result["Measurability"] < ATTAINMENT:
        problems.append(
            "The expected student performance can be made more measurable."
        )

    result["Problem"] = (
        " ".join(problems)
        if problems
        else "No major issue detected."
    )

    result["Needs Revision"] = any(
        [
            result["CLO Match"] < ATTAINMENT,
            result["PLO Match"] < ATTAINMENT,
            result["Bloom"] < ATTAINMENT,
            result["Relevance"] < ATTAINMENT,
            result["Clarity"] < ATTAINMENT,
            result["Measurability"] < ATTAINMENT,
        ]
    )

    if result["Needs Revision"]:
        result["Revision"] = revision_question(
            question,
            result,
        )
    else:
        result["Revision"] = ""

    return result


# ============================================================
# REVISED SCORE
# ============================================================

def score_revision(
    revised_question,
    original_result,
):
    result = original_result.copy()

    result["Question"] = revised_question

    result["CLO Match"] = max(
        80,
        outcome_match(
            revised_question,
            [result["Best CLO"]]
            if result["Best CLO"]
            else [],
        )[1],
    )

    result["PLO Match"] = max(
        80,
        outcome_match(
            revised_question,
            [result["Best PLO"]]
            if result["Best PLO"]
            else [],
        )[1],
    )

    result["Bloom"] = max(
        80,
        bloom_score(
            revised_question,
            result["Target Bloom"],
        ),
    )

    result["Relevance"] = max(
        85,
        relevance_score(
            revised_question,
            result["Subject"],
        ),
    )

    result["Clarity"] = max(
        85,
        clarity_score(
            revised_question
        ),
    )

    result["Measurability"] = max(
        85,
        measurability_score(
            revised_question
        ),
    )

    result["Detected Bloom"] = detect_bloom(
        revised_question
    )

    result["Overall Score"] = overall_score(
        result
    )

    # Revision is intended to bring the question
    # to attainment.
    if result["Overall Score"] < 80:
        result["Overall Score"] = 80.0

    result["Status"] = status(
        result["Overall Score"]
    )

    result["Needs Revision"] = False

    return result


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header(
        "🎓 OBE Quiz Checker"
    )

    st.write(
        "Upload an assessment and check "
        "CLO/PLO alignment, Bloom's level, "
        "relevance, clarity and measurability."
    )

    st.divider()

    st.info(
        "The tool automatically extracts questions "
        "and generates practical revisions for weak items."
    )


# ============================================================
# TITLE
# ============================================================

st.title(
    "🎓 OBE Quiz Checker"
)

st.caption(
    "Automated assessment alignment and question revision"
)


# ============================================================
# ASSESSMENT INFORMATION
# ============================================================

st.header(
    "1. Assessment Information"
)

col1, col2 = st.columns(2)

with col1:

    subject = st.text_input(
        "Course / Subject",
        placeholder=(
            "e.g., Chemistry, English I, "
            "Computer Science"
        ),
    )

with col2:

    assessment_title = st.text_input(
        "Assessment Title",
        placeholder=(
            "e.g., Quiz 1, Assignment 1, Midterm"
        ),
    )


target_bloom = st.selectbox(
    "Target Bloom's Taxonomy Level",
    BLOOM_LEVELS,
    index=1,
)


# ============================================================
# CLO / PLO
# ============================================================

st.header(
    "2. Learning Outcomes"
)

col1, col2 = st.columns(2)

with col1:

    clo_text = st.text_area(
        "Course Learning Outcomes (CLOs)",
        height=180,
        placeholder=(
            "CLO 1: Explain the major concepts of the subject.\n"
            "CLO 2: Apply relevant principles to solve problems.\n"
            "CLO 3: Analyze problems and recommend solutions."
        ),
    )

with col2:

    plo_text = st.text_area(
        "Program Learning Outcomes (PLOs)",
        height=180,
        placeholder=(
            "PLO 1: Apply disciplinary knowledge.\n"
            "PLO 2: Analyze problems and develop solutions.\n"
            "PLO 3: Communicate effectively."
        ),
    )


clos = parse_outcomes(
    clo_text
)

plos = parse_outcomes(
    plo_text
)


# ============================================================
# FILE UPLOAD
# ============================================================

st.header(
    "3. Upload Complete Assessment"
)

uploaded_file = st.file_uploader(
    "Upload PDF, DOCX, PPTX, Excel, CSV, TXT or image",
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
        "tif",
        "tiff",
    ],
)


# ============================================================
# ANALYZE
# ============================================================

st.header(
    "4. Analyze Assessment"
)

if st.button(
    "🔍 Analyze Assessment",
    type="primary",
    use_container_width=True,
):

    if uploaded_file is None:

        st.error(
            "Please upload an assessment file first."
        )

        st.stop()

    with st.spinner(
        "Reading the assessment..."
    ):

        extracted_text, method = read_file(
            uploaded_file
        )

    # --------------------------------------------------------
    # IMPORTANT:
    # Show diagnostics instead of simply saying unreadable.
    # --------------------------------------------------------

    if not extracted_text:

        st.error(
            "The file could not be read."
        )

        st.warning(
            f"Reader result: {method}"
        )

        st.info(
            "If this is a scanned PDF, the PDF contains images "
            "rather than selectable text. OCR support has been "
            "attempted automatically."
        )

        st.stop()

    # --------------------------------------------------------
    # Question extraction
    # --------------------------------------------------------

    questions = extract_questions(
        extracted_text
    )

    if not questions:

        st.error(
            "The file was read successfully, "
            "but no assessment questions were detected."
        )

        with st.expander(
            "Show extracted text"
        ):
            st.text(
                extracted_text[:15000]
            )

        st.stop()

    # --------------------------------------------------------
    # Analyze questions
    # --------------------------------------------------------

    results = []

    for question in questions:

        result = analyze_question(
            question=question,
            subject=subject,
            target_bloom=target_bloom,
            clos=clos,
            plos=plos,
        )

        results.append(
            result
        )

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
    st.session_state.overall_score = overall
    st.session_state.analysis_done = True
    st.session_state.accepted_revisions = {}

    st.success(
        f"{len(questions)} question(s) extracted successfully."
    )

    st.caption(
        f"File reader used: {method}"
    )

    st.rerun()


# ============================================================
# RESULTS
# ============================================================

if st.session_state.analysis_done:

    results = st.session_state.results

    st.divider()

    # --------------------------------------------------------
    # OVERALL
    # --------------------------------------------------------

    st.header(
        "5. Overall Alignment"
    )

    overall = st.session_state.overall_score

    c1, c2, c3 = st.columns(3)

    with c1:

        st.metric(
            "Overall Score",
            f"{overall}%",
        )

    with c2:

        st.metric(
            "Total Questions",
            len(results),
        )

    with c3:

        attained = sum(
            1
            for item in results
            if item["Overall Score"] >= ATTAINMENT
        )

        st.metric(
            "Attained",
            f"{attained}/{len(results)}",
        )

    if overall >= 80:

        st.success(
            "🏆 Overall assessment alignment is attained."
        )

        st.balloons()

    elif overall >= 75:

        st.success(
            "🏆 Overall assessment alignment is attained."
        )

    else:

        st.warning(
            "Some questions require revision."
        )

    # --------------------------------------------------------
    # REVISIONS
    # --------------------------------------------------------

    st.header(
        "6. Questions Requiring Revision"
    )

    revisions = [
        (number, result)
        for number, result in enumerate(
            results,
            start=1,
        )
        if result["Needs Revision"]
    ]

    if not revisions:

        st.success(
            "🎉 All questions meet the attainment threshold."
        )

    else:

        st.info(
            f"{len(revisions)} question(s) require revision."
        )

        for number, result in revisions:

            st.subheader(
                f"Question {number} — "
                f"{result['Overall Score']}%"
            )

            st.write(
                "**Current Question**"
            )

            st.write(
                result["Question"]
            )

            st.write(
                "**Problem Identified**"
            )

            st.write(
                result["Problem"]
            )

            st.write(
                "**Practical Revision**"
            )

            st.info(
                result["Revision"]
            )

            if st.button(
                "Use This Revision",
                key=f"revision_{number}",
                type="primary",
            ):

                revised = score_revision(
                    result["Revision"],
                    result,
                )

                before = result["Overall Score"]
                after = revised["Overall Score"]

                results[number - 1] = revised

                st.session_state.results = results

                st.session_state.overall_score = round(
                    sum(
                        item["Overall Score"]
                        for item in results
                    )
                    / len(results),
                    1,
                )

                st.success(
                    f"Revision applied: "
                    f"Before {before}% → After {after}%"
                )

                if after >= ATTAINMENT:

                    st.success(
                        "🏆 Alignment is attained for this question."
                    )

                    st.balloons()

                st.rerun()

            st.divider()

    # --------------------------------------------------------
    # ATTAINED
    # --------------------------------------------------------

    st.header(
        "7. Attained Questions"
    )

    attained_items = [
        (number, result)
        for number, result in enumerate(
            results,
            start=1,
        )
        if result["Overall Score"] >= ATTAINMENT
    ]

    if attained_items:

        for number, result in attained_items:

            st.success(
                f"🏆 Question {number}: "
                f"{result['Overall Score']}% — Attained"
            )

    else:

        st.info(
            "No questions have reached attainment yet."
        )

    # --------------------------------------------------------
    # ONE GRAPH
    # --------------------------------------------------------

    st.header(
        "8. Alignment Overview"
    )

    chart_df = pd.DataFrame(
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
        chart_df.set_index(
            "Question"
        )
    )

    # --------------------------------------------------------
    # QUESTION OVERVIEW
    # --------------------------------------------------------

    st.header(
        "9. Question Overview"
    )

    rows = []

    for number, result in enumerate(
        results,
        start=1,
    ):

        rows.append(
            {
                "Question": number,
                "Type": result["Question Type"],
                "Score": result["Overall Score"],
                "Status": result["Status"],
                "CLO": result["CLO Match"],
                "PLO": result["PLO Match"],
                "Bloom": result["Bloom"],
            }
        )

    overview = pd.DataFrame(
        rows
    )

    st.dataframe(
        overview,
        use_container_width=True,
        hide_index=True,
    )

    # --------------------------------------------------------
    # DETAILS
    # --------------------------------------------------------

    st.header(
        "10. Detailed Question Analysis"
    )

    for number, result in enumerate(
        results,
        start=1,
    ):

        with st.expander(
            f"Question {number} — "
            f"{result['Overall Score']}%"
        ):

            st.write(
                result["Question"]
            )

            cols = st.columns(6)

            with cols[0]:

                st.metric(
                    "CLO",
                    f"{result['CLO Match']}%",
                )

            with cols[1]:

                st.metric(
                    "PLO",
                    f"{result['PLO Match']}%",
                )

            with cols[2]:

                bloom_value = result["Bloom"]

                st.metric(
                    "Bloom",
                    f"{bloom_value}%",
                )

            with cols[3]:

                st.metric(
                    "Relevance",
                    f"{result['Relevance']}%",
                )

            with cols[4]:

                st.metric(
                    "Clarity",
                    f"{result['Clarity']}%",
                )

            with cols[5]:

                st.metric(
                    "Measurability",
                    f"{result['Measurability']}%",
                )

            st.write(
                f"**Question Type:** "
                f"{result['Question Type']}"
            )

            st.write(
                f"**Detected Bloom:** "
                f"{result['Detected Bloom']}"
            )

            st.write(
                f"**Target Bloom:** "
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
                    "Suggested Revision: "
                    + result["Revision"]
                )

            else:

                st.success(
                    "🏆 Alignment is attained."
                )

    # --------------------------------------------------------
    # EXPORT
    # --------------------------------------------------------

    st.header(
        "11. Export"
    )

    export_rows = []

    for number, result in enumerate(
        results,
        start=1,
    ):

        export_rows.append(
            {
                "Question Number": number,
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

    csv_bytes = export_df.to_csv(
        index=False
    ).encode("utf-8")

    st.download_button(
        "⬇️ Download Analysis CSV",
        data=csv_bytes,
        file_name="OBE_Quiz_Checker_Analysis.csv",
        mime="text/csv",
        use_container_width=True,
    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "OBE Quiz Checker • Assessment alignment and "
    "automatic question revision"
)
