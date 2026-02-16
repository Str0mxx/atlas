"""ATLAS Email Aksiyon Çıkarıcı modülü.

Görev çıkarma, son tarih tespiti,
istek tanımlama, taahhüt takibi,
takip ihtiyacı.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class EmailActionExtractor:
    """Email aksiyon çıkarıcı.

    Emaillerden aksiyonları çıkarır.

    Attributes:
        _actions: Aksiyon kayıtları.
        _commitments: Taahhüt kayıtları.
    """

    def __init__(self) -> None:
        """Çıkarıcıyı başlatır."""
        self._actions: list[
            dict[str, Any]
        ] = []
        self._commitments: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "actions_extracted": 0,
            "deadlines_found": 0,
        }

        logger.info(
            "EmailActionExtractor "
            "baslatildi",
        )

    def extract_tasks(
        self,
        email_id: str = "",
        body: str = "",
    ) -> dict[str, Any]:
        """Görev çıkarır.

        Args:
            email_id: Email kimliği.
            body: Gövde.

        Returns:
            Çıkarma bilgisi.
        """
        text = body.lower()
        tasks = []

        task_patterns = [
            "please", "could you",
            "can you", "need to",
            "action required",
            "todo", "task",
        ]

        sentences = self._split_sentences(
            body,
        )

        for sent in sentences:
            lower = sent.lower()
            for pattern in task_patterns:
                if pattern in lower:
                    self._counter += 1
                    tasks.append({
                        "task_id": (
                            f"tsk_"
                            f"{self._counter}"
                        ),
                        "description": (
                            sent.strip()
                        ),
                        "pattern": pattern,
                    })
                    self._stats[
                        "actions_extracted"
                    ] += 1
                    break

        self._actions.extend(tasks)

        return {
            "email_id": email_id,
            "tasks": tasks,
            "count": len(tasks),
            "extracted": True,
        }

    def detect_deadlines(
        self,
        email_id: str = "",
        body: str = "",
    ) -> dict[str, Any]:
        """Son tarih tespit eder.

        Args:
            email_id: Email kimliği.
            body: Gövde.

        Returns:
            Tespit bilgisi.
        """
        text = body.lower()
        deadlines = []

        deadline_patterns = [
            "by tomorrow", "by friday",
            "by monday", "end of week",
            "end of day", "eod",
            "asap", "by end of month",
            "due date", "deadline",
        ]

        for pattern in deadline_patterns:
            if pattern in text:
                self._counter += 1
                deadlines.append({
                    "deadline_id": (
                        f"dl_"
                        f"{self._counter}"
                    ),
                    "pattern": pattern,
                    "urgency": (
                        "high"
                        if pattern in (
                            "asap", "by tomorrow",
                            "end of day", "eod",
                        )
                        else "medium"
                    ),
                })
                self._stats[
                    "deadlines_found"
                ] += 1

        return {
            "email_id": email_id,
            "deadlines": deadlines,
            "count": len(deadlines),
            "detected": len(deadlines) > 0,
        }

    def identify_requests(
        self,
        email_id: str = "",
        body: str = "",
    ) -> dict[str, Any]:
        """İstek tanımlar.

        Args:
            email_id: Email kimliği.
            body: Gövde.

        Returns:
            Tanımlama bilgisi.
        """
        sentences = self._split_sentences(
            body,
        )
        requests = []

        request_patterns = [
            "could you", "can you",
            "would you", "please send",
            "please provide", "need",
            "request", "looking for",
        ]

        for sent in sentences:
            lower = sent.lower()
            for pattern in request_patterns:
                if pattern in lower:
                    self._counter += 1
                    requests.append({
                        "request_id": (
                            f"req_"
                            f"{self._counter}"
                        ),
                        "description": (
                            sent.strip()
                        ),
                        "type": "request",
                    })
                    break

        return {
            "email_id": email_id,
            "requests": requests,
            "count": len(requests),
            "identified": len(requests) > 0,
        }

    def track_commitments(
        self,
        email_id: str = "",
        body: str = "",
    ) -> dict[str, Any]:
        """Taahhüt takibi yapar.

        Args:
            email_id: Email kimliği.
            body: Gövde.

        Returns:
            Takip bilgisi.
        """
        sentences = self._split_sentences(
            body,
        )
        commitments = []

        commitment_patterns = [
            "i will", "i'll",
            "we will", "we'll",
            "i promise", "i commit",
            "i plan to", "i'm going to",
        ]

        for sent in sentences:
            lower = sent.lower()
            for pattern in (
                commitment_patterns
            ):
                if pattern in lower:
                    self._counter += 1
                    commitments.append({
                        "commitment_id": (
                            f"cmt_"
                            f"{self._counter}"
                        ),
                        "description": (
                            sent.strip()
                        ),
                    })
                    break

        self._commitments.extend(
            commitments,
        )

        return {
            "email_id": email_id,
            "commitments": commitments,
            "count": len(commitments),
            "tracked": len(
                commitments,
            ) > 0,
        }

    def check_followup_needs(
        self,
        email_id: str = "",
        body: str = "",
    ) -> dict[str, Any]:
        """Takip ihtiyacı kontrol eder.

        Args:
            email_id: Email kimliği.
            body: Gövde.

        Returns:
            Kontrol bilgisi.
        """
        text = body.lower()

        followup_indicators = [
            "follow up", "get back to",
            "let me know", "waiting for",
            "pending", "awaiting",
            "remind me", "check back",
        ]

        needs_followup = any(
            ind in text
            for ind in followup_indicators
        )

        urgency = "low"
        if needs_followup:
            if any(
                w in text for w in [
                    "urgent", "asap",
                    "immediately",
                ]
            ):
                urgency = "high"
            elif any(
                w in text for w in [
                    "soon", "this week",
                ]
            ):
                urgency = "medium"

        return {
            "email_id": email_id,
            "needs_followup": needs_followup,
            "urgency": urgency,
            "checked": True,
        }

    def _split_sentences(
        self,
        text: str,
    ) -> list[str]:
        """Cümlelere böler."""
        if not text:
            return []

        sentences = []
        current = ""

        for char in text:
            current += char
            if char in ".!?":
                stripped = current.strip()
                if stripped:
                    sentences.append(stripped)
                current = ""

        if current.strip():
            sentences.append(
                current.strip(),
            )

        return sentences

    @property
    def action_count(self) -> int:
        """Aksiyon sayısı."""
        return self._stats[
            "actions_extracted"
        ]

    @property
    def deadline_count(self) -> int:
        """Son tarih sayısı."""
        return self._stats[
            "deadlines_found"
        ]
