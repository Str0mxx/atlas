"""
Context window yonetim modulu.

Token sayma, baglam sigdirma,
oncelikli kirpma, chunking stratejileri,
tasma yonetimi.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class ContextWindowManager:
    """Context window yoneticisi.

    Attributes:
        _windows: Pencere kayitlari.
        _chunks: Chunk kayitlari.
        _stats: Istatistikler.
    """

    CHUNK_STRATEGIES: list[str] = [
        "fixed_size",
        "sentence_boundary",
        "paragraph_boundary",
        "semantic_boundary",
        "overlap_sliding",
    ]

    PRIORITY_LEVELS: list[str] = [
        "critical",
        "high",
        "medium",
        "low",
        "optional",
    ]

    def __init__(
        self,
        default_max_tokens: int = 4096,
        tokens_per_word: float = 1.3,
    ) -> None:
        """Window yoneticisini baslatir.

        Args:
            default_max_tokens: Varsayilan max.
            tokens_per_word: Kelime/token orani.
        """
        self._default_max = (
            default_max_tokens
        )
        self._tokens_per_word = (
            tokens_per_word
        )
        self._windows: dict[
            str, dict
        ] = {}
        self._chunks: dict[
            str, list[dict]
        ] = {}
        self._stats: dict[str, int] = {
            "windows_created": 0,
            "tokens_counted": 0,
            "truncations_done": 0,
            "chunks_created": 0,
            "overflows_handled": 0,
        }
        logger.info(
            "ContextWindowManager "
            "baslatildi"
        )

    @property
    def window_count(self) -> int:
        """Pencere sayisi."""
        return len(self._windows)

    def count_tokens(
        self,
        text: str = "",
    ) -> dict[str, Any]:
        """Token sayar.

        Args:
            text: Metin.

        Returns:
            Token bilgisi.
        """
        try:
            words = len(text.split())
            chars = len(text)
            est_tokens = int(
                words * self._tokens_per_word
            )

            self._stats[
                "tokens_counted"
            ] += 1

            return {
                "word_count": words,
                "char_count": chars,
                "estimated_tokens": (
                    est_tokens
                ),
                "counted": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "counted": False,
                "error": str(e),
            }

    def create_window(
        self,
        name: str = "",
        max_tokens: int = 0,
        system_prompt: str = "",
        reserved_output: int = 500,
    ) -> dict[str, Any]:
        """Window olusturur.

        Args:
            name: Pencere adi.
            max_tokens: Maks token.
            system_prompt: Sistem promptu.
            reserved_output: Cikis icin ayri.

        Returns:
            Pencere bilgisi.
        """
        try:
            wid = f"cw_{uuid4()!s:.8}"
            mt = max_tokens or (
                self._default_max
            )

            sys_tokens = int(
                len(system_prompt.split())
                * self._tokens_per_word
            )

            available = (
                mt
                - sys_tokens
                - reserved_output
            )

            self._windows[wid] = {
                "window_id": wid,
                "name": name,
                "max_tokens": mt,
                "system_tokens": sys_tokens,
                "reserved_output": (
                    reserved_output
                ),
                "available_tokens": max(
                    0, available
                ),
                "used_tokens": 0,
                "segments": [],
                "created_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }

            self._stats[
                "windows_created"
            ] += 1

            return {
                "window_id": wid,
                "max_tokens": mt,
                "available_tokens": max(
                    0, available
                ),
                "created": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "created": False,
                "error": str(e),
            }

    def add_segment(
        self,
        window_id: str = "",
        content: str = "",
        priority: str = "medium",
        label: str = "",
    ) -> dict[str, Any]:
        """Segmenti pencereye ekler.

        Args:
            window_id: Pencere ID.
            content: Icerik.
            priority: Oncelik.
            label: Etiket.

        Returns:
            Ekleme bilgisi.
        """
        try:
            window = self._windows.get(
                window_id
            )
            if not window:
                return {
                    "added": False,
                    "error": (
                        "Pencere bulunamadi"
                    ),
                }

            tokens = int(
                len(content.split())
                * self._tokens_per_word
            )

            segment = {
                "content": content,
                "priority": priority,
                "label": label,
                "tokens": tokens,
            }

            window["segments"].append(
                segment
            )
            window["used_tokens"] += tokens

            fits = (
                window["used_tokens"]
                <= window["available_tokens"]
            )

            return {
                "window_id": window_id,
                "tokens": tokens,
                "used_tokens": window[
                    "used_tokens"
                ],
                "available_tokens": window[
                    "available_tokens"
                ],
                "fits": fits,
                "added": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "added": False,
                "error": str(e),
            }

    def fit_context(
        self,
        window_id: str = "",
    ) -> dict[str, Any]:
        """Baglami pencereye sigdirir.

        Args:
            window_id: Pencere ID.

        Returns:
            Sigdirma bilgisi.
        """
        try:
            window = self._windows.get(
                window_id
            )
            if not window:
                return {
                    "fitted": False,
                    "error": (
                        "Pencere bulunamadi"
                    ),
                }

            available = window[
                "available_tokens"
            ]
            segments = window["segments"]

            if (
                window["used_tokens"]
                <= available
            ):
                # Zaten sigiyor
                return {
                    "window_id": window_id,
                    "truncated": False,
                    "segments_kept": len(
                        segments
                    ),
                    "segments_removed": 0,
                    "fitted": True,
                }

            # Oncelik sirasina gore kirp
            priority_order = {
                p: i
                for i, p in enumerate(
                    self.PRIORITY_LEVELS
                )
            }

            sorted_segs = sorted(
                enumerate(segments),
                key=lambda x: priority_order
                .get(
                    x[1]["priority"], 2
                ),
            )

            kept = []
            used = 0
            removed = 0

            for _idx, seg in sorted_segs:
                if (
                    used + seg["tokens"]
                    <= available
                ):
                    kept.append(seg)
                    used += seg["tokens"]
                else:
                    removed += 1

            window["segments"] = kept
            window["used_tokens"] = used

            self._stats[
                "truncations_done"
            ] += 1

            return {
                "window_id": window_id,
                "truncated": True,
                "segments_kept": len(kept),
                "segments_removed": removed,
                "used_tokens": used,
                "fitted": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "fitted": False,
                "error": str(e),
            }

    def chunk_text(
        self,
        text: str = "",
        chunk_size: int = 500,
        strategy: str = "fixed_size",
        overlap: int = 50,
    ) -> dict[str, Any]:
        """Metni parcalar.

        Args:
            text: Metin.
            chunk_size: Parca boyutu.
            strategy: Strateji.
            overlap: Ortusme.

        Returns:
            Chunk bilgisi.
        """
        try:
            if strategy == "fixed_size":
                chunks = (
                    self._chunk_fixed(
                        text, chunk_size
                    )
                )
            elif strategy == (
                "sentence_boundary"
            ):
                chunks = (
                    self._chunk_sentences(
                        text, chunk_size
                    )
                )
            elif strategy == (
                "paragraph_boundary"
            ):
                chunks = (
                    self._chunk_paragraphs(
                        text, chunk_size
                    )
                )
            elif strategy == (
                "overlap_sliding"
            ):
                chunks = (
                    self._chunk_overlap(
                        text,
                        chunk_size,
                        overlap,
                    )
                )
            else:
                chunks = (
                    self._chunk_fixed(
                        text, chunk_size
                    )
                )

            cid = f"ch_{uuid4()!s:.8}"
            self._chunks[cid] = chunks

            self._stats[
                "chunks_created"
            ] += len(chunks)

            return {
                "chunk_id": cid,
                "strategy": strategy,
                "total_chunks": len(chunks),
                "chunk_sizes": [
                    len(c["content"].split())
                    for c in chunks
                ],
                "chunked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "chunked": False,
                "error": str(e),
            }

    def _chunk_fixed(
        self,
        text: str,
        size: int,
    ) -> list[dict]:
        """Sabit boyutlu chunking."""
        words = text.split()
        chunks = []
        for i in range(0, len(words), size):
            chunk_words = words[i : i + size]
            chunks.append({
                "index": len(chunks),
                "content": " ".join(
                    chunk_words
                ),
                "word_count": len(
                    chunk_words
                ),
            })
        return chunks

    def _chunk_sentences(
        self,
        text: str,
        size: int,
    ) -> list[dict]:
        """Cumle sinirli chunking."""
        sentences = text.split(". ")
        chunks = []
        current: list[str] = []
        current_words = 0

        for sent in sentences:
            words = len(sent.split())
            if (
                current_words + words > size
                and current
            ):
                chunks.append({
                    "index": len(chunks),
                    "content": ". ".join(
                        current
                    ),
                    "word_count": (
                        current_words
                    ),
                })
                current = []
                current_words = 0
            current.append(sent)
            current_words += words

        if current:
            chunks.append({
                "index": len(chunks),
                "content": ". ".join(
                    current
                ),
                "word_count": current_words,
            })

        return chunks

    def _chunk_paragraphs(
        self,
        text: str,
        size: int,
    ) -> list[dict]:
        """Paragraf sinirli chunking."""
        paragraphs = text.split("\n\n")
        chunks = []
        current: list[str] = []
        current_words = 0

        for para in paragraphs:
            words = len(para.split())
            if (
                current_words + words > size
                and current
            ):
                chunks.append({
                    "index": len(chunks),
                    "content": "\n\n".join(
                        current
                    ),
                    "word_count": (
                        current_words
                    ),
                })
                current = []
                current_words = 0
            current.append(para)
            current_words += words

        if current:
            chunks.append({
                "index": len(chunks),
                "content": "\n\n".join(
                    current
                ),
                "word_count": current_words,
            })

        return chunks

    def _chunk_overlap(
        self,
        text: str,
        size: int,
        overlap: int,
    ) -> list[dict]:
        """Ortusme kaydirilmali chunking."""
        words = text.split()
        step = max(1, size - overlap)
        chunks = []

        for i in range(
            0, len(words), step
        ):
            chunk_words = words[i : i + size]
            if not chunk_words:
                break
            chunks.append({
                "index": len(chunks),
                "content": " ".join(
                    chunk_words
                ),
                "word_count": len(
                    chunk_words
                ),
            })
            if i + size >= len(words):
                break

        return chunks

    def get_chunks(
        self,
        chunk_id: str = "",
    ) -> dict[str, Any]:
        """Chunklari getirir."""
        try:
            chunks = self._chunks.get(
                chunk_id
            )
            if chunks is None:
                return {
                    "retrieved": False,
                    "error": (
                        "Chunk bulunamadi"
                    ),
                }
            return {
                "chunk_id": chunk_id,
                "chunks": chunks,
                "total": len(chunks),
                "retrieved": True,
            }
        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def handle_overflow(
        self,
        text: str = "",
        max_tokens: int = 0,
        strategy: str = "truncate_end",
    ) -> dict[str, Any]:
        """Tasma yonetimi.

        Args:
            text: Metin.
            max_tokens: Maks token.
            strategy: Strateji.

        Returns:
            Yonetim bilgisi.
        """
        try:
            mt = max_tokens or (
                self._default_max
            )
            words = text.split()
            est_tokens = int(
                len(words)
                * self._tokens_per_word
            )

            if est_tokens <= mt:
                return {
                    "overflow": False,
                    "text": text,
                    "tokens": est_tokens,
                    "handled": True,
                }

            target_words = int(
                mt / self._tokens_per_word
            )

            if strategy == "truncate_end":
                result = " ".join(
                    words[:target_words]
                )
            elif strategy == (
                "truncate_start"
            ):
                result = " ".join(
                    words[-target_words:]
                )
            elif strategy == (
                "truncate_middle"
            ):
                half = target_words // 2
                result = (
                    " ".join(words[:half])
                    + " ... "
                    + " ".join(words[-half:])
                )
            else:
                result = " ".join(
                    words[:target_words]
                )

            self._stats[
                "overflows_handled"
            ] += 1

            return {
                "overflow": True,
                "text": result,
                "original_tokens": (
                    est_tokens
                ),
                "result_tokens": int(
                    len(result.split())
                    * self._tokens_per_word
                ),
                "strategy": strategy,
                "handled": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "handled": False,
                "error": str(e),
            }

    def get_window_status(
        self,
        window_id: str = "",
    ) -> dict[str, Any]:
        """Pencere durumunu getirir."""
        try:
            window = self._windows.get(
                window_id
            )
            if not window:
                return {
                    "retrieved": False,
                    "error": (
                        "Pencere bulunamadi"
                    ),
                }

            usage_pct = 0.0
            if window["available_tokens"] > 0:
                usage_pct = (
                    window["used_tokens"]
                    / window[
                        "available_tokens"
                    ]
                    * 100
                )

            return {
                "window_id": window_id,
                "max_tokens": window[
                    "max_tokens"
                ],
                "available_tokens": window[
                    "available_tokens"
                ],
                "used_tokens": window[
                    "used_tokens"
                ],
                "usage_pct": round(
                    usage_pct, 1
                ),
                "segments": len(
                    window["segments"]
                ),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def get_summary(
        self,
    ) -> dict[str, Any]:
        """Ozet getirir."""
        try:
            return {
                "total_windows": len(
                    self._windows
                ),
                "total_chunk_sets": len(
                    self._chunks
                ),
                "default_max_tokens": (
                    self._default_max
                ),
                "stats": dict(self._stats),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
