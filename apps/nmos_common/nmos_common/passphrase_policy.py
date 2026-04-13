from __future__ import annotations

import re

MIN_PASSPHRASE_LENGTH = 12

COMMON_WEAK_PASSPHRASES = {
    "123456",
    "12345678",
    "123456789",
    "password",
    "password123",
    "qwerty",
    "qwerty123",
    "letmein",
    "welcome",
    "admin",
    "changeme",
    "iloveyou",
    "000000",
    "111111",
    "abc123",
    "nm-os",
    "nmos",
}

SPECIAL_CHAR_PATTERN = re.compile(r"[^A-Za-z0-9]")


def evaluate_passphrase(passphrase: str) -> dict:
    text = str(passphrase or "")
    lowered = text.strip().lower()
    has_min_length = len(text) >= MIN_PASSPHRASE_LENGTH
    has_lower = any(ch.islower() for ch in text)
    has_upper = any(ch.isupper() for ch in text)
    has_digit = any(ch.isdigit() for ch in text)
    has_special = bool(SPECIAL_CHAR_PATTERN.search(text))
    is_common = lowered in COMMON_WEAK_PASSPHRASES

    issues: list[str] = []
    if not text.strip():
        issues.append("passphrase cannot be empty")
    if not has_min_length:
        issues.append(f"minimum length is {MIN_PASSPHRASE_LENGTH}")
    if not has_lower:
        issues.append("must include a lowercase letter")
    if not has_upper:
        issues.append("must include an uppercase letter")
    if not has_digit:
        issues.append("must include a number")
    if not has_special:
        issues.append("must include a special character")
    if is_common:
        issues.append("common weak passphrases are not allowed")

    score = int(has_min_length) + int(has_lower) + int(has_upper) + int(has_digit) + int(has_special)
    if is_common or not text.strip():
        score = max(0, score - 2)

    if not issues and score >= 5:
        strength = "strong"
    elif score >= 4 and len(issues) <= 2:
        strength = "fair"
    else:
        strength = "weak"

    return {
        "valid_for_creation": len(issues) == 0,
        "strength": strength,
        "score": score,
        "issues": issues,
        "has_min_length": has_min_length,
        "has_lower": has_lower,
        "has_upper": has_upper,
        "has_digit": has_digit,
        "has_special": has_special,
        "is_common": is_common,
    }


def passphrase_feedback_text(passphrase: str) -> str:
    evaluation = evaluate_passphrase(passphrase)
    strength = str(evaluation["strength"])
    issues = list(evaluation["issues"])
    if not passphrase:
        return "Passphrase strength: waiting for input."
    if not issues:
        return f"Passphrase strength: {strength}."
    return f"Passphrase strength: {strength}. Missing: {', '.join(issues)}."
