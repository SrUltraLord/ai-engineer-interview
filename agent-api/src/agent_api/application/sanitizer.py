from collections.abc import Sequence
from dataclasses import replace

from agent_api.application.ports.audit import AuditLog
from agent_api.application.ports.security import InjectionDetector
from agent_api.domain.documents import Document
from agent_api.domain.injection import Detection, normalize, redact


class DocumentSanitizer:
    """Neutraliza prompt injection indirecta: redacta el fragmento y conserva el resto del documento."""

    def __init__(self, detectors: Sequence[InjectionDetector], audit: AuditLog) -> None:
        self._detectors = detectors
        self._audit = audit

    def sanitize(self, document: Document) -> Document:
        text = normalize(document.text)
        detections: list[Detection] = [d for det in self._detectors for d in det.detect(text)]
        if not detections:
            return replace(document, text=text)
        for d in detections:
            self._audit.record(
                "injection_detected", document_id=document.id, pattern=d.pattern, action="redacted"
            )
        return replace(document, text=redact(text, detections))
