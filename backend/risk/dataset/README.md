# CodeAtlas + BugsInPy Dataset Pipeline

This pipeline creates a real supervised-learning dataset from historical BugsInPy defects.

It uses the **pre-fix/buggy repository snapshot** to calculate all features. The positive label comes from the actual difference between the buggy and fixed revisions. Untouched functions from the same buggy snapshot are sampled as negatives.

The 13 features are:

`loc, complexity, max_nesting, num_args, num_returns, num_calls, file_imports, caller_count, callee_count, dependency_count, degree, betweenness, pagerank`

## 1. Install BugsInPy

Follow the official BugsInPy setup and make sure `git` works from your terminal. BugsInPy's repository documents the checkout workflow and its Docker option: https://github.com/soarsmu/BugsInPy

## 2. Put this pipeline inside CodeAtlas

Expected:

```text
CodeAtlas/
  backend/
    parser.py
    graph.py
    risk/
      dataset/
```

The included `parser.py` and `graph.py` are copies of the teammate versions this pipeline was built against. If your working CodeAtlas already has these files, **do not overwrite them**; copy only `backend/risk/dataset/`.

## 3. Run a tiny real test

From the CodeAtlas project root on Windows PowerShell:

```powershell
python -m backend.risk.dataset.build_bugsinpy_dataset --bugsinpy-root C:\path\to\BugsInPy --projects black --max-bugs 1
```

Then inspect:

```text
backend/risk/data/bugsinpy_features.csv
```

## 4. Run five projects

```powershell
python -m backend.risk.dataset.build_bugsinpy_dataset --bugsinpy-root C:\path\to\BugsInPy
```

The script defaults to the first five BugsInPy projects it discovers. For a controlled run, explicitly name projects with `--projects`.

## Important

This code has **not** been run against real GitHub repositories inside this ChatGPT environment because external Git cloning is unavailable here. The script is intentionally designed to run on the developer machine where Git/network access is available.

Do not report dataset counts until the real command has completed locally.
