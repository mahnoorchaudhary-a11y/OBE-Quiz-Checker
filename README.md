# 🎓 OBE Quiz Checker

An AI-assisted assessment quality and OBE alignment tool that evaluates assessment questions against **CLOs, PLOs, Bloom's Taxonomy, relevance, clarity, and measurability**.

The tool is designed for faculty members who want to quickly review an entire quiz, assignment, or assessment and identify questions that require improvement.

---

## 📌 Purpose

The **OBE Quiz Checker** helps instructors determine whether assessment questions are appropriately aligned with intended learning outcomes.

Instead of checking questions one by one manually, faculty can upload a complete assessment and receive:

* CLO alignment analysis
* PLO alignment analysis
* Bloom's Taxonomy analysis
* Relevance assessment
* Clarity assessment
* Measurability assessment
* Overall question score
* Automatic identification of weak questions
* Practical question revisions
* Before-and-after scoring
* Assessment-level alignment overview
* Downloadable assessment report

The tool is **subject-agnostic** and can be used with assessments from different academic disciplines.

---

# ✨ Key Features

## 1. Complete Assessment Upload

Upload an entire assessment instead of entering questions individually.

Supported formats include:

* PDF
* DOCX
* PPTX
* XLSX
* XLS
* CSV
* TXT
* MD
* PNG
* JPG
* JPEG
* WEBP
* BMP
* TIFF

---

## 2. PDF Text Extraction

The tool uses multiple methods to improve PDF compatibility.

For PDF files, it attempts:

1. PyMuPDF
2. pypdf
3. pdfplumber
4. OCR for scanned/image-based PDFs

This allows the tool to handle both:

* Text-based PDFs
* Scanned PDF assessments

---

## 3. Question Detection

The tool can identify questions using several common formats.

### Numbered questions

```text
1. What is photosynthesis?

2. Explain the process of cellular respiration.
```

### Parentheses

```text
1) Define osmosis.

2) Explain diffusion.
```

### Q-format

```text
Q1. What is a database?

Q2. Explain normalization.
```

### Question format

```text
Question 1: Define inheritance.

Question 2: Explain polymorphism.
```

### Question marks

The tool can also detect questions such as:

```text
Why does temperature affect enzyme activity?
```

### Action verbs

The system recognizes common academic verbs such as:

* Define
* Identify
* Describe
* Explain
* Discuss
* Calculate
* Apply
* Analyze
* Evaluate
* Compare
* Contrast
* Design
* Develop
* Justify
* Recommend

---

# 🎯 OBE Alignment Criteria

Each question is evaluated using six main dimensions.

| Metric           | Weight |
| ---------------- | -----: |
| CLO Match        |    20% |
| PLO Match        |    15% |
| Bloom's Taxonomy |    20% |
| Relevance        |    15% |
| Clarity          |    15% |
| Measurability    |    15% |

The final question score is calculated using these weighted dimensions.

---

# 📊 Attainment Levels

The tool uses the following interpretation:

|     Score | Status         |
| --------: | -------------- |
|   85–100% | Strong         |
|    75–84% | Attained       |
|    65–74% | Minor Revision |
|    50–64% | Review         |
| Below 50% | Needs Revision |

A question reaching **75% or above** is considered attained.

---

# 🧠 Bloom's Taxonomy

The tool supports all six levels of the revised Bloom's Taxonomy:

1. Remember
2. Understand
3. Apply
4. Analyze
5. Evaluate
6. Create

The instructor selects the intended Bloom's level for the assessment.

The tool then compares the cognitive demand of the question with the selected target level.

---

# 🎯 CLO and PLO Analysis

Faculty enter the relevant CLOs and PLOs before analyzing the assessment.

Example:

```text
CLO 1: Explain the process of photosynthesis and its importance to plant growth.

CLO 2: Analyze factors affecting plant growth.
```

Example PLOs:

```text
PLO 1: Apply knowledge of the discipline to solve problems.

PLO 2: Analyze and communicate solutions effectively.
```

The system identifies the closest matching CLO and PLO for each question.

---

# 🔍 Question-Level Analysis

For every question, the tool provides:

* Overall score
* CLO match
* PLO match
* Bloom's score
* Relevance
* Clarity
* Measurability
* Detected Bloom's level
* Question type
* Best matching CLO
* Best matching PLO
* Status

---

# ✏️ Automatic Question Revision

Questions below the attainment threshold are automatically considered for revision.

The tool does not simply add generic phrases such as:

> "According to the CLO..."

or

> "Using the learning outcome..."

Instead, the CLO/PLO is used internally to identify the **actual knowledge, concept, skill, or cognitive task** that the question should address.

### Example

**CLO:**

```text
Explain the process of photosynthesis and its importance to plant growth.
```

**Original question:**

```text
What is photosynthesis?
```

**Suggested revision:**

```text
Explain the process of photosynthesis and describe its importance to plant growth.
```

The revision directly assesses the intended content.

---

# 🚫 Revision Principles

The revision engine follows several rules.

### It does not:

* Mention CLO inside the student question
* Mention PLO inside the student question
* Say "according to the CLO"
* Say "according to the PLO"
* Say "using the learning outcome"
* Add vague learning-outcome language
* Change the subject unnecessarily
* Add unrelated content
* Change numerical values
* Change MCQ options unnecessarily

### It attempts to:

* Preserve the original topic
* Preserve technical terminology
* Preserve numerical information
* Preserve the question type
* Preserve MCQ options
* Directly address missing CLO/PLO content
* Improve cognitive demand where necessary
* Make the question measurable
* Keep the revised question concise

---

# 📝 Supported Assessment Types

The tool is not restricted to MCQs.

It can work with different assessment formats, including:

### MCQs

```text
Which of the following is an example of renewable energy?

A) Coal
B) Solar energy
C) Natural gas
D) Petroleum
```

### True/False

```text
Photosynthesis occurs in chloroplasts. True/False
```

### Fill in the Blank

```text
The powerhouse of the cell is ________.
```

### Numerical / Problem Solving

```text
A car travels 120 m in 10 seconds. Calculate its velocity.
```

### Short Answer

```text
Explain the process of osmosis.
```

### Case Study

```text
Read the case and analyze the factors contributing to the business failure.
```

### Essay / Long Answer

```text
Evaluate the impact of artificial intelligence on higher education.
```

### Practical/Application Questions

The tool can also analyze questions requiring students to apply knowledge or perform a task.

---

# 🔄 Revision Workflow

The intended workflow is:

```text
Upload Assessment
       ↓
Enter CLOs
       ↓
Enter PLOs
       ↓
Select Bloom's Level
       ↓
Read Assessment
       ↓
Extract Questions
       ↓
Evaluate Questions
       ↓
Identify Weak Questions
       ↓
Generate Practical Revisions
       ↓
Use This Revision
       ↓
Rescore Question
       ↓
Check Attainment
```

---

# 🏆 Attainment

When a revised question reaches **75% or above**, the question is considered attained.

The tool displays:

```text
🏆 Attained
```

The revised question replaces the original question in the working assessment.

If the overall assessment reaches **80% or above**, the tool displays an overall achievement message and visual celebration.

---

# 📈 Alignment Overview

The tool provides one main visualization:

**Alignment Overview**

This graph displays the overall score for each question.

Example:

```text
Q1  ████████████████████  88%
Q2  █████████████████     79%
Q3  ██████████████        68%
Q4  ███████████████████   84%
```

Only one graph is intentionally used to keep the interface simple.

---

# 📋 Question Overview

The Question Overview table provides a quick assessment-level summary.

It includes:

* Question number
* Question type
* Overall score
* Status
* CLO score
* PLO score
* Bloom score
* Clarity score
* Measurability score

This allows faculty to quickly identify patterns across the assessment.

---

# 📤 Export

After analysis, faculty can download the assessment report as:

```text
obe_quiz_checker_report.csv
```

The report contains:

* Question number
* Original question
* Question type
* Overall score
* Status
* CLO match
* PLO match
* Bloom score
* Relevance
* Clarity
* Measurability
* Detected Bloom's level
* Best matching CLO
* Best matching PLO
* Suggested revision

---

# 🛠️ Installation

## Requirements

The application requires:

```text
streamlit
pandas
PyMuPDF
pypdf
pdfplumber
python-docx
python-pptx
openpyxl
Pillow
pytesseract
```

Create a file called:

```text
requirements.txt
```

and add:

```text
streamlit
pandas
PyMuPDF
pypdf
pdfplumber
python-docx
python-pptx
openpyxl
Pillow
pytesseract
```

---

# ▶️ Run Locally

Install the requirements:

```bash
pip install -r requirements.txt
```

Run the application:

```bash
streamlit run app.py
```

The application will open in your browser.

---

# ☁️ Deploy on Streamlit Cloud

1. Create a GitHub repository.
2. Upload:

   * `app.py`
   * `requirements.txt`
3. Open Streamlit Community Cloud.
4. Select your GitHub repository.
5. Select `app.py` as the main file.
6. Deploy the application.

---

# 📁 Recommended Project Structure

```text
obe-alignment-checker/
│
├── app.py
│
├── requirements.txt
│
└── README.md
```

---

# 🧪 Recommended Testing

Before using the tool in a faculty workshop, test it with assessments from different disciplines.

Suggested subjects:

* English
* Chemistry
* Biology
* Computer Science
* Mathematics
* Physics
* Business
* Economics
* Engineering
* Psychology

Test different question formats:

* MCQs
* Short questions
* Numerical questions
* Case studies
* True/False
* Fill-in-the-blank
* Essay questions
* Application questions

---

# ⚠️ Important File-Reading Considerations

For the most reliable extraction:

### PDF

Prefer a text-based PDF.

For scanned PDFs, OCR is required.

### Word

Use `.docx` rather than very old `.doc` files.

### Excel

Use `.xlsx` where possible.

### Images

Use clear, high-resolution images.

### Question numbering

The tool performs best when questions are clearly separated, for example:

```text
1. Explain...
2. Analyze...
3. Calculate...
```

---

# 🔧 Troubleshooting

## "No assessment questions could be extracted"

First use the **Read File** button.

The tool displays the extracted text.

If the text is visible but questions are not detected, check whether the assessment has recognizable question boundaries.

For example:

```text
1. Explain photosynthesis.
2. Describe cellular respiration.
3. Compare aerobic and anaerobic respiration.
```

is easier to process than a document containing large blocks of unstructured text.

---

## "The PDF could not be read"

Check that the following are present in `requirements.txt`:

```text
PyMuPDF
pypdf
pdfplumber
pytesseract
Pillow
```

Then redeploy the Streamlit application.

---

## Scanned PDF

If the PDF consists of scanned pages rather than selectable text, OCR is used.

For best results:

* Use high-resolution scans
* Keep pages straight
* Avoid blurry images
* Use clear fonts
* Avoid heavily compressed screenshots

---

# 🔐 Data and Privacy

The tool is intended to process assessment material supplied by the instructor.

Institutions should follow their own policies regarding:

* Student information
* Confidential assessments
* Examination papers
* Personally identifiable information
* Data retention
* External AI or cloud services

Avoid uploading confidential student information unless the deployment environment and institutional policies permit it.

---

# 🎓 Suggested Faculty Workshop Activity

The tool can be used as a practical OBE activity.

### Group Activity

Divide participants into groups of approximately four members.

Each group:

1. Selects a course.
2. Identifies a CLO.
3. Identifies a PLO.
4. Selects a Bloom's level.
5. Selects assessment questions.
6. Uploads the assessment.
7. Runs the OBE Quiz Checker.
8. Reviews the identified weaknesses.
9. Examines the automatic revisions.
10. Uses an appropriate revision.
11. Checks the new score.
12. Gives a short presentation explaining what was wrong and how the tool helped.

### Suggested Presentation

Each group can present for approximately one minute:

**1. What did you test?**

**2. What alignment problem did the tool identify?**

**3. What revision did the tool suggest?**

**4. Did the revised question improve the score?**

**5. What did your group learn about writing aligned assessment questions?**

---

# 💡 Example Workshop Scenario

### Course

```text
Biology
```

###
