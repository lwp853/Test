from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image, ImageDraw, ImageOps

try:
    import pymupdf as fitz
except ImportError:  # PyMuPDF versions before the pymupdf alias
    import fitz  # type: ignore[no-redef]

from lxml import etree

from .model import Issue, Severity
from .musicxml import load_musicxml, save_mxl
from .preprocess import detect_staff_lines, parse_page_spec
from .tunings import Tuning, midi_to_components


Progress = Callable[[str], None]
_DIATONIC = {"C": 0, "D": 1, "E": 2, "F": 3, "G": 4, "A": 5, "B": 6}


@dataclass(slots=True)
class VisualCandidate:
    measure: etree._Element
    measure_number: str
    page_slot: int
    system_index: int
    x: float
    y: float
    gap: float
    score: float
    outer_dark: float
    inner_dark: float
    ledger_support: float
    expected_duration: int
    divisions: int


def _pitch_midi(note: etree._Element) -> int | None:
    pitch = note.find("pitch")
    if pitch is None:
        return None
    step = pitch.findtext("step")
    octave = pitch.findtext("octave")
    if not step or octave is None:
        return None
    semitone = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}.get(step.upper())
    if semitone is None:
        return None
    try:
        alter = int(float(pitch.findtext("alter", "0")))
        return (int(octave) + 1) * 12 + semitone + alter
    except ValueError:
        return None


def _duration(element: etree._Element) -> int:
    try:
        return int(element.findtext("duration", "0"))
    except ValueError:
        return 0


def _measure_cursor_end(measure: etree._Element) -> int:
    cursor = 0
    for element in measure:
        if element.tag == "backup":
            cursor -= _duration(element)
        elif element.tag == "forward":
            cursor += _duration(element)
        elif element.tag == "note":
            if element.find("chord") is None and element.find("grace") is None:
                cursor += _duration(element)
    return max(cursor, 0)


def _measure_contexts(part: etree._Element) -> dict[int, tuple[int, int, tuple[int, int]]]:
    divisions = 1
    time_value = (4, 4)
    contexts: dict[int, tuple[int, int, tuple[int, int]]] = {}
    for measure in part.findall("measure"):
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
        contexts[id(measure)] = (divisions, expected, time_value)
    return contexts


def _system_layout(part: etree._Element) -> dict[tuple[int, int], list[etree._Element]]:
    systems: dict[tuple[int, int], list[etree._Element]] = defaultdict(list)
    page_slot = 0
    system_index = 0
    for index, measure in enumerate(part.findall("measure")):
        print_element = measure.find("print")
        if index and print_element is not None:
            if print_element.get("new-page") == "yes":
                page_slot += 1
                system_index = 0
            elif print_element.get("new-system") == "yes":
                system_index += 1
        systems[(page_slot, system_index)].append(measure)
    return dict(systems)


def _render_selected_pages(pdf_path: Path, page_spec: str, dpi: int = 600) -> list[Image.Image]:
    source = fitz.open(pdf_path)
    try:
        selected = parse_page_spec(page_spec, source.page_count)
        pages: list[Image.Image] = []
        matrix = fitz.Matrix(dpi / 72.0, dpi / 72.0)
        for page_index in selected:
            pixmap = source[page_index].get_pixmap(
                matrix=matrix,
                colorspace=fitz.csGRAY,
                alpha=False,
            )
            pages.append(Image.frombytes("L", (pixmap.width, pixmap.height), pixmap.samples))
        return pages
    finally:
        source.close()


def _longest_true_run(mask: np.ndarray) -> tuple[int, int] | None:
    indices = np.flatnonzero(mask)
    if not indices.size:
        return None
    breaks = np.where(np.diff(indices) > 1)[0] + 1
    groups = [group for group in np.split(indices, breaks) if group.size]
    best = max(groups, key=len)
    return int(best[0]), int(best[-1]) + 1


def _staff_span(image: Image.Image, lines: tuple[float, float, float, float, float]) -> tuple[int, int]:
    array = np.asarray(image.convert("L"))
    rows: list[np.ndarray] = []
    for line in lines:
        y = int(round(line))
        top = max(0, y - 2)
        bottom = min(array.shape[0], y + 3)
        rows.append(array[top:bottom].min(axis=0))
    line_stack = np.stack(rows, axis=0)
    mask = (line_stack < 205).sum(axis=0) >= 3
    run = _longest_true_run(mask)
    if run is None or run[1] - run[0] < image.width * 0.35:
        return round(image.width * 0.05), round(image.width * 0.95)
    return run


def _measure_segments(
    measures: list[etree._Element],
    left: int,
    right: int,
) -> list[tuple[etree._Element, float, float]]:
    widths: list[float] = []
    for measure in measures:
        try:
            width = float(measure.get("width", "0"))
        except ValueError:
            width = 0.0
        widths.append(width if width > 0 else 1.0)
    total = sum(widths) or float(len(measures) or 1)
    cursor = float(left)
    available = max(float(right - left), 1.0)
    segments: list[tuple[etree._Element, float, float]] = []
    for measure, width in zip(measures, widths, strict=True):
        next_cursor = cursor + available * width / total
        segments.append((measure, cursor, next_cursor))
        cursor = next_cursor
    return segments


def _diatonic_number(midi: int) -> int:
    step, _, octave = midi_to_components(midi)
    return octave * 7 + _DIATONIC[step]


def _expected_y(lines: tuple[float, float, float, float, float], target_midi: int) -> tuple[float, float]:
    gap = float(np.median(np.diff(lines)))
    bottom_line = lines[-1]
    bottom_e4 = 64
    steps_below = _diatonic_number(bottom_e4) - _diatonic_number(target_midi)
    return bottom_line + steps_below * gap * 0.5, gap


def _ring_metrics(array: np.ndarray, x: float, y: float, gap: float) -> tuple[float, float, float]:
    radius_x = max(4, round(gap * 0.66))
    radius_y = max(3, round(gap * 0.46))
    x0 = max(0, round(x) - radius_x - 2)
    x1 = min(array.shape[1], round(x) + radius_x + 3)
    y0 = max(0, round(y) - radius_y - 2)
    y1 = min(array.shape[0], round(y) + radius_y + 3)
    patch = array[y0:y1, x0:x1]
    if patch.size == 0:
        return 0.0, 1.0, -1.0
    yy, xx = np.mgrid[y0:y1, x0:x1]
    normalized = ((xx - x) / radius_x) ** 2 + ((yy - y) / radius_y) ** 2
    outer_mask = (normalized >= 0.48) & (normalized <= 1.15)
    inner_mask = normalized <= 0.30
    if not outer_mask.any() or not inner_mask.any():
        return 0.0, 1.0, -1.0
    dark = patch < 175
    outer_dark = float(dark[outer_mask].mean())
    inner_dark = float(dark[inner_mask].mean())
    score = outer_dark - 0.65 * inner_dark
    return outer_dark, inner_dark, score


def _ledger_support(
    array: np.ndarray,
    x: float,
    lines: tuple[float, float, float, float, float],
    y: float,
    gap: float,
) -> float:
    bottom = lines[-1]
    ledger_rows: list[float] = []
    ledger_y = bottom + gap
    while ledger_y < y - gap * 0.20:
        ledger_rows.append(ledger_y)
        ledger_y += gap
    if not ledger_rows:
        return 0.0
    half_width = max(4, round(gap * 1.05))
    x0 = max(0, round(x) - half_width)
    x1 = min(array.shape[1], round(x) + half_width + 1)
    supports = []
    for row in ledger_rows:
        y0 = max(0, round(row) - 2)
        y1 = min(array.shape[0], round(row) + 3)
        strip = array[y0:y1, x0:x1]
        supports.append(float((strip < 185).mean()) if strip.size else 0.0)
    return float(np.mean(supports))


def _find_open_bass_notehead(
    image: Image.Image,
    lines: tuple[float, float, float, float, float],
    x0: float,
    x1: float,
    target_midi: int,
) -> tuple[float, float, float, float, float, float] | None:
    expected_y, gap = _expected_y(lines, target_midi)
    if expected_y < 0 or expected_y >= image.height:
        return None
    width = max(x1 - x0, 1.0)
    search_left = max(0, round(x0 + width * 0.035))
    search_right = min(image.width, round(x0 + width * 0.48))
    if search_right <= search_left:
        return None
    array = np.asarray(ImageOps.autocontrast(image.convert("L"), cutoff=(0.2, 0.2)))
    x_step = max(2, round(gap * 0.10))
    y_step = max(1, round(gap * 0.08))
    y_radius = max(2, round(gap * 0.42))
    best: tuple[float, float, float, float, float, float] | None = None
    for y in range(round(expected_y) - y_radius, round(expected_y) + y_radius + 1, y_step):
        if not 0 <= y < image.height:
            continue
        for x in range(search_left, search_right + 1, x_step):
            outer, inner, ring = _ring_metrics(array, x, y, gap)
            if outer < 0.15 or inner > 0.64:
                continue
            ledger = _ledger_support(array, x, lines, y, gap)
            score = ring + 0.28 * ledger
            candidate = (score, float(x), float(y), outer, inner, ledger)
            if best is None or candidate[0] > best[0]:
                best = candidate
    if best is None or best[0] < 0.070:
        return None
    score, x, y, outer, inner, ledger = best
    return x, y, gap, score, outer, inner, ledger


def _has_pitched_notes(measure: etree._Element) -> bool:
    return any(_pitch_midi(note) is not None for note in measure.findall("note"))


def _has_low_note(measure: etree._Element, target_midi: int) -> bool:
    return any(
        pitch is not None and pitch <= target_midi + 1
        for pitch in (_pitch_midi(note) for note in measure.findall("note"))
    )


def _next_bass_voice(measure: etree._Element) -> str:
    used: set[int] = set()
    for note in measure.findall("note"):
        try:
            used.add(int(note.findtext("voice", "1")))
        except ValueError:
            pass
    voice = 2
    while voice in used:
        voice += 1
    return str(voice)


def _insert_before_right_barline(measure: etree._Element, element: etree._Element) -> None:
    for index, existing in enumerate(measure):
        if existing.tag == "barline" and existing.get("location") == "right":
            measure.insert(index, element)
            return
    measure.append(element)


def _insert_open_bass(candidate: VisualCandidate, target_midi: int) -> bool:
    measure = candidate.measure
    if _has_low_note(measure, target_midi):
        return False
    # This first visual repair is deliberately restricted to a complete 4/4
    # whole-note pedal. Other durations remain review-only until validated.
    if candidate.expected_duration != candidate.divisions * 4:
        return False
    cursor = _measure_cursor_end(measure)
    if cursor:
        backup = etree.Element("backup")
        etree.SubElement(backup, "duration").text = str(cursor)
        _insert_before_right_barline(measure, backup)

    note = etree.Element("note")
    pitch = etree.SubElement(note, "pitch")
    step, alter, octave = midi_to_components(target_midi)
    etree.SubElement(pitch, "step").text = step
    if alter is not None:
        etree.SubElement(pitch, "alter").text = str(alter)
    etree.SubElement(pitch, "octave").text = str(octave)
    etree.SubElement(note, "duration").text = str(candidate.expected_duration)
    etree.SubElement(note, "voice").text = _next_bass_voice(measure)
    etree.SubElement(note, "type").text = "whole"
    etree.SubElement(note, "staff").text = "1"
    notations = etree.SubElement(note, "notations")
    technical = etree.SubElement(notations, "technical")
    etree.SubElement(technical, "fret").text = "0"
    etree.SubElement(technical, "string").text = "6"
    _insert_before_right_barline(measure, note)
    return True


def _consecutive_groups(candidates: list[VisualCandidate]) -> dict[str, list[VisualCandidate]]:
    numbered = sorted(
        (candidate for candidate in candidates if candidate.measure_number.isdigit()),
        key=lambda item: int(item.measure_number),
    )
    groups: dict[str, list[VisualCandidate]] = {}
    current: list[VisualCandidate] = []
    for candidate in numbered:
        if current and int(candidate.measure_number) != int(current[-1].measure_number) + 1:
            key = current[0].measure_number
            groups[key] = current
            current = []
        current.append(candidate)
    if current:
        groups[current[0].measure_number] = current
    return groups


def verify_missing_open_bass(
    source_pdf: Path,
    musicxml_path: Path,
    page_spec: str,
    tuning: Tuning,
    evidence_dir: Path,
    progress: Progress = lambda _: None,
) -> tuple[list[Issue], int]:
    """Detect omitted whole-note open-sixth-string bass notes from page pixels.

    The routine does not infer arbitrary harmony. It searches only for a hollow
    notehead at the written pitch of the lowest open string, with matching
    ledger-line evidence, in a 4/4 measure whose recognised XML contains melody
    but no lower note. Repeated detections are stronger than isolated marks.
    """
    loaded = load_musicxml(musicxml_path)
    root = loaded.root
    part = root.find("part")
    if part is None:
        return [], 0

    target_midi = tuning.open_midi_by_string[6] + 12
    contexts = _measure_contexts(part)
    systems = _system_layout(part)
    pages = _render_selected_pages(source_pdf, page_spec, dpi=600)
    evidence_dir.mkdir(parents=True, exist_ok=True)

    detections: list[VisualCandidate] = []
    annotated = [page.convert("RGB") for page in pages]

    for (page_slot, system_index), measures in systems.items():
        if page_slot >= len(pages):
            continue
        page = pages[page_slot]
        staff_detection = detect_staff_lines(page)
        if system_index >= len(staff_detection.groups):
            continue
        lines = staff_detection.groups[system_index]
        left, right = _staff_span(page, lines)
        for measure, x0, x1 in _measure_segments(measures, left, right):
            number = measure.get("number") or "?"
            divisions, expected, time_value = contexts[id(measure)]
            if time_value != (4, 4):
                continue
            if not _has_pitched_notes(measure) or _has_low_note(measure, target_midi):
                continue
            found = _find_open_bass_notehead(page, lines, x0, x1, target_midi)
            if found is None:
                continue
            x, y, gap, score, outer, inner, ledger = found
            detections.append(
                VisualCandidate(
                    measure=measure,
                    measure_number=number,
                    page_slot=page_slot,
                    system_index=system_index,
                    x=x,
                    y=y,
                    gap=gap,
                    score=score,
                    outer_dark=outer,
                    inner_dark=inner,
                    ledger_support=ledger,
                    expected_duration=expected,
                    divisions=divisions,
                )
            )

    grouped_ids: set[int] = set()
    for group in _consecutive_groups(detections).values():
        if len(group) >= 2 and min(candidate.score for candidate in group) >= 0.078:
            grouped_ids.update(id(candidate) for candidate in group)

    issues: list[Issue] = []
    inserted = 0
    step, alter, octave = midi_to_components(target_midi)
    pitch_name = f"{step}{'#' if alter == 1 else 'b' if alter == -1 else ''}{octave}"

    for candidate in detections:
        high_confidence = candidate.score >= 0.155
        repeated_evidence = id(candidate) in grouped_ids
        should_insert = high_confidence or repeated_evidence
        draw = ImageDraw.Draw(annotated[candidate.page_slot])
        radius_x = max(8, round(candidate.gap * 0.85))
        radius_y = max(6, round(candidate.gap * 0.65))
        box = (
            round(candidate.x - radius_x),
            round(candidate.y - radius_y),
            round(candidate.x + radius_x),
            round(candidate.y + radius_y),
        )
        draw.rectangle(box, outline=(0, 0, 0), width=max(2, round(candidate.gap * 0.08)))
        draw.text((box[0], max(0, box[1] - 16)), f"m{candidate.measure_number} {candidate.score:.2f}", fill=(0, 0, 0))

        if should_insert and _insert_open_bass(candidate, target_midi):
            inserted += 1
            issues.append(
                Issue(
                    Severity.WARNING,
                    f"Inserted a visually detected {pitch_name} pedal bass.",
                    measure=candidate.measure_number,
                    code="auto-repair-visual-bass",
                    detail=(
                        "A hollow lower notehead and its ledger-line pattern were visible in the source, "
                        "while the recognised MusicXML contained no lower voice. Added a whole note on "
                        f"open string 6. Visual confidence {candidate.score:.2f}."
                    ),
                )
            )
        else:
            issues.append(
                Issue(
                    Severity.WARNING,
                    "Possible omitted lower-voice note found in the source image.",
                    measure=candidate.measure_number,
                    code="visual-bass-review",
                    detail=(
                        f"The lower-staff detector found a possible {pitch_name} notehead "
                        f"(confidence {candidate.score:.2f}) but did not alter the score automatically."
                    ),
                )
            )

    for index, image in enumerate(annotated, start=1):
        if any(candidate.page_slot == index - 1 for candidate in detections):
            image.save(evidence_dir / f"page-{index:03d}-bass-check.png", optimize=True)

    if inserted:
        save_mxl(root, musicxml_path)
        progress(f"Visual bass verification inserted {inserted} sustained lower note(s).")
    elif detections:
        progress(f"Visual bass verification flagged {len(detections)} possible lower note(s) for review.")
    else:
        progress("Visual bass verification found no confident omitted open-string pedal notes.")

    return issues, inserted
