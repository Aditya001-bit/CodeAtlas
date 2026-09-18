from __future__ import annotations

import argparse
import csv
import random
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List


from backend.risk.dataset.bugs_parser import (
    discover_bugs,
    discover_projects,
    load_bug_info,
    parse_kv_file,
)

from backend.risk.dataset.codeatlas_features import (
    FEATURES,
    analyze_with_features,
)

from backend.risk.dataset.function_mapper import (
    map_bug_to_functions,
)


COLUMNS = [
    "sample_id",
    "repository",
    "bug_id",
    "commit",
    "id",
    "file",
    "function",
    *FEATURES,
    "label",
]


def run(cmd, cwd=None):
    return subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        check=True,
    )


def get_git_url(
    bugsinpy_root: Path,
    project: str,
    bug_id: str,
) -> str:

    info = load_bug_info(
        bugsinpy_root,
        project,
        bug_id,
    )

    project_info = (
        bugsinpy_root
        / "projects"
        / project
        / "project.info"
    )

    metadata = {}

    if project_info.exists():
        metadata = parse_kv_file(
            project_info
        )

    git_url = (
        info.github_url
        or metadata.get("github_url", "")
    )

    if not git_url:
        raise ValueError(
            f"No github_url for {project} bug {bug_id}"
        )

    if not git_url.endswith(".git"):
        git_url += ".git"

    return git_url


def create_lightweight_repo(
    git_url: str,
    repo_path: Path,
):

    print(
        "  creating lightweight git repository..."
    )

    repo_path.mkdir(
        parents=True,
        exist_ok=True,
    )

    run(
        [
            "git",
            "init",
        ],
        cwd=repo_path,
    )

    run(
        [
            "git",
            "remote",
            "add",
            "origin",
            git_url,
        ],
        cwd=repo_path,
    )


def fetch_commit(
    repo: Path,
    commit: str,
):

    print(
        f"  fetching commit {commit[:12]}..."
    )

    run(
        [
            "git",
            "fetch",
            "--filter=blob:none",
            "--depth=1",
            "origin",
            commit,
        ],
        cwd=repo,
    )


def cleanup_worktree(
    repo: Path,
    destination: Path,
):
    try:
        result = subprocess.run(
            [
                "git",
                "worktree",
                "remove",
                "--force",
                str(destination),
            ],
            cwd=repo,
            text=True,
            capture_output=True,
        )

        if result.returncode != 0:
            shutil.rmtree(
                destination,
                ignore_errors=True,
            )

    except Exception:
        shutil.rmtree(
            destination,
            ignore_errors=True,
        )

    try:
        run(
            [
                "git",
                "worktree",
                "prune",
            ],
            cwd=repo,
        )
    except subprocess.CalledProcessError:
        pass


def checkout_commit(
    repo: Path,
    commit: str,
    destination: Path,
):

    cleanup_worktree(
        repo,
        destination,
    )

    print(
        f"  checking out {commit[:12]}..."
    )

    run(
        [
            "git",
            "worktree",
            "add",
            "--detach",
            "--force",
            str(destination),
            commit,
        ],
        cwd=repo,
    )


def sample_negatives(
    rows: List[Dict],
    positives: set,
    rng: random.Random,
    ratio: int,
):

    candidates = [
        row
        for row in rows
        if (
            row["file"],
            row["function"],
        ) not in positives
    ]

    if not positives:
        return []

    count = min(
        len(candidates),
        max(
            1,
            len(positives) * ratio,
        ),
    )

    if count == 0:
        return []

    return rng.sample(
        candidates,
        count,
    )


def process_bug(
    bugsinpy_root: Path,
    project: str,
    bug_id: str,
    repo: Path,
    buggy: Path,
    fixed: Path,
    fetched_commits: set,
    rng: random.Random,
    negative_ratio: int,
):

    info = load_bug_info(
        bugsinpy_root,
        project,
        bug_id,
    )

    if info.buggy_commit not in fetched_commits:

        fetch_commit(
            repo,
            info.buggy_commit,
        )

        fetched_commits.add(
            info.buggy_commit
        )

    if info.fixed_commit not in fetched_commits:

        fetch_commit(
            repo,
            info.fixed_commit,
        )

        fetched_commits.add(
            info.fixed_commit
        )

    print(
        "  preparing buggy snapshot..."
    )

    checkout_commit(
        repo,
        info.buggy_commit,
        buggy,
    )

    print(
        "  preparing fixed snapshot..."
    )

    checkout_commit(
        repo,
        info.fixed_commit,
        fixed,
    )

    print(
        "  mapping changed lines to functions..."
    )

    positives = map_bug_to_functions(
        buggy,
        fixed,
    )

    positive_keys = {
        (
            p["file"],
            p["name"],
        )
        for p in positives
    }

    if not positive_keys:
        raise ValueError(
            "No changed Python functions could be mapped"
        )

    print(
        "  functions identified:"
    )

    for file, function in sorted(
        positive_keys
    ):
        print(
            f"    {file} -> {function}"
        )

    print(
        "  analyzing buggy commit..."
    )

    rows = analyze_with_features(
        buggy
    )

    print(
        f"  CodeAtlas functions found: "
        f"{len(rows)}"
    )

    by_key = {
        (
            row["file"],
            row["function"],
        ): row
        for row in rows
    }

    selected_pos = []

    for key in positive_keys:

        if key in by_key:
            selected_pos.append(
                by_key[key]
            )

    if not selected_pos:
        raise ValueError(
            "Changed functions were not present "
            "in the buggy CodeAtlas parse"
        )

    print(
        f"  positive functions matched: "
        f"{len(selected_pos)}"
    )

    negatives = sample_negatives(
        rows,
        positive_keys,
        rng,
        negative_ratio,
    )

    print(
        f"  negative functions sampled: "
        f"{len(negatives)}"
    )

    output = []

    for row in selected_pos:

        output.append(
            {
                "repository": project,
                "bug_id": bug_id,
                "commit": info.buggy_commit,
                **row,
                "label": 1,
            }
        )

    for row in negatives:

        output.append(
            {
                "repository": project,
                "bug_id": bug_id,
                "commit": info.buggy_commit,
                **row,
                "label": 0,
            }
        )

    return output


def load_existing_rows(
    output_path: Path,
) -> List[Dict]:

    if not output_path.exists():
        return []

    with output_path.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as handle:

        reader = csv.DictReader(
            handle
        )

        return list(reader)


def make_sample_id(
    row: Dict,
    index: int,
) -> str:

    return (
        f"{row['repository']}_"
        f"{row['bug_id']}_"
        f"{row['commit'][:12]}_"
        f"{row['file']}_"
        f"{row['function']}_"
        f"{row['label']}"
    )


def merge_rows(
    existing: List[Dict],
    new_rows: List[Dict],
) -> List[Dict]:

    merged = []
    seen = set()

    for row in existing + new_rows:

        key = (
            row["repository"],
            row["bug_id"],
            row["commit"],
            row["file"],
            row["function"],
            str(row["label"]),
        )

        if key in seen:
            continue

        seen.add(key)
        merged.append(row)

    for index, row in enumerate(
        merged,
        start=1,
    ):

        row["sample_id"] = make_sample_id(
            row,
            index,
        )

    return merged


def save_rows(
    output_path: Path,
    rows: List[Dict],
):

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as handle:

        writer = csv.DictWriter(
            handle,
            fieldnames=COLUMNS,
        )

        writer.writeheader()
        writer.writerows(rows)


def process_project(
    bugsinpy_root: Path,
    project: str,
    bugs: List[str],
    work_root: Path,
    rng: random.Random,
    negative_ratio: int,
):

    if not bugs:
        return [], 0, 0

    git_url = get_git_url(
        bugsinpy_root,
        project,
        bugs[0],
    )

    project_root = (
        work_root
        / f"{project}_repo"
    )

    buggy = (
        work_root
        / f"{project}_buggy"
    )

    fixed = (
        work_root
        / f"{project}_fixed"
    )

    create_lightweight_repo(
        git_url,
        project_root,
    )

    all_rows = []

    attempted = 0
    skipped = 0

    fetched_commits = set()

    for bug_id in bugs:

        attempted += 1

        print()
        print("=" * 60)
        print(
            f"Project: {project}"
        )
        print(
            f"Bug:     {bug_id}"
        )
        print("=" * 60)

        try:

            bug_rows = process_bug(
                bugsinpy_root,
                project,
                bug_id,
                project_root,
                buggy,
                fixed,
                fetched_commits,
                rng,
                negative_ratio,
            )

            all_rows.extend(
                bug_rows
            )

            print(
                "  STATUS: SUCCESS"
            )

        except Exception as exc:

            skipped += 1

            print(
                "  STATUS: FAILED"
            )

            print(
                f"  ERROR: {exc}"
            )

    return (
        all_rows,
        attempted,
        skipped,
    )


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--bugsinpy-root",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--output",
        default=Path(
            "backend/risk/data/"
            "bugsinpy_features.csv"
        ),
        type=Path,
    )

    parser.add_argument(
        "--projects",
        nargs="*",
        help="Projects to process",
    )

    parser.add_argument(
        "--max-bugs",
        type=int,
        default=0,
    )

    parser.add_argument(
        "--negative-ratio",
        type=int,
        default=3,
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=42,
    )

    args = parser.parse_args()

    rng = random.Random(
        args.seed
    )

    if args.projects:

        projects = args.projects

    else:

        projects = discover_projects(
            args.bugsinpy_root
        )[:5]

    existing_rows = load_existing_rows(
        args.output
    )

    print(
        f"Existing samples loaded: "
        f"{len(existing_rows)}"
    )

    work_root = Path(
        tempfile.mkdtemp(
            prefix="codeatlas_bugsinpy_"
        )
    )

    new_rows = []

    total_attempted = 0
    total_skipped = 0
    total_successful = 0

    try:

        for project in projects:

            bugs = discover_bugs(
                args.bugsinpy_root,
                project,
            )

            if args.max_bugs:

                bugs = bugs[
                    :args.max_bugs
                ]

            if not bugs:
                continue

            try:

                (
                    project_rows,
                    attempted,
                    skipped,
                ) = process_project(
                    args.bugsinpy_root,
                    project,
                    bugs,
                    work_root,
                    rng,
                    args.negative_ratio,
                )

                new_rows.extend(
                    project_rows
                )

                total_attempted += (
                    attempted
                )

                total_skipped += (
                    skipped
                )

                total_successful += (
                    attempted - skipped
                )

            except Exception as exc:

                total_attempted += len(
                    bugs
                )

                total_skipped += len(
                    bugs
                )

                print()
                print(
                    "=" * 60
                )

                print(
                    f"Project setup failed: "
                    f"{project}"
                )

                print(
                    f"ERROR: {exc}"
                )

                print(
                    "=" * 60
                )

    finally:

        shutil.rmtree(
            work_root,
            ignore_errors=True,
        )

    rows = merge_rows(
        existing_rows,
        new_rows,
    )

    save_rows(
        args.output,
        rows,
    )

    positives = sum(
        int(row["label"]) == 1
        for row in rows
    )

    negatives = sum(
        int(row["label"]) == 0
        for row in rows
    )

    print()
    print("=" * 60)

    print(
        f"Projects attempted: "
        f"{len(projects)}"
    )

    print(
        f"Bugs attempted:     "
        f"{total_attempted}"
    )

    print(
        f"Bugs successful:    "
        f"{total_successful}"
    )

    print(
        f"Bugs skipped:       "
        f"{total_skipped}"
    )

    print(
        f"New samples:        "
        f"{len(new_rows)}"
    )

    print(
        f"Total samples:      "
        f"{len(rows)}"
    )

    print(
        f"Positive samples:   "
        f"{positives}"
    )

    print(
        f"Negative samples:   "
        f"{negatives}"
    )

    print(
        f"CSV:                "
        f"{args.output.resolve()}"
    )

    print("=" * 60)


if __name__ == "__main__":
    main()