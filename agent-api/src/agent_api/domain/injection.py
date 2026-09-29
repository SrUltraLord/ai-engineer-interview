import re
import unicodedata
from dataclasses import dataclass

REDACTION = "[FRAGMENTO SOSPECHOSO REDACTADO]"


@dataclass(frozen=True)
class Detection:
    pattern: str
    start: int
    end: int


@dataclass(frozen=True)
class SanitizedText:
    text: str
    detections: tuple[Detection, ...]


# nombre -> regex (sobre texto normalizado y en minúsculas)
PATTERNS: dict[str, str] = {
    "ignore_previous_rules_es": r"ignor(?:a|ar|e|en)\s+(?:todas\s+)?(?:las\s+|tus\s+)?(?:reglas|instrucciones|indicaciones)\s+(?:anteriores|previas)",
    "ignore_previous_rules_en": r"(?:ignore|disregard|forget)\s+(?:all\s+)?(?:the\s+|your\s+)?(?:previous|prior|above|earlier)\s+(?:rules|instructions|prompts?)",
    "forget_everything": r"(?:olvida|olvide)\s+(?:todo|las\s+(?:reglas|instrucciones))",
    "dump_all_documents_es": r"muestr(?:a|e)(?:me)?\s+(?:todos\s+los|la\s+totalidad\s+de\s+los)\s+documentos",
    "dump_all_documents_en": r"(?:show|reveal|list|dump|print)\s+(?:me\s+)?(?:all|every)\s+(?:the\s+)?documents",
    "reveal_system_prompt": r"(?:revela|muestra|imprime|reveal|show|print)\s+(?:tu\s+|el\s+|your\s+|the\s+)?(?:system\s+prompt|prompt\s+del\s+sistema|instrucciones\s+del\s+sistema)",
    "disable_filters": r"(?:desactiva|deshabilita|elimina|disable|remove|bypass)\s+(?:los\s+|the\s+|all\s+)?(?:filtros|restricciones|controles|filters|restrictions)",
    "role_override": r"(?:ahora\s+eres|a\s+partir\s+de\s+ahora\s+eres|you\s+are\s+now|act\s+as\s+(?:an?\s+)?(?:admin|administrator|root))",
    "delimiter_forgery": r"</?\s*(?:documento|documentos_recuperados|system|instrucciones)\b",
}
_COMPILED = {name: re.compile(rx) for name, rx in PATTERNS.items()}
_ZERO_WIDTH = dict.fromkeys(map(ord, "​‌‍⁠﻿"), None)
_SENTENCE_END = ".!?\n"


def normalize(text: str) -> str:
    """NFKC + sin caracteres invisibles, para que no se evada la detección con ofuscación trivial."""
    return unicodedata.normalize("NFKC", text).translate(_ZERO_WIDTH)


class PatternInjectionDetector:
    """Heurística por patrones (es/en). Devuelve rangos sobre el texto normalizado."""

    def detect(self, text: str) -> list[Detection]:
        lowered = text.lower()
        return [
            Detection(name, m.start(), m.end())
            for name, rx in _COMPILED.items()
            for m in rx.finditer(lowered)
        ]


def _expand_to_sentence(text: str, start: int, end: int) -> tuple[int, int]:
    s = start
    while s > 0 and text[s - 1] not in _SENTENCE_END:
        s -= 1
    e = end
    while e < len(text) and text[e] not in _SENTENCE_END:
        e += 1
    return s, min(e + 1, len(text))


def redact(text: str, detections: list[Detection]) -> str:
    """Sustituye la oración completa de cada detección; el resto del documento se conserva."""
    spans = sorted(_expand_to_sentence(text, d.start, d.end) for d in detections)
    merged: list[list[int]] = []
    for s, e in spans:
        if merged and s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    out, pos = [], 0
    for s, e in merged:
        out.append(text[pos:s])
        out.append(f" {REDACTION}" if s and not text[s - 1].isspace() else REDACTION)
        pos = e
    out.append(text[pos:])
    return re.sub(r"[ \t]{2,}", " ", "".join(out)).strip()
