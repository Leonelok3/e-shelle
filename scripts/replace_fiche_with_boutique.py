#!/usr/bin/env python3
"""Replace occurrences of the word 'fiche' with 'boutique' in non-code files.

Rules:
- Operates on extensions: .html, .md, .txt, .css, .js, .json, .svg, .po, .rst, .yml, .yaml
- Skips any path that contains /migrations/ or ends with .py
- Uses word-boundary regex so 'affiche' is NOT modified.
- Creates backups under scripts/backups/<timestamp>/
"""
import os
import re
import shutil
import sys
from datetime import datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
BACKUP_DIR = os.path.join(ROOT, 'scripts', 'backups', datetime.now().strftime('%Y%m%d_%H%M%S'))
ALLOWED_EXTS = {'.html', '.md', '.txt', '.css', '.js', '.json', '.svg', '.po', '.rst', '.yml', '.yaml'}
EXCLUDE_DIR_PARTS = ('/migrations/', '\\migrations\\')

REPLACEMENTS = [
    (re.compile(r"\bFiches\b"), 'Boutiques'),
    (re.compile(r"\bfiches\b"), 'boutiques'),
    (re.compile(r"\bFiche\b"), 'Boutique'),
    (re.compile(r"\bfiche\b"), 'boutique'),
]


def should_skip(path):
    low = path.replace('\\', '/')
    for part in EXCLUDE_DIR_PARTS:
        if part in low:
            return True
    return False


def process_file(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            text = f.read()
    except Exception:
        return False, 0

    new_text = text
    total_changes = 0
    for pattern, repl in REPLACEMENTS:
        new_text, n = pattern.subn(repl, new_text)
        total_changes += n

    if total_changes > 0 and new_text != text:
        # backup
        rel = os.path.relpath(path, ROOT)
        backup_path = os.path.join(BACKUP_DIR, rel)
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        shutil.copy2(path, backup_path)
        # write
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_text)
        return True, total_changes
    return False, 0


def main():
    changed_files = []
    os.makedirs(BACKUP_DIR, exist_ok=True)
    for dirpath, dirnames, filenames in os.walk(ROOT):
        # skip .venv and backups
        if '/.venv/' in dirpath.replace('\\', '/') or '/scripts/backups/' in dirpath.replace('\\', '/'):
            continue
        for fn in filenames:
            _, ext = os.path.splitext(fn)
            if ext.lower() not in ALLOWED_EXTS:
                continue
            full = os.path.join(dirpath, fn)
            if should_skip(full):
                continue
            changed, count = process_file(full)
            if changed:
                changed_files.append((full, count))

    # report
    report_path = os.path.join(ROOT, 'scripts', 'replace_report.txt')
    with open(report_path, 'w', encoding='utf-8') as r:
        r.write(f'Replace report generated: {datetime.now().isoformat()}\n')
        r.write(f'Root: {ROOT}\n')
        r.write(f'Backup dir: {BACKUP_DIR}\n')
        r.write(f'Files changed: {len(changed_files)}\n')
        for p, c in changed_files:
            r.write(f'{p}: {c} replacements\n')

    print('Done. Files changed:', len(changed_files))
    if changed_files:
        for p, c in changed_files[:200]:
            print(f' - {os.path.relpath(p, ROOT)} ({c})')
    print('Backup directory:', BACKUP_DIR)
    print('Report:', report_path)


if __name__ == '__main__':
    main()
