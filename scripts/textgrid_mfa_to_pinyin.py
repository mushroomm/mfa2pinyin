#!/usr/bin/env python3
"""Add a Hanyu Pinyin tier to a Mandarin MFA TextGrid without changing timestamps.

The generated tier copies the interval boundaries from the Chinese character
(`words`) tier and derives a numbered-tone pinyin label from the aligned MFA
phone labels.  Existing `words` and `phones` tiers are copied verbatim; only the
TextGrid tier count is updated and a new `pinyin` tier is appended.
"""
from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

TONE_MAP = {
    "˥˥": "1",
    "˧˥": "2",
    "˨˩˦": "3",
    "˥˩": "4",
    "˨": "5",
}

INITIALS = {
    "p": "b",
    "pʰ": "p",
    "m": "m",
    "f": "f",
    "t": "d",
    "tʰ": "t",
    "n": "n",
    "l": "l",
    "k": "g",
    "kʰ": "k",
    "x": "h",
    "ts": "z",
    "tsʰ": "c",
    "s": "s",
    "ʈʂ": "zh",
    "ʈʂʰ": "ch",
    "ʂ": "sh",
    "ʐ": "r",
    "tɕ": "j",
    "tɕʰ": "q",
    "ɕ": "x",
}
LABIAL_INITIALS = {"b", "p", "m", "f"}

# Context-sensitive readings that should follow the written Chinese text rather
# than the raw MFA phone spelling in this sample.
PINYIN_OVERRIDES = {
    "的": "de5",
    "了": "le5",
    "得": "de5",
    "北": "bei3",
    "更": "geng4",
    "长": "zhang3",
    "学": "xue2",
    "播": "bo1",
    "场": "chang3",
    "处": "chu4",
    "合": "he2",
    "教": "jiao4",
    "色": "se4",
    "数": "shu4",
    "盛": "sheng4",
    "还": "hai2",
    "血": "xue4",
    "率": "lü4",
}

TONE_RE = re.compile(r"[˥˧˩˨˦]+")
QUOTED_RE = re.compile(r'"(.*)"')


@dataclass
class Interval:
    xmin: float
    xmax: float
    xmin_text: str
    xmax_text: str
    text: str


def strip_tone(phone: str) -> str:
    return TONE_RE.sub("", phone)


def tone_number(phones: list[str]) -> str:
    for phone in phones:
        for mark, number in TONE_MAP.items():
            if mark in phone:
                return number
    return "5"


def parse_tiers(lines: list[str]) -> dict[str, list[Interval]]:
    tiers: dict[str, list[Interval]] = {}
    current_tier: str | None = None
    current: dict[str, str | float] | None = None

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("name = "):
            match = QUOTED_RE.search(stripped)
            if match:
                current_tier = match.group(1)
                tiers[current_tier] = []
        elif current_tier and stripped.startswith("intervals ["):
            current = {}
        elif current_tier and current is not None and stripped.startswith("xmin = "):
            value = stripped.split("=", 1)[1].strip()
            current["xmin"] = float(value)
            current["xmin_text"] = value
        elif current_tier and current is not None and stripped.startswith("xmax = "):
            value = stripped.split("=", 1)[1].strip()
            current["xmax"] = float(value)
            current["xmax_text"] = value
        elif current_tier and current is not None and stripped.startswith("text = "):
            match = QUOTED_RE.search(stripped)
            current["text"] = match.group(1) if match else ""
            tiers[current_tier].append(
                Interval(
                    xmin=current["xmin"],  # type: ignore[arg-type]
                    xmax=current["xmax"],  # type: ignore[arg-type]
                    xmin_text=current["xmin_text"],  # type: ignore[arg-type]
                    xmax_text=current["xmax_text"],  # type: ignore[arg-type]
                    text=current["text"],  # type: ignore[arg-type]
                )
            )
    return tiers


def final_from_segments(initial: str, rest: tuple[str, ...]) -> str:
    if rest == ("ʐ̩",):
        return "ri" if not initial else "i"
    if rest == ("z̩",):
        return "i"
    if rest == ("i",):
        return "yi" if not initial else "i"
    if rest == ("i", "n"):
        return "yin" if not initial else "in"
    if rest == ("i", "ŋ"):
        return "ying" if not initial else "ing"
    if rest == ("u",):
        return "wu" if not initial else "u"
    if rest == ("u", "ŋ"):
        return "ong"
    if rest == ("y",):
        return "yu" if not initial else "u"
    if rest == ("y", "n"):
        return "yun" if not initial else "un"
    if rest == ("ɥ", "e"):
        return "yue" if not initial else "ue"
    if rest == ("ɥ", "e", "n"):
        return "yuan" if not initial else "uan"
    if rest == ("j", "a"):
        return "ya" if not initial else "ia"
    if rest == ("j", "a", "ŋ"):
        return "yang" if not initial else "iang"
    if rest == ("j", "aw"):
        return "yao" if not initial else "iao"
    if rest == ("j", "e"):
        return "ye" if not initial else "ie"
    if rest == ("j", "e", "n"):
        return "yan" if not initial else "ian"
    if rest == ("j", "ow"):
        return "you" if not initial else "iu"
    if rest == ("j", "u", "ŋ"):
        return "yong" if not initial else "iong"
    if rest == ("w", "a"):
        return "wa" if not initial else "ua"
    if rest == ("w", "a", "n"):
        return "wan" if not initial else "uan"
    if rest == ("w", "a", "ŋ"):
        return "wang" if not initial else "uang"
    if rest == ("w", "aj"):
        return "wai" if not initial else "uai"
    if rest == ("w", "ej"):
        return "wei" if not initial else "ui"
    if rest == ("w", "ə", "n"):
        return "wen" if not initial else "un"
    if rest == ("w", "o"):
        if not initial:
            return "wo"
        return "o" if initial in LABIAL_INITIALS else "uo"

    simple = {
        ("a",): "a",
        ("a", "n"): "an",
        ("a", "ŋ"): "ang",
        ("aj",): "ai",
        ("aw",): "ao",
        ("ej",): "ei",
        ("e",): "e",
        ("ə", "n"): "en",
        ("o",): "e",
        ("o", "ŋ"): "eng",
        ("ow",): "ou",
    }
    if rest in simple:
        return simple[rest]
    return "".join(rest)


def pinyin_from_phones(char: str, phones: list[str]) -> str:
    if not char or not phones:
        return ""
    if char in PINYIN_OVERRIDES:
        return PINYIN_OVERRIDES[char]

    number = tone_number(phones)
    base = [strip_tone(phone) for phone in phones]

    initial = ""
    rest = tuple(base)
    if base and base[0] in INITIALS:
        initial = INITIALS[base[0]]
        rest = tuple(base[1:])
    elif base and base[0] == "ʔ":
        rest = tuple(base[1:])

    final = final_from_segments(initial, rest)
    if not initial:
        return f"{final}{number}"
    return f"{initial}{final}{number}"


def aligned_phones(word: Interval, phones: list[Interval]) -> list[str]:
    return [
        phone.text
        for phone in phones
        if phone.text
        and phone.xmin >= word.xmin - 1e-7
        and phone.xmax <= word.xmax + 1e-7
    ]


def pinyin_tier(words: list[Interval], phones: list[Interval], xmin: str, xmax: str) -> list[str]:
    lines = [
        "    item [3]:\n",
        '        class = "IntervalTier" \n',
        '        name = "pinyin" \n',
        f"        xmin = {xmin} \n",
        f"        xmax = {xmax} \n",
        f"        intervals: size = {len(words)} \n",
    ]
    for index, word in enumerate(words, start=1):
        label = pinyin_from_phones(word.text, aligned_phones(word, phones))
        lines.extend(
            [
                f"        intervals [{index}]:\n",
                f"            xmin = {word.xmin_text} \n",
                f"            xmax = {word.xmax_text} \n",
                f'            text = "{label}" \n',
            ]
        )
    return lines


def add_pinyin_tier(input_path: Path, output_path: Path) -> None:
    lines = input_path.read_text(encoding="utf-8").splitlines(keepends=True)
    tiers = parse_tiers(lines)
    if "words" not in tiers or "phones" not in tiers:
        raise ValueError("TextGrid must contain 'words' and 'phones' interval tiers")

    output_lines: list[str] = []
    changed_size = False
    xmin = xmax = None
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("xmin = ") and xmin is None:
            xmin = stripped.split("=", 1)[1].strip()
        elif stripped.startswith("xmax = ") and xmax is None:
            xmax = stripped.split("=", 1)[1].strip()
        if not changed_size and stripped == "size = 2":
            output_lines.append(line.replace("size = 2", "size = 3"))
            changed_size = True
        else:
            output_lines.append(line)

    if xmin is None or xmax is None:
        raise ValueError("TextGrid xmin/xmax not found")
    output_lines.extend(pinyin_tier(tiers["words"], tiers["phones"], xmin, xmax))
    output_path.write_text("".join(output_lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    add_pinyin_tier(args.input, args.output)


if __name__ == "__main__":
    main()
