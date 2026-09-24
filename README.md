# 🗺️ CodeAtlas

> **Understand Any Python Codebase in Minutes.**

CodeAtlas is an AI-powered developer tool that helps developers understand unfamiliar Python repositories through **codebase analysis, dependency graphs, risk prediction, and repository-aware AI**.

Instead of manually going through hundreds of files, CodeAtlas provides a visual and intelligent way to explore how a Python codebase is structured and where potential risks exist.

---

## 🚀 Features

### 🧩 Codebase Map

Analyze a Python repository and generate a dependency graph showing relationships between:

* Files
* Functions
* Classes
* Imports
* Function calls

### ⚠️ Risk View

Identify potentially risky parts of a codebase using code-level features and ML-based risk prediction.

### 🤖 Ask Your Codebase

Ask questions about the analyzed repository and get answers grounded in the codebase using the RAG pipeline.

---

## 🛠️ Tech Stack

**Frontend**

* React
* Vite
* JavaScript
* Tailwind CSS

**Backend**

* Python
* FastAPI
* Uvicorn
* Python AST
* NetworkX

**Risk Analysis**

* NumPy
* Pandas
* Scikit-learn
* SHAP

**AI / RAG**

* LangChain
* Google GenAI
* FAISS

---

## 📁 Project Structure

```text
CodeAtlas/
│
├── backend/
│   ├── rag/
│   ├── risk/
│   ├── graph.py
│   ├── main.py
│   ├── parser.py
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   ├── public/
│   └── package.json
│
├── .env
├── .gitignore
└── README.md
```

---

# 💻 Run Locally

## 1. Clone the Repository

```bash
git clone https://github.com/Aditya001-bit/CodeAtlas.git
cd CodeAtlas
```

---

# 🔧 Backend Setup

CodeAtlas uses **Python 3.13** for the backend.

### Create Virtual Environment

From the project root:

```bash
py -3.13 -m venv backend/venv
```

### Activate Virtual Environment

**Windows:**

```powershell
.\backend\venv\Scripts\Activate.ps1
```

### Install Dependencies

```bash
python -m pip install -r backend/requirements.txt
```

If SHAP is not installed through the requirements file:

```bash
python -m pip install shap
```

### Start Backend

From the project root:

```bash
python -m uvicorn backend.main:app --reload
```

Backend:

```text
http://127.0.0.1:8000
```

---

# 🎨 Frontend Setup

Open a **new terminal**.

Move into the frontend folder:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Start the development server:

```bash
npm run dev
```

Frontend:

```text
http://localhost:5173
```

---

# 🔑 Environment Variables

If required by the AI/RAG functionality, create a `.env` file and add the required API keys.

Example:

```env
GOOGLE_API_KEY=your_api_key_here
```

**Never commit API keys or other secrets to GitHub.**

---

# 🔄 Running the Project

You need two terminals.

### Terminal 1 — Backend

From the project root:

```bash
.\backend\venv\Scripts\Activate.ps1
python -m uvicorn backend.main:app --reload
```

### Terminal 2 — Frontend

```bash
cd frontend
npm run dev
```

Then open:

```text
http://localhost:5173
```

---

# 🧠 How It Works

```text
Python Repository
        │
        ▼
 Repository Parser
        │
        ├── Files
        ├── Functions
        ├── Classes
        ├── Imports
        └── Calls
        │
        ▼
 Dependency Graph
        │
        ├───────────────┐
        ▼               ▼
    Code Map       Risk Analysis
                        │
                        ▼
                 ML Risk Prediction
                        │
                        ▼
                 Risk Explanation

        Repository
             │
             ▼
        RAG Pipeline
             │
             ▼
      Ask Your Codebase
```

---

# 🎯 Problem

Understanding an unfamiliar codebase can take hours or even days.

Developers often need to:

* Search through multiple files
* Trace function calls
* Understand dependencies
* Identify complex or risky code
* Determine how changes may affect the project

CodeAtlas brings these pieces together into an interactive developer tool.

---

# 💡 Core Workflow

```text
Upload
   ↓
Analyze
   ↓
Explore
   ↓
Understand
```

Users can analyze a Python repository, explore its dependency graph, inspect code relationships, view risk information, and ask repository-specific questions.

---

# 🏆 Hackathon MVP

CodeAtlas is currently a **hackathon prototype/MVP** focused on demonstrating the complete workflow from repository analysis to intelligent codebase exploration.

The current implementation prioritizes a functional end-to-end demonstration rather than production-scale infrastructure.

---

## 👥 Team

* **Aditya Kasaudhan** — Backend / System Development
* **Lakshya** — ML / RAG

---

## 🔮 Future Improvements

* Support for larger repositories
* Multi-language code analysis
* Improved risk prediction
* Advanced dependency analysis
* Better repository-aware AI
* Authentication and user accounts
* Persistent projects
* Production deployment

---

## 📄 License

This project is currently developed as a hackathon prototype.
