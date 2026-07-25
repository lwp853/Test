from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
import shutil


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent if (HERE.parent / "score2tab").is_dir() else HERE
PACKAGE = ROOT / "score2tab"
STAMP = datetime.now().strftime("%Y%m%d-%H%M%S")
BACKUP = ROOT / "Updates" / "Backups" / f"v0.2.2-hotfix2-{STAMP}"


class PatchError(RuntimeError):
    pass


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise PatchError(f"Could not read {path}: {exc}") from exc


def backup(path: Path) -> None:
    relative = path.relative_to(ROOT)
    target = BACKUP / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, target)


def write_checked(path: Path, content: str) -> None:
    if path.suffix in {".py", ".pyw"}:
        compile(content, str(path), "exec")
    backup(path)
    path.write_text(content, encoding="utf-8", newline="\n")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    count = text.count(old)
    if count != 1:
        raise PatchError(
            f"Could not safely patch {label}: expected one matching block, found {count}."
        )
    return text.replace(old, new, 1)


def patch_app() -> None:
    path = PACKAGE / "app.py"
    text = read(path)
    text = text.replace("Score2Tab 0.2.1", "Score2Tab 0.2.2")
    text = text.replace(
        "Accurate (3 recognition passes)",
        "Accurate (3 passes + bass check)",
    )

    pattern = re.compile(
        r"        default_tuning_display = PRESETS\[\"standard\"\]\.display\n\n"
        r"        self\.input_var = tk\.StringVar\(\)\n"
        r"        self\.output_var = tk\.StringVar\(\n"
        r"            value=str\(self\.settings\.get\(\"output_dir\", \"\"\)\)\n"
        r"        \)\n"
        r"        self\.page_var = tk\.StringVar\(value=\"all\"\)\n"
        r"        self\.audiveris_var = tk\.StringVar\(\n"
        r"            value=str\(detected_audiveris or \"\"\)\n"
        r"        \)\n"
        r"        self\.tuning_var = tk\.StringVar\(value=default_tuning_display\)\n"
        r"        self\.custom_tuning_var = tk\.StringVar\(value=\"E2 A2 D3 G3 B3 E4\"\)\n"
        r"        self\.tempo_var = tk\.StringVar\(value=\"Auto\"\)\n"
        r"        self\.mode_var = tk\.StringVar\(value=\"Accurate \(3 passes \+ bass check\)\"\)\n"
        r"        self\.crop_var = tk\.BooleanVar\(value=True\)\n"
        r"        self\.auto_repair_var = tk\.BooleanVar\(value=True\)\n"
        r"        self\.max_fret_var = tk\.IntVar\(value=24\)\n"
    )
    replacement = '''        saved_tuning_key = str(self.settings.get("tuning_key", "standard"))
        default_tuning_display = next(
            (
                display
                for display, key in TUNING_CHOICES.items()
                if key == saved_tuning_key
            ),
            PRESETS["standard"].display,
        )

        self.input_var = tk.StringVar()
        self.output_var = tk.StringVar(
            value=str(self.settings.get("output_dir", ""))
        )
        self.page_var = tk.StringVar(value=str(self.settings.get("page_spec", "all")))
        self.audiveris_var = tk.StringVar(
            value=str(detected_audiveris or "")
        )
        self.tuning_var = tk.StringVar(value=default_tuning_display)
        self.custom_tuning_var = tk.StringVar(
            value=str(self.settings.get("custom_tuning", "E2 A2 D3 G3 B3 E4"))
        )
        self.tempo_var = tk.StringVar(value=str(self.settings.get("tempo", "Auto")))
        self.mode_var = tk.StringVar(
            value=str(self.settings.get("mode", "Accurate (3 passes + bass check)"))
        )
        self.crop_var = tk.BooleanVar(
            value=bool(self.settings.get("crop_to_music", True))
        )
        self.auto_repair_var = tk.BooleanVar(
            value=bool(self.settings.get("auto_repair", True))
        )
        self.max_fret_var = tk.IntVar(
            value=int(self.settings.get("max_fret", 24) or 24)
        )
'''
    if "saved_tuning_key" not in text:
        text, count = pattern.subn(replacement, text, count=1)
        if count != 1:
            raise PatchError("Could not safely patch saved GUI settings.")

    old_save = '''        _save_settings(
            {
                "audiveris": str(options.audiveris_path or ""),
                "output_dir": str(options.output_dir),
            }
        )
'''
    new_save = '''        _save_settings(
            {
                "audiveris": str(options.audiveris_path or ""),
                "output_dir": str(options.output_dir),
                "page_spec": options.page_spec,
                "tuning_key": options.tuning_key,
                "custom_tuning": options.custom_tuning,
                "tempo": self.tempo_var.get().strip() or "Auto",
                "mode": self.mode_var.get(),
                "crop_to_music": options.crop_to_music,
                "auto_repair": options.auto_repair,
                "max_fret": options.max_fret,
            }
        )
'''
    text = replace_once(text, old_save, new_save, "saved conversion settings")
    write_checked(path, text)


def patch_report() -> None:
    path = PACKAGE / "report.py"
    text = read(path).replace("Score2Tab 0.2.1", "Score2Tab 0.2.2")
    text = text.replace('"version": "0.2.1"', '"version": "0.2.2"')
    write_checked(path, text)


def patch_bass_verify() -> None:
    path = PACKAGE / "bass_verify.py"
    text = read(path)

    context_pattern = re.compile(
        r"def _measure_contexts\(part: etree\._Element\).*?\n\n\ndef _system_layout",
        re.S,
    )
    context_replacement = '''def _measure_contexts(part: etree._Element) -> dict[str, tuple[int, int, tuple[int, int]]]:
    divisions = 1
    time_value = (4, 4)
    contexts: dict[str, tuple[int, int, tuple[int, int]]] = {}
    for index, measure in enumerate(part.findall("measure"), start=1):
        divisions_text = measure.findtext("attributes/divisions")
        if divisions_text:
            try:
                divisions = max(1, int(divisions_text))
            except ValueError:
                pass
        beats_text = measure.findtext("attributes/time/beats")
        beat_type_text = measure.findtext("attributes/time/beat-type")
        if beats_text and beat_type_text:
            try:
                time_value = (int(beats_text), int(beat_type_text))
            except ValueError:
                pass
        beats, beat_type = time_value
        expected = round(divisions * beats * 4 / max(beat_type, 1))
        number = measure.get("number") or str(index)
        contexts[number] = (divisions, expected, time_value)
    return contexts


def _system_layout'''
    text, count = context_pattern.subn(context_replacement, text, count=1)
    if count != 1:
        raise PatchError("Could not safely normalise visual measure contexts.")

    text = text.replace(
        '            divisions, expected, time_value = contexts[id(measure)]\n',
        '            context = contexts.get(number)\n'
        '            if context is None:\n'
        '                continue\n'
        '            divisions, expected, time_value = context\n',
    )

    safe_function = '''def _safe_for_visual_insert(candidate: VisualCandidate, target_midi: int) -> bool:
    measure = candidate.measure
    if _has_low_note(measure, target_midi):
        return False
    if candidate.expected_duration != candidate.divisions * 4:
        return False
    if measure.find("backup") is not None or measure.find("forward") is not None:
        return False
    if _measure_cursor_end(measure) != candidate.expected_duration:
        return False
    voices = {
        note.findtext("voice", "1")
        for note in measure.findall("note")
        if _pitch_midi(note) is not None
    }
    return len(voices) <= 1


'''
    marker = "def _insert_open_bass(candidate: VisualCandidate, target_midi: int) -> bool:\n"
    if "def _safe_for_visual_insert" not in text:
        text = replace_once(text, marker, safe_function + marker, "visual insertion safety")

    insert_start = '''def _insert_open_bass(candidate: VisualCandidate, target_midi: int) -> bool:
    measure = candidate.measure
    if _has_low_note(measure, target_midi):
        return False
'''
    insert_new = '''def _insert_open_bass(candidate: VisualCandidate, target_midi: int) -> bool:
    measure = candidate.measure
    if not _safe_for_visual_insert(candidate, target_midi):
        return False
'''
    text = replace_once(text, insert_start, insert_new, "visual insertion guard")

    text = re.sub(
        r"if len\(group\) >= 2 and min\(candidate\.score for candidate in group\) >= [0-9.]+:",
        "if len(group) >= 2 and min(candidate.score for candidate in group) >= 0.75:",
        text,
        count=1,
    )

    old_decision = '''        high_confidence = candidate.score >= 0.155
        repeated_evidence = id(candidate) in grouped_ids
        should_insert = high_confidence or repeated_evidence
'''
    new_decision = '''        high_confidence = candidate.score >= 0.75
        review_confidence = candidate.score >= 0.45
        repeated_evidence = id(candidate) in grouped_ids
        if not review_confidence:
            continue
        should_insert = high_confidence and _safe_for_visual_insert(candidate, target_midi)
'''
    text = replace_once(text, old_decision, new_decision, "visual confidence thresholds")

    old_detail = '''                        f"The lower-staff detector found a possible {pitch_name} notehead "
                        f"(confidence {candidate.score:.2f}) but did not alter the score automatically."
'''
    new_detail = '''                        f"The lower-staff detector found a possible {pitch_name} notehead "
                        f"(confidence {candidate.score:.2f}) but did not alter the score automatically. "
                        + (
                            "The measure already contains complex voice timing, so automatic insertion was blocked."
                            if high_confidence and not should_insert
                            else "Automatic insertion requires confidence of at least 0.75."
                        )
'''
    text = replace_once(text, old_detail, new_detail, "visual review explanation")
    write_checked(path, text)


def patch_musicxml() -> None:
    path = PACKAGE / "musicxml.py"
    text = read(path)

    helpers = '''def remove_false_barre_harmony(root: etree._Element) -> list[Issue]:
    """Remove Audiveris chord frames produced by misreading BII as B11."""
    issues: list[Issue] = []
    for harmony in list(root.findall(".//harmony")):
        root_step = (harmony.findtext("root/root-step") or "").strip().upper()
        kind = harmony.find("kind")
        kind_text = ""
        if kind is not None:
            kind_text = " ".join(
                part for part in ((kind.text or ""), kind.get("text", "")) if part
            ).strip().upper().replace(" ", "")
        if root_step == "B" and harmony.find("frame") is not None and "11" in kind_text:
            parent = harmony.getparent()
            if parent is not None:
                parent.remove(harmony)
                issues.append(
                    Issue(
                        Severity.INFO,
                        "Removed a false B11 chord frame created from a BII barre marking.",
                        code="auto-repair-false-barre-harmony",
                    )
                )
    return issues


def _insert_before_right_barline(measure: etree._Element, element: etree._Element) -> None:
    for index, existing in enumerate(measure):
        if existing.tag == "barline" and existing.get("location") == "right":
            measure.insert(index, element)
            return
    measure.append(element)


def fill_simple_underflows(root: etree._Element) -> list[Issue]:
    """Complete simple underfilled single-voice measures with an explicit rest."""
    issues: list[Issue] = []
    part = _first_part(root)
    current_divisions = 1
    current_time = (4, 4)
    for index, measure in enumerate(part.findall("measure"), start=1):
        number = measure.get("number") or str(index)
        divisions_text = measure.findtext("attributes/divisions")
        if divisions_text:
            try:
                current_divisions = max(1, int(divisions_text))
            except ValueError:
                pass
        expected, current_time = _expected_measure_duration(
            measure, current_divisions, current_time
        )
        cursor, maximum, negative = _measure_cursor(measure)
        is_pickup = index == 1 or measure.get("implicit") == "yes" or number in {"0", "X0"}
        if is_pickup or negative or maximum >= expected or cursor != maximum:
            continue
        if measure.find("backup") is not None or measure.find("forward") is not None:
            continue
        missing = expected - maximum
        if missing <= 0 or missing > expected // 2:
            continue
        rest = etree.Element("note")
        etree.SubElement(rest, "rest")
        etree.SubElement(rest, "duration").text = str(missing)
        etree.SubElement(rest, "voice").text = "1"
        note_type = {
            current_divisions * 4: "whole",
            current_divisions * 2: "half",
            current_divisions: "quarter",
            max(1, current_divisions // 2): "eighth",
        }.get(missing)
        if note_type:
            etree.SubElement(rest, "type").text = note_type
        _insert_before_right_barline(measure, rest)
        issues.append(
            Issue(
                Severity.WARNING,
                "Inserted a rest to complete an underfilled measure.",
                measure=number,
                code="auto-repair-underflow-rest",
                detail=(
                    f"The recognised music contained {maximum} of {expected} duration units. "
                    f"Added a {missing}-unit rest for valid MusicXML structure; the printed source still needs checking."
                ),
            )
        )
    return issues


'''
    marker = "def clean_musicxml(\n"
    if "def remove_false_barre_harmony" not in text:
        text = replace_once(text, marker, helpers + marker, "MusicXML cleanup helpers")

    old_body = '''    configure_guitar_part(root, tuning)
    if tempo is not None:
        set_tempo(root, tempo)

    repair_issues = repair_polyphony(root) if auto_repair else []
    signatures = measure_signatures(root)
    assigned, unassigned, tab_issues = assign_tablature(root, tuning, max_fret)
    issues = [*repair_issues, *validate_musicxml(root), *tab_issues]
'''
    new_body = '''    configure_guitar_part(root, tuning)
    cleanup_issues = remove_false_barre_harmony(root)
    if tempo is not None:
        set_tempo(root, tempo)

    repair_issues = repair_polyphony(root) if auto_repair else []
    underflow_issues = fill_simple_underflows(root) if auto_repair else []
    signatures = measure_signatures(root)
    assigned, unassigned, tab_issues = assign_tablature(root, tuning, max_fret)
    issues = [
        *cleanup_issues,
        *repair_issues,
        *underflow_issues,
        *validate_musicxml(root),
        *tab_issues,
    ]
'''
    text = replace_once(text, old_body, new_body, "final MusicXML cleanup")
    write_checked(path, text)


def patch_changelog() -> None:
    path = ROOT / "CHANGELOG.md"
    if not path.is_file():
        return
    text = read(path)
    heading = "### Hotfix 2"
    if heading not in text:
        addition = '''\n### Hotfix 2\n\n- Raised automatic visual bass insertion to 0.75 confidence.\n- Ignored detections below 0.45 and kept medium-confidence detections review-only.\n- Blocked visual insertion in measures with complex or incomplete voice timing.\n- Added simple underflow-rest completion for structurally incomplete single-voice bars.\n- Removed false B11 chord frames caused by BII barre recognition.\n- Remembered tuning, tempo, mode, crop, repair and fret settings.\n- Corrected report metadata to version 0.2.2.\n'''
        text += addition
        path.write_text(text, encoding="utf-8", newline="\n")


def main() -> int:
    print()
    print("Score2Tab v0.2.2 hotfix 2")
    print("=============================")
    print()
    required = [
        PACKAGE / "app.py",
        PACKAGE / "bass_verify.py",
        PACKAGE / "musicxml.py",
        PACKAGE / "report.py",
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise PatchError("Missing required Score2Tab files: " + ", ".join(missing))

    patch_app()
    patch_report()
    patch_bass_verify()
    patch_musicxml()
    patch_changelog()

    marker = ROOT / "Updates" / "V0.2.2_HOTFIX2_APPLIED.txt"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(
        "Score2Tab v0.2.2 hotfix 2 applied successfully.\n"
        f"Backups: {BACKUP}\n",
        encoding="utf-8",
    )
    print("Hotfix 2 applied successfully.")
    print(f"Backups: {BACKUP}")
    print()
    print("Start Score2Tab with RUN_SCORE2TAB.bat.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except PatchError as exc:
        print(f"HOTFIX FAILED: {exc}")
        raise SystemExit(1)
