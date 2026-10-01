#!/usr/bin/env python3
"""Validate generated checkpoint-quiz HTML files.

Usage:
    validate_quiz.py quiz.html [answer-schema.html]

Checks the quiz file for:
  - structural markup: every question <li> inside <ol class="questions"> has a
    stem <p> and a <ul class="choices"> with 3-5 option <li>s
  - inline script: KEY length == question count, WHY length == question count,
    and every KEY letter fits within its question's option count
  - JS syntax via `node --check` (when node is on PATH)

With a schema file argument, its <span class="letter">X.</span> answers must
match the quiz KEY exactly.

Prints PASS or a list of problems; exits 0 on pass, 1 on fail.
"""
import re
import shutil
import subprocess
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path


class QuizParser(HTMLParser):
    """Counts questions and options; verifies each question's basic shape."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.n_questions = 0
        self.option_counts = []  # options per question, in order
        self.errors = []
        self._in_ol = False
        self._in_choices_ul = False
        self._li_stack = []

    def handle_starttag(self, tag, attrs):
        cls = (dict(attrs).get("class") or "").split()
        if tag == "ol" and "questions" in cls:
            if self._in_ol:
                self.errors.append("nested <ol class='questions'>")
            self._in_ol = True
            return
        if not self._in_ol:
            return
        if tag == "ul" and "choices" in cls:
            if self._in_choices_ul:
                self.errors.append("nested <ul class='choices'>")
            self._in_choices_ul = True
            return
        if tag == "li":
            if self._in_choices_ul:
                parent = self._li_stack[-1] if self._li_stack else None
                if parent and parent.get("kind") == "choice":
                    self.errors.append("nested <li> inside a choice <li>")
                elif parent and parent.get("kind") == "q":
                    parent["opts"] += 1
                self._li_stack.append({"kind": "choice"})
            else:
                if self._li_stack:
                    self.errors.append("<li> nested inside a question <li>")
                else:
                    self.n_questions += 1
                self._li_stack.append({"kind": "q", "opts": 0, "stem": False})
        elif tag == "p":
            if self._li_stack and self._li_stack[-1].get("kind") == "q":
                self._li_stack[-1]["stem"] = True

    def handle_endtag(self, tag):
        if tag == "ol" and self._in_ol:
            if self._li_stack:
                self.errors.append("<ol class='questions'> closed with <li> still open")
            self._in_ol = False
            return
        if not self._in_ol:
            return
        if tag == "ul" and self._in_choices_ul:
            self._in_choices_ul = False
            return
        if tag == "li" and self._li_stack:
            node = self._li_stack.pop()
            if node.get("kind") == "q":
                qn = self.n_questions
                if not node["stem"]:
                    self.errors.append(f"question {qn} has no stem <p>")
                if not 3 <= node["opts"] <= 5:
                    self.errors.append(
                        f"question {qn} has {node['opts']} options (expected 3-5)")
                self.option_counts.append(node["opts"])


def strip_comments(html):
    return re.sub(r"<!--.*?-->", "", html, flags=re.S)


def extract_script(html):
    m = re.search(r"<script>(.*?)</script>", strip_comments(html), re.S)
    return m.group(1) if m else None


def extract_key(js):
    m = re.search(r'var KEY = \((.*?)\)\.split\(""\);', js, re.S)
    if not m:
        return None
    return "".join(re.findall(r'"([A-Ea-e]*)"', m.group(1))).upper()


def extract_why_count(js):
    # String-aware scan: find "var WHY = [", then walk chars tracking string state;
    # the array ends at the first top-level ']'. Handles '];' occurring inside
    # entry strings and both single-line and one-entry-per-line formats.
    start = js.find("var WHY = [")
    if start < 0:
        return None
    i = js.find("[", start)
    n, in_str, esc = 0, False, False
    for ch in js[i + 1:]:
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        elif ch == '"':
            in_str = True
            n += 1
        elif ch == "]":
            return n
    return None


def extract_schema_letters(schema_html):
    return re.findall(r'<span class="letter">([A-E])\.', schema_html)


def validate(path, schema_path=None):
    problems = []
    html = strip_comments(Path(path).read_text(encoding="utf-8"))

    for m in re.finditer(r"\{\{[A-Z_]+\}\}", html):
            problems.append(f"unreplaced placeholder {m.group(0)}")

    parser = QuizParser()
    try:
        parser.feed(html)
        parser.close()
    except Exception as exc:  # malformed HTML
        return [f"HTML parse error: {exc}"], None
    problems.extend(parser.errors)
    if parser.n_questions == 0:
        problems.append("no <ol class='questions'> questions found")

    js = extract_script(html)
    if js is None:
        problems.append("no inline <script> found")
    else:
        key = extract_key(js)
        why_n = extract_why_count(js)
        if key is None:
            problems.append("could not extract KEY from inline script")
        else:
            if len(key) != parser.n_questions:
                problems.append(
                    f"KEY has {len(key)} entries but quiz has {parser.n_questions} questions")
            for i, letter in enumerate(key):
                opts = parser.option_counts[i] if i < len(parser.option_counts) else 0
                if opts and ord(letter) - ord("A") + 1 > opts:
                    problems.append(
                        f"question {i + 1}: KEY letter {letter} exceeds {opts} options")
        if why_n is None:
            problems.append("could not extract WHY array from inline script")
        elif parser.n_questions and why_n != parser.n_questions:
            problems.append(f"WHY has {why_n} entries but quiz has {parser.n_questions} questions")
        if shutil.which("node"):
            with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as fh:
                fh.write(js)
                tmp = fh.name
            proc = subprocess.run(["node", "--check", tmp], capture_output=True, text=True)
            if proc.returncode != 0:
                problems.append("inline JS failed node --check:\n" + proc.stderr.strip())

    if schema_path:
        schema_html = Path(schema_path).read_text(encoding="utf-8")
        letters = extract_schema_letters(schema_html)
        key = extract_key(extract_script(html) or "")
        if key is None:
            problems.append("schema check skipped: no quiz KEY")
        elif len(letters) != len(key):
            problems.append(
                f"schema has {len(letters)} answers but quiz KEY has {len(key)}")
        elif "".join(letters) != key:
            diffs = [f"Q{i + 1}: quiz={k} schema={s}"
                     for i, (k, s) in enumerate(zip(key, letters)) if k != s]
            problems.append("schema answers mismatch quiz KEY: " + "; ".join(diffs))
        else:
            print(f"Schema answers match quiz KEY ({len(key)} entries).")

    return problems, parser


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    problems, parser = validate(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    if parser and not problems:
        print(f"PASS: {parser.n_questions} questions, "
              f"options per question {parser.option_counts}")
        return 0
    print("FAIL:" if problems else "FAIL: unknown error")
    for p in problems:
        print(f"  - {p}")
    return 1


if __name__ == "__main__":
    sys.exit(main())