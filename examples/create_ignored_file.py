from pathlib import Path

Path("private.txt").write_text("created\n", encoding="utf-8")
