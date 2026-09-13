"""Back up the database configured by Django, without printing credentials."""
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
from contextlib import closing

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "edu_cm.settings")

import django
django.setup()
from django.conf import settings


def backup(destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True, mode=0o700)
    config = settings.DATABASES["default"]
    engine = config["ENGINE"]
    if engine.endswith("sqlite3"):
        source = Path(config["NAME"]).resolve()
        output = destination / "database.sqlite3"
        if output.exists():
            raise RuntimeError("Le fichier de sauvegarde existe déjà.")
        with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as current, closing(sqlite3.connect(output)) as copy:
            current.backup(copy)
            if copy.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise RuntimeError("Échec de validation SQLite.")
    elif engine.endswith("postgresql") or engine.endswith("postgresql_psycopg2"):
        if not shutil.which("pg_dump") or not shutil.which("pg_restore"):
            raise RuntimeError("Installez les clients PostgreSQL correspondant à la version du serveur.")
        output = destination / "database.dump"
        if output.exists():
            raise RuntimeError("Le fichier de sauvegarde existe déjà.")
        env = dict(os.environ)
        for key, name in [("HOST", "PGHOST"), ("PORT", "PGPORT"), ("USER", "PGUSER"), ("PASSWORD", "PGPASSWORD")]:
            if config.get(key):
                env[name] = str(config[key])
        env["PGCONNECT_TIMEOUT"] = "15"
        for key in ("sslmode", "sslcert", "sslkey", "sslrootcert"):
            if config.get("OPTIONS", {}).get(key):
                env["PG" + key.upper()] = str(config["OPTIONS"][key])
        subprocess.run(["pg_dump", "--format=custom", "--no-owner", "--file", str(output),
                        "--dbname", str(config["NAME"])], env=env, check=True)
        subprocess.run(["pg_restore", "--list", str(output)], check=True, stdout=subprocess.DEVNULL)
    else:
        raise RuntimeError("Moteur de base non pris en charge : sauvegarde manuelle nécessaire.")
    output.chmod(0o600)
    if output.stat().st_size == 0:
        raise RuntimeError("Sauvegarde vide.")
    print(f"Sauvegarde créée et vérifiée : {output}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python deploy/backup_studio_database.py /chemin/sauvegarde")
    backup(sys.argv[1])
