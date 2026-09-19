🎓 CLO–PLO Mapping System

Dashboard
Programs
PLO Management
Course Management
CLO Management
CLO–PLO Mapping
PLO Attainment
Reports
Import / Export
Settings

Dashboard
It should show cards such as:

┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ Programs    │ │ Courses     │ │ CLOs        │
│     3       │ │     25      │ │     92      │
└─────────────┘ └─────────────┘ └─────────────┘

┌─────────────┐
│ PLOs        │
│     12      │
└─────────────┘

And charts for:

PLO coverage
CLO–PLO mapping strength
PLO attainment
Weak/unmapped PLOs
PLO Management
You should be able to enter:

PLO1
Knowledge of Computing
Description...

Course Management
For example:

Course Code: CS101
Course Name: Programming Fundamentals
Credit Hours: 3
Semester: 1

CLO Management
For example:

CLO1
Explain fundamental programming concepts.

Bloom Level:
Understand

Assessment:
Midterm Examination

CLO–PLO Mapping
The main matrix would look like:

CLO	PLO1	PLO2	PLO3	PLO4	PLO5
CLO1	3	2	0	0	0
CLO2	3	3	2	0	0
CLO3	2	3	3	1	0

Where:

0 = No mapping
1 = Low
2 = Medium
3 = High
Reports
The app can generate:

CLO–PLO matrix
Course-wise mapping
Program-wide mapping
PLO coverage
PLO attainment
Weak PLO report
Excel report
PDF report
One important question before I give you the full code
There are two different things universities often mean by "CLO–PLO mapping":

A. Mapping only

Example:

CLO1 → PLO1 = 3

The application shows the mapping matrix and coverage.

B. Mapping + CLO/PLO attainment

For example:

CLO1 target = 70%
Actual CLO1 attainment = 76%
CLO1 contributes to PLO1 at level 3
Calculated PLO1 attainment = 74%