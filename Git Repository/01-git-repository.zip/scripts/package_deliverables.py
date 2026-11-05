"""Build portable numbered upload files, excluding secrets and local runtime data."""
import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "submissions"
SQL = ROOT / "Database Schema & Data"
EXCLUDED = {".git", ".venv", "venv", "instance", "__pycache__", ".pytest_cache", "submissions"}


def sources():
    # Explicit roots ensure unrelated local files never enter a public artifact.
    files = [ROOT / name for name in ("README.md", "SUBMISSION_GUIDE.md", ".gitignore")]
    for name in ("Functional Web Application", "Database Schema & Data", "API Documentation", "Unit Tests", "Git Repository", "scripts", ".github"):
        for path in (ROOT / name).rglob("*"):
            relative = path.relative_to(ROOT)
            if not path.is_file() or any(part in EXCLUDED for part in relative.parts):
                continue
            if path.name.startswith(".env") or path.name == "secret.key" or path.suffix in (".pyc", ".pyo", ".sqlite3"):
                continue
            files.append(path)
    return sorted(files, key=lambda p: p.relative_to(ROOT).as_posix())


def archive(name, files):
    with ZipFile(OUTPUT / name, "w", compression=ZIP_DEFLATED) as bundle:
        for path in files:
            entry = ZipInfo(path.relative_to(ROOT).as_posix())
            entry.compress_type = ZIP_DEFLATED
            entry.external_attr = 0o644 << 16
            bundle.writestr(entry, path.read_bytes())


def main():
    OUTPUT.mkdir(exist_ok=True)
    combined = "-- Personalized Study Planner: SQLite schema and fictional demo data\n"
    combined += (SQL / "schema.sql").read_text(encoding="utf-8")
    combined += "\n" + (SQL / "sample_data.sql").read_text(encoding="utf-8")
    (SQL / "database.sql").write_text(combined, encoding="utf-8")
    (OUTPUT / "03-database-schema-and-data.sql").write_text(combined, encoding="utf-8")
    (OUTPUT / "04-api-documentation.md").write_bytes((ROOT / "API Documentation" / "API.md").read_bytes())
    all_files = sources()
    archive("01-git-repository.zip", all_files)
    app_roots = {"Functional Web Application", "Database Schema & Data"}
    app_files = [p for p in all_files if p.relative_to(ROOT).parts[0] in app_roots]
    archive("02-functional-web-application.zip", app_files)
    test_roots = app_roots | {"Unit Tests", "scripts"}
    test_files = [p for p in all_files if p.relative_to(ROOT).parts[0] in test_roots]
    archive("05-unit-tests.zip", test_files)
    manifest = []
    for name in ("01-git-repository.zip", "02-functional-web-application.zip", "03-database-schema-and-data.sql", "04-api-documentation.md", "05-unit-tests.zip"):
        data = (OUTPUT / name).read_bytes()
        manifest.append({"file": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    (OUTPUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("Created five upload files and SHA-256 manifest in", OUTPUT)


if __name__ == "__main__":
    main()
