from __future__ import annotations

from pathlib import Path
import shutil
import sys


ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT / "score2tab"
BACKUP = ROOT / "v0.2.1-backup"


class PatchError(RuntimeError):
    pass


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise PatchError(f"Could not read {path}: {exc}") from exc


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    count = text.count(old)
    if count != 1:
        raise PatchError(f"Could not safely patch {label}: expected one matching code block, found {count}.")
    return text.replace(old, new, 1)


def backup(path: Path) -> None:
    relative = path.relative_to(ROOT)
    target = BACKUP / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        shutil.copy2(path, target)


def write_checked(path: Path, content: str) -> None:
    if path.suffix in {".py", ".pyw"}:
        compile(content, str(path), "exec")
    backup(path)
    path.write_text(content, encoding="utf-8", newline="\n")


def patch_pipeline() -> None:
    path = PACKAGE / "pipeline.py"
    text = read(path)
    text = replace_once(
        text,
        "from .preprocess import preprocess_pdf\n",
        "from .preprocess import preprocess_pdf\nfrom .bass_verify import verify_missing_open_bass\n",
        "pipeline import",
    )
    marker = "    # De-duplicate after comparisons from multiple recognition passes.\n"
    block = '''    if input_path.suffix.lower() == ".pdf" and options.accurate_mode:\n        progress("Checking the source image for omitted sustained bass notes…")\n        visual_tuning = _candidate_tuning(final_mxl, options)\n        visual_issues, inserted_bass = verify_missing_open_bass(\n            input_path,\n            final_mxl,\n            options.page_spec,\n            visual_tuning,\n            job_dir / "Visual Verification",\n            progress=progress,\n        )\n        issues.extend(visual_issues)\n        if inserted_bass:\n            visually_cleaned = job_dir / f"{stem}_after_visual_bass_check.mxl"\n            visual_outcome = clean_musicxml(\n                final_mxl,\n                visually_cleaned,\n                tuning=visual_tuning,\n                tempo=options.tempo,\n                max_fret=options.max_fret,\n                auto_repair=options.auto_repair,\n            )\n            shutil.copy2(visually_cleaned, final_mxl)\n            issues.extend(visual_outcome.issues)\n            final_signatures = visual_outcome.measure_signatures\n            assigned_notes = visual_outcome.assigned_notes\n            unassigned_notes = visual_outcome.unassigned_notes\n            tuning_display = visual_tuning.display\n\n'''
    text = replace_once(text, marker, block + marker, "visual verification stage")
    write_checked(path, text)


def patch_preprocess() -> None:
    path = PACKAGE / "preprocess.py"
    text = read(path)
    old = '''            width_points = image.width / dpi * 72.0\n            height_points = image.height / dpi * 72.0\n            target_page = result_pdf.new_page(\n                width=width_points,\n                height=height_points,\n            )\n'''
    new = '''            # Audiveris normally rasterises PDF pages at about 300 dpi.\n            # Keep higher-resolution passes physically larger so the 400 dpi\n            # image reaches Audiveris with a genuinely larger staff scale.\n            audiveris_scale_dpi = min(dpi, 300)\n            width_points = image.width / audiveris_scale_dpi * 72.0\n            height_points = image.height / audiveris_scale_dpi * 72.0\n            if dpi > audiveris_scale_dpi:\n                action += (\n                    f"; genuine {dpi} dpi raster presented at "\n                    f"{audiveris_scale_dpi} dpi Audiveris scale"\n                )\n            target_page = result_pdf.new_page(\n                width=width_points,\n                height=height_points,\n            )\n'''
    text = replace_once(text, old, new, "genuine 400 dpi output")
    write_checked(path, text)


def patch_app() -> None:
    path = PACKAGE / "app.py"
    text = read(path)
    text = text.replace("Score2Tab 0.2.1", "Score2Tab 0.2.2")
    text = text.replace(
        "Accurate (3 recognition passes)",
        "Accurate (3 passes + bass check)",
    )
    write_checked(path, text)


def patch_version() -> None:
    path = PACKAGE / "__init__.py"
    text = read(path).replace('__version__ = "0.2.1"', '__version__ = "0.2.2"')
    write_checked(path, text)


def patch_readme() -> None:
    path = ROOT / "README.md"
    if not path.exists():
        return
    text = read(path)
    text = text.replace("Score2Tab 0.2.1 for Windows", "Score2Tab 0.2.2 for Windows", 1)
    heading = "## What changed in 0.2.2"
    if heading not in text:
        addition = '''\n\n## What changed in 0.2.2\n\n- The 400 dpi recognition pass is now presented to Audiveris at a genuinely\n  larger raster scale instead of being reduced to the same effective scale as\n  the 300 dpi pass.\n- Accurate mode performs a 600 dpi source-image check below each staff.\n- The visual check searches for hollow open-sixth-string whole notes and their\n  ledger-line pattern when the recognised MusicXML contains melody but no bass.\n- Repeated high-confidence detections can be inserted as a separate bass voice,\n  with open-string tablature, and are listed individually in the quality report.\n- Evidence images are saved under `Working Files/Visual Verification/`.\n\nThe visual repair remains deliberately narrow: it does not invent arbitrary\nharmony or infer short bass notes. Lower-confidence detections are highlighted\nfor review without changing the MusicXML.\n'''
        text += addition
    path.write_text(text, encoding="utf-8", newline="\n")


def patch_changelog() -> None:
    path = ROOT / "CHANGELOG.md"
    if not path.exists():
        return
    text = read(path)
    if "## 0.2.2" not in text:
        entry = '''## 0.2.2\n\n- Made the 400 dpi Audiveris pass genuinely higher scale.\n- Added 600 dpi lower-staff image verification.\n- Added conservative detection and insertion of omitted open-string whole-note\n  pedal basses.\n- Added per-measure visual-repair reporting and annotated evidence images.\n\n'''
        text = text.replace("# Changelog\n\n", "# Changelog\n\n" + entry, 1)
    path.write_text(text, encoding="utf-8", newline="\n")


def main() -> int:
    print()
    print("Score2Tab v0.2.2 patch")
    print("========================")
    print()
    required = [
        PACKAGE / "pipeline.py",
        PACKAGE / "preprocess.py",
        PACKAGE / "app.py",
        PACKAGE / "__init__.py",
        PACKAGE / "bass_verify.py",
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
    if missing:
        raise PatchError(
            "This patch must be extracted into the existing Score2Tab v0.2.1 folder. "
            "Missing: " + ", ".join(missing)
        )

    # Compile the newly supplied module before touching the installed source.
    compile(read(PACKAGE / "bass_verify.py"), str(PACKAGE / "bass_verify.py"), "exec")
    patch_pipeline()
    patch_preprocess()
    patch_app()
    patch_version()
    patch_readme()
    patch_changelog()

    marker = ROOT / "V0.2.2_PATCH_APPLIED.txt"
    marker.write_text(
        "Score2Tab v0.2.2 patch applied successfully.\n"
        "Original edited files are stored in v0.2.1-backup.\n",
        encoding="utf-8",
    )
    print("Patch applied successfully.")
    print(f"Backups: {BACKUP}")
    print()
    print("Start the app normally with RUN_SCORE2TAB.bat.")
    print("Use Accurate (3 passes + bass check) for the Conde Claros test.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except PatchError as exc:
        print(f"PATCH FAILED: {exc}")
        raise SystemExit(1)
