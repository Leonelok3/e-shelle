#!/usr/bin/env python3
"""Restore files from the specified backup directory into the repository root.

By default this script restores from the most recent folder under scripts/backups/.
It will overwrite current files with the backed-up versions.
"""
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKUPS_DIR = ROOT / 'scripts' / 'backups'


def latest_backup_dir():
    if not BACKUPS_DIR.exists():
        return None
    entries = [d for d in BACKUPS_DIR.iterdir() if d.is_dir()]
    if not entries:
        return None
    return sorted(entries)[-1]


def restore(backup_dir: Path):
    restored = []
    for src in backup_dir.rglob('*'):
        if src.is_file():
            rel = src.relative_to(backup_dir)
            dest = ROOT / rel
            dest_parent = dest.parent
            dest_parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            restored.append(str(rel))
    return restored


def main():
    bk = latest_backup_dir()
    if bk is None:
        print('No backup directories found under', BACKUPS_DIR)
        return
    print('Restoring from backup:', bk)
    restored = restore(bk)
    print('Restored', len(restored), 'files')
    for p in restored[:200]:
        print(' -', p)


if __name__ == '__main__':
    main()
