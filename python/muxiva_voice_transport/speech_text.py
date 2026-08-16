"""Deterministic display-text to speech-text normalization."""

from __future__ import annotations

import re
import unicodedata


_CJK = re.compile(r"[\u3400-\u9fff]")
_LATIN = re.compile(r"[A-Za-z]")
_FENCE = re.compile(r"```.*?```|~~~.*?~~~", re.DOTALL)
_IMAGE = re.compile(r"!\[([^]]*)]\([^)]*\)")
_LINK = re.compile(r"\[([^]]+)]\([^)]*\)")
_HTML = re.compile(r"<[^>]+>")
_URL = re.compile(
    r"(?:https?|ftp)://[^\s<>()\[\]{}\"',;!?，。！？；：、]+|"
    r"www\.[^\s<>()\[\]{}\"',;!?，。！？；：、]+",
    re.IGNORECASE,
)
_EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_DOMAIN = re.compile(
    r"(?<![@\w])(?:[A-Z0-9-]+\.)+(?:com|cn|net|org|io|ai|dev|app|co|me|tech)"
    r"(?:/[^\s<>()\[\]{}\"',;!?，。！？；：、]*)?",
    re.IGNORECASE,
)
_YEAR = re.compile(r"(?<!\d)(\d{4})\s*年")
_PERCENT = re.compile(r"(?<![A-Za-z])(-?\d+(?:\.\d+)?)\s*%")
_NUMBER = re.compile(r"(?<![A-Za-z])(-?\d[\d,]*(?:\.\d+)?)(?![A-Za-z])")

_DIGITS = "零一二三四五六七八九"
_SMALL_UNITS = ("", "十", "百", "千")
_GROUP_UNITS = ("", "万", "亿", "兆")


def _is_emoji(character: str) -> bool:
    value = ord(character)
    return (
        0x1F000 <= value <= 0x1FAFF
        or 0x2600 <= value <= 0x27BF
        or 0x2300 <= value <= 0x23FF
        or 0x2B00 <= value <= 0x2BFF
        or 0xFE00 <= value <= 0xFE0F
        or 0x1F1E6 <= value <= 0x1F1FF
        or value in {0x200D, 0x20E3}
    )


def _digits(value: str) -> str:
    return "".join(_DIGITS[int(character)] for character in value if character.isdigit())


def _section(value: int) -> str:
    output: list[str] = []
    zero_pending = False
    started = False
    for position in range(3, -1, -1):
        divisor = 10**position
        digit = value // divisor % 10
        if digit == 0:
            if started and value % divisor:
                zero_pending = True
            continue
        if zero_pending:
            output.append("零")
            zero_pending = False
        if not (digit == 1 and position == 1 and not output):
            output.append(_DIGITS[digit])
        output.append(_SMALL_UNITS[position])
        started = True
    return "".join(output) or "零"


def _integer(value: str) -> str:
    if len(value) > 1 and value.startswith("0"):
        return _digits(value)
    number = int(value)
    if number == 0:
        return "零"
    groups: list[int] = []
    while number:
        groups.append(number % 10_000)
        number //= 10_000
    if len(groups) > len(_GROUP_UNITS):
        return _digits(value)
    output: list[str] = []
    zero_pending = False
    for index in range(len(groups) - 1, -1, -1):
        group = groups[index]
        if group == 0:
            if output:
                zero_pending = True
            continue
        if output and (zero_pending or group < 1000):
            output.append("零")
        output.append(_section(group))
        output.append(_GROUP_UNITS[index])
        zero_pending = False
    return "".join(output)


def _number(value: str) -> str:
    negative = value.startswith("-")
    value = (value[1:] if negative else value).replace(",", "")
    whole, dot, fraction = value.partition(".")
    if len(whole) >= 7 and not dot:
        spoken = _digits(whole)
    else:
        spoken = _integer(whole)
    if dot:
        spoken = f"{spoken}点{_digits(fraction)}"
    return f"负{spoken}" if negative else spoken


def _zh_numbers(text: str) -> str:
    text = _YEAR.sub(lambda match: f"{_digits(match.group(1))}年", text)
    text = _PERCENT.sub(lambda match: f"百分之{_number(match.group(1))}", text)
    return _NUMBER.sub(lambda match: _number(match.group(1)), text)


def normalize_for_speech(
    text: str,
    *,
    language: str = "auto",
    code_message: str = "代码已经生成，请在聊天窗口查看。",
) -> str:
    """Return stable, speakable text while preserving the displayed answer."""

    text = unicodedata.normalize("NFKC", text)
    text = _FENCE.sub(f" {code_message} ", text)
    text = _IMAGE.sub(lambda match: f" {match.group(1)} ", text)
    text = _LINK.sub(lambda match: match.group(1), text)
    text = _URL.sub(" ", text)
    text = _EMAIL.sub(" ", text)
    text = _DOMAIN.sub(" ", text)
    text = _HTML.sub(" ", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"(?m)^\s*[-‐‑‒–—―_=]{2,}\s*$", " ", text)
    text = re.sub(r"(?m)^\s{0,3}(?:#{1,6}|>|[-+*]|\d+[.)])\s+", "", text)
    text = re.sub(r"[*_~]{1,3}", "", text)
    text = "".join(character for character in text if not _is_emoji(character))

    resolved_language = language
    if language == "auto":
        resolved_language = "zh" if len(_CJK.findall(text)) >= len(_LATIN.findall(text)) / 2 else "en"
    if resolved_language == "zh":
        text = _zh_numbers(text)
        text = text.translate(str.maketrans({
            "&": "和", "+": "加", "=": "等于", "@": "艾特",
            "℃": "摄氏度", "°": "度",
            ",": "，", ";": "；", ":": "：", "!": "！", "?": "？",
        }))

    text = re.sub(r"[-‐‑‒–—―]+", "，", text)
    text = re.sub(r"[\[\]{}()<>|\\/\"'“”‘’#^$]+", " ", text)
    text = re.sub(r"[，,]{2,}", "，" if resolved_language == "zh" else ",", text)
    text = re.sub(r"\s+", " ", text)
    if resolved_language == "zh":
        text = re.sub(r"(?<=[\u3400-\u9fff])\s+(?=[\u3400-\u9fff])", "", text)
    text = re.sub(r"\s*([,，。.!！?？;；:：、])\s*", r"\1", text)
    return text.strip(" ,，")
