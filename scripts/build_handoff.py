"""Package the handoff CLI and Codex adapter into one dependency-free zipapp."""
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / "dist/claimtrail-handoff.pyz"

files = {
    "__main__.py": b"from handoff import main\nraise SystemExit(main())\n",
    "LICENSE": (ROOT / "LICENSE").read_bytes(),
}
for name in ("handoff.py", "scope_verification.py", "cli_paths.py"):
    files[name] = (ROOT / "src" / name).read_bytes()

DESTINATION.parent.mkdir(parents=True, exist_ok=True)
with TemporaryDirectory(prefix="claimtrail-handoff-", dir=DESTINATION.parent) as directory:
    staging = Path(directory) / DESTINATION.name
    with ZipFile(staging, "w") as archive:
        for name, contents in sorted(files.items()):
            archive.writestr(ZipInfo(name), contents, compress_type=ZIP_DEFLATED, compresslevel=9)
    staging.replace(DESTINATION)
print(DESTINATION)
