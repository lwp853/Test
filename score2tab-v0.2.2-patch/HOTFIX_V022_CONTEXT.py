from __future__ import annotations

from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "score2tab" / "bass_verify.py"
BACKUP = ROOT / "v0.2.2-hotfix-backup" / "bass_verify.py"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"Could not safely apply {label}: expected one matching block, found {count}."
        )
    return text.replace(old, new, 1)


def main() -> int:
    if not TARGET.is_file():
        raise RuntimeError(
            "Could not find score2tab\\bass_verify.py. Put this hotfix in the "
            "main Score2Tab folder beside RUN_SCORE2TAB.bat."
        )

    text = TARGET.read_text(encoding="utf-8")

    text = replace_once(
        text,
        "def _measure_contexts(part: etree._Element) -> dict[int, tuple[int, int, tuple[int, int]]]:\n"
        "    divisions = 1\n"
        "    time_value = (4, 4)\n"
        "    contexts: dict[int, tuple[int, int, tuple[int, int]]] = {}\n"
        "    for measure in part.findall(\"measure\"):\n",
        "def _measure_contexts(part: etree._Element) -> dict[str, tuple[int, int, tuple[int, int]]]:\n"
        "    divisions = 1\n"
        "    time_value = (4, 4)\n"
        "    contexts: dict[str, tuple[int, int, tuple[int, int]]] = {}\n"
        "    for index, measure in enumerate(part.findall(\"measure\"), start=1):\n",
        "context dictionary declaration",
    )

    text = replace_once(
        text,
        "        contexts[id(measure)] = (divisions, expected, time_value)\n",
        "        measure_key = measure.get(\"number\") or f\"@{index}\"\n"
        "        contexts[measure_key] = (divisions, expected, time_value)\n",
        "stable context key",
    )

    text = replace_once(
        text,
        "            divisions, expected, time_value = contexts[id(measure)]\n",
        "            context = contexts.get(number)\n"
        "            if context is None:\n"
        "                continue\n"
        "            divisions, expected, time_value = context\n",
        "stable context lookup",
    )

    # Compile before changing the installed source.
    compile(text, str(TARGET), "exec")
    BACKUP.parent.mkdir(parents=True, exist_ok=True)
    if not BACKUP.exists():
        shutil.copy2(TARGET, BACKUP)
    TARGET.write_text(text, encoding="utf-8", newline="\n")

    marker = ROOT / "V0.2.2_HOTFIX1_APPLIED.txt"
    marker.write_text(
        "Score2Tab v0.2.2 hotfix 1 applied.\n"
        "Bass verification now uses stable MusicXML measure keys.\n",
        encoding="utf-8",
    )
    print("Score2Tab v0.2.2 hotfix 1 applied successfully.")
    print("Start Score2Tab normally and rerun the PDF.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"HOTFIX FAILED: {type(exc).__name__}: {exc}")
        raise SystemExit(1)
