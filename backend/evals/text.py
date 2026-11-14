"""Plain text measures for the graders: words, sentences, syllables, Flesch-Kincaid grade."""

import re

_WORD = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)*")
_SENTENCE_END = re.compile(r"[.!?]+(?:[\"')\]]+)?(?:\s+|$)")


def words(text: str) -> list[str]:
    return _WORD.findall(text)


def word_count(text: str) -> int:
    """Whitespace-separated tokens (what a person counts as words)."""
    return len(text.split())


def sentence_count(text: str) -> int:
    """Sentences ended by . ! or ?; trailing text without a mark counts as one."""
    stripped = text.strip()
    if not stripped:
        return 0
    pieces = [p for p in _SENTENCE_END.split(stripped) if p.strip()]
    return max(len(pieces), 1)


def syllables(word: str) -> int:
    """Vowel-group heuristic with a silent final 'e'; at least 1."""
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return 0
    count = len(re.findall(r"[aeiouy]+", w))
    if w.endswith("e") and not w.endswith(("le", "ee", "ye")) and count > 1:
        count -= 1
    if w.endswith("es") and not w.endswith(("ses", "zes", "ces", "ges", "xes")) and count > 1:
        count -= 1
    if w.endswith("ed") and not w.endswith(("ted", "ded", "ied")) and count > 1:
        count -= 1
    return max(count, 1)


def flesch_kincaid_grade(text: str) -> float:
    """0.39 * words/sentences + 11.8 * syllables/words - 15.59. Empty text grades 0."""
    tokens = words(text)
    sentences = sentence_count(text)
    if not tokens or sentences == 0:
        return 0.0
    total_syllables = sum(syllables(t) for t in tokens)
    return 0.39 * len(tokens) / sentences + 11.8 * total_syllables / len(tokens) - 15.59


def contains_term(text: str, term: str) -> bool:
    """Whole-word / whole-phrase, case-insensitive match (so 'dose' does not match 'closer')."""
    normalised = text.lower().replace("\N{RIGHT SINGLE QUOTATION MARK}", "'")
    needle = re.escape(term.lower()).replace("\\ ", r"\s+")
    return re.search(rf"(?<![\w']){needle}(?![\w'])", normalised) is not None
