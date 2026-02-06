"""Sesli asistan agent modulu.

OpenAI Whisper (STT) ve ElevenLabs (TTS) API'leri uzerinden:
- Ses dosyasindan metin cikarma (transkripsiyon)
- Metinden ses dosyasi olusturma (sentez)
- Sesli komut analizi ve ilgili agent'a yonlendirme
- Pydub ile ses dosyasi on-isleme

Sonuclari risk/aciliyet olarak siniflandirir ve karar matrisine iletir.
"""

import io
import json
import logging
import re
import tempfile
from pathlib import Path
from typing import Any

import anthropic
import httpx

from app.agents.base_agent import BaseAgent, TaskResult
from app.config import settings
from app.core.decision_matrix import (
    DECISION_RULES,
    ActionType,
    RiskLevel,
    UrgencyLevel,
)
from app.models.voice import (
    CommandAnalysis,
    CommandIntent,
    SynthesisResult,
    TranscriptionResult,
    VoiceAnalysisResult,
    VoiceConfig,
    VoiceLanguage,
    VoiceTaskType,
)

logger = logging.getLogger("atlas.agent.voice")

# === LLM prompt sablonlari ===
_COMMAND_ANALYSIS_PROMPT = (
    "Asagidaki sesli komutu analiz et ve uygun agent'a yonlendir.\n\n"
    "Mevcut agent'lar:\n"
    "- server_monitor: Sunucu durumu, CPU, RAM, disk kontrolu\n"
    "- security: Guvenlik taramasi, IP engelleme, SSL kontrolu\n"
    "- communication: E-posta yazma, okuma, gonderme\n"
    "- research: Web arastirmasi, tedarikci analizi\n"
    "- marketing: Google Ads, reklam analizi\n"
    "- coding: Kod analizi, guvenlik taramasi\n\n"
    "Sesli komut: \"{text}\"\n\n"
    "JSON formatinda yanit ver:\n"
    '{{"intent": "server_check|security_scan|send_email|research|'
    'marketing|code_review|status_report|general_question|unknown", '
    '"target_agent": "agent adi (bossa bos string)", '
    '"parameters": {{"anahtar": "deger"}}, '
    '"confidence": 0.0-1.0, '
    '"response_text": "kullaniciya Turkce kisa yanit"}}\n'
)


class VoiceAgent(BaseAgent):
    """Sesli asistan agent'i.

    OpenAI Whisper ve ElevenLabs API'leri ile ses isleme yapar.
    Sesli komutlari analiz edip ilgili agent'a yonlendirir.

    Attributes:
        config: Ses yapilandirmasi.
    """

    def __init__(
        self,
        config: VoiceConfig | None = None,
    ) -> None:
        """VoiceAgent'i baslatir.

        Args:
            config: Ses yapilandirmasi.
                Bos ise varsayilan degerler kullanilir.
        """
        super().__init__(name="voice")
        self.config = config or VoiceConfig()
        self._anthropic_client: anthropic.AsyncAnthropic | None = None
        self._http_client: httpx.AsyncClient | None = None

    # === Client yonetimi ===

    def _get_anthropic_client(self) -> anthropic.AsyncAnthropic:
        """Anthropic API istemcisini dondurur (lazy init).

        Returns:
            Yapilandirilmis AsyncAnthropic.

        Raises:
            ValueError: API key eksikse.
        """
        if self._anthropic_client is not None:
            return self._anthropic_client

        api_key = settings.anthropic_api_key.get_secret_value()
        if not api_key:
            raise ValueError("Anthropic API key yapilandirilmamis.")

        self._anthropic_client = anthropic.AsyncAnthropic(api_key=api_key)
        return self._anthropic_client

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Async HTTP istemcisini dondurur (lazy init).

        Returns:
            Yapilandirilmis httpx.AsyncClient.
        """
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=60.0)
        return self._http_client

    async def close(self) -> None:
        """Acik istemcileri kapatir."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()

    # === BaseAgent abstract metodlari ===

    async def execute(self, task: dict[str, Any]) -> TaskResult:
        """Ses gorevini calistirir.

        Args:
            task: Gorev detaylari. Beklenen anahtarlar:
                - task_type: Gorev tipi (transcribe/synthesize/command).
                - config: Ozel yapilandirma (dict, opsiyonel).
                - audio_path: Ses dosyasi yolu (transcribe/command icin).
                - audio_data: Base64 kodlanmis ses verisi (opsiyonel).
                - text: Sentezlenecek metin (synthesize icin).
                - language: Dil kodu (opsiyonel).
                - output_path: Cikti ses dosyasi yolu (synthesize icin).

        Returns:
            Ses islem sonuclarini iceren TaskResult.
        """
        # Yapilandirma guncelle
        if task.get("config"):
            self.config = VoiceConfig(**task["config"])

        # Gorev tipini belirle
        task_type_str = task.get("task_type", "command")
        try:
            task_type = VoiceTaskType(task_type_str)
        except ValueError:
            return TaskResult(
                success=False,
                message=f"Gecersiz gorev tipi: {task_type_str}",
                errors=[f"Gecerli tipler: {[t.value for t in VoiceTaskType]}"],
            )

        analysis_result = VoiceAnalysisResult(task_type=task_type)
        errors: list[str] = []

        try:
            if task_type == VoiceTaskType.TRANSCRIBE:
                await self._handle_transcribe(task, analysis_result)

            elif task_type == VoiceTaskType.SYNTHESIZE:
                await self._handle_synthesize(task, analysis_result)

            elif task_type == VoiceTaskType.COMMAND:
                await self._handle_command(task, analysis_result)

            analysis_result.summary = self._build_summary(analysis_result)

        except Exception as exc:
            self.logger.error("Ses isleme hatasi: %s", exc)
            errors.append(str(exc))

        # Karar matrisi icin analiz
        analysis = await self.analyze({"result": analysis_result.model_dump()})

        task_result = TaskResult(
            success=len(errors) == 0,
            data={
                "analysis_result": analysis_result.model_dump(),
                "analysis": analysis,
            },
            message=analysis_result.summary or "Ses gorevi tamamlandi.",
            errors=errors,
        )

        report_text = await self.report(task_result)
        self.logger.info("Ses Raporu:\n%s", report_text)

        return task_result

    async def analyze(self, data: dict[str, Any]) -> dict[str, Any]:
        """Analiz sonuclarini degerlendirir ve risk/aciliyet belirler.

        Args:
            data: {"result": VoiceAnalysisResult dict}.

        Returns:
            Analiz sonuclari: risk, urgency, action, summary.
        """
        result_dict = data.get("result", {})
        result = (
            VoiceAnalysisResult(**result_dict)
            if isinstance(result_dict, dict)
            else result_dict
        )

        issues: list[str] = []

        # Komut analizi kontrolu
        if result.command:
            if result.command.intent == CommandIntent.UNKNOWN:
                issues.append("Komut anlasilamadi")
            if result.command.confidence < 0.5:
                issues.append(
                    f"Dusuk guven skoru: {result.command.confidence:.2f}"
                )

        # Transkripsiyon kontrolu
        if result.transcription and not result.transcription.text.strip():
            issues.append("Transkripsiyon bos dondu")

        risk, urgency = self._map_to_risk_urgency(result)
        action = self._determine_action(risk, urgency)

        return {
            "task_type": result.task_type.value,
            "risk": risk.value,
            "urgency": urgency.value,
            "action": action.value,
            "summary": result.summary,
            "issues": issues,
            "stats": {
                "has_transcription": result.transcription is not None,
                "has_synthesis": result.synthesis is not None,
                "has_command": result.command is not None,
                "command_intent": (
                    result.command.intent.value if result.command else None
                ),
                "command_confidence": (
                    result.command.confidence if result.command else None
                ),
                "target_agent": (
                    result.command.target_agent if result.command else None
                ),
            },
        }

    async def report(self, result: TaskResult) -> str:
        """Ses sonucunu formatli rapor metnine donusturur.

        Args:
            result: Raporlanacak gorev sonucu.

        Returns:
            Formatlanmis rapor metni.
        """
        analysis = result.data.get("analysis", {})
        stats = analysis.get("stats", {})
        issues = analysis.get("issues", [])

        lines = [
            "=== SESLI ASISTAN RAPORU ===",
            f"Gorev: {analysis.get('task_type', 'bilinmiyor').upper()}",
            f"Risk: {analysis.get('risk', '-')} | "
            f"Aciliyet: {analysis.get('urgency', '-')}",
            f"Aksiyon: {analysis.get('action', '-')}",
            "",
            analysis.get("summary", ""),
            "",
        ]

        if stats.get("has_command"):
            lines.extend([
                "--- Komut Analizi ---",
                f"  Niyet: {stats.get('command_intent', '-')}",
                f"  Hedef Agent: {stats.get('target_agent', '-')}",
                f"  Guven: {stats.get('command_confidence', 0):.0%}",
                "",
            ])

        if issues:
            lines.append("--- Bulgular ---")
            for issue in issues:
                lines.append(f"  - {issue}")
            lines.append("")

        if result.errors:
            lines.append("HATALAR:")
            for err in result.errors:
                lines.append(f"  ! {err}")

        return "\n".join(lines)

    # === Gorev handler metodlari ===

    async def _handle_transcribe(
        self,
        task: dict[str, Any],
        result: VoiceAnalysisResult,
    ) -> None:
        """Ses dosyasini metne donusturur (Whisper API).

        Args:
            task: Gorev detaylari. Beklenen anahtarlar:
                - audio_path: Ses dosyasi yolu.
                - audio_data: Ses verisi (bytes).
                - language: Dil kodu (opsiyonel).
            result: Sonuclarin yazilacagi nesne.
        """
        audio_data = await self._load_audio(task)
        language = task.get("language", self.config.default_language.value)

        transcription = await self._whisper_transcribe(audio_data, language)
        result.transcription = transcription

    async def _handle_synthesize(
        self,
        task: dict[str, Any],
        result: VoiceAnalysisResult,
    ) -> None:
        """Metinden ses dosyasi olusturur (ElevenLabs API).

        Args:
            task: Gorev detaylari. Beklenen anahtarlar:
                - text: Sentezlenecek metin.
                - output_path: Cikti dosya yolu (opsiyonel).
                - voice_id: Ses kimlik numarasi (opsiyonel).
            result: Sonuclarin yazilacagi nesne.
        """
        text = task.get("text", "")
        if not text:
            raise ValueError("Sentez icin metin (text) gerekli.")

        output_path = task.get("output_path", "")
        voice_id = task.get("voice_id", self.config.elevenlabs_voice_id)

        synthesis = await self._elevenlabs_synthesize(
            text, output_path, voice_id,
        )
        result.synthesis = synthesis

    async def _handle_command(
        self,
        task: dict[str, Any],
        result: VoiceAnalysisResult,
    ) -> None:
        """Sesli komutu transkripsyon + analiz + yanit sentezi yapar.

        Tam pipeline: STT -> Komut Analizi -> TTS

        Args:
            task: Gorev detaylari. Beklenen anahtarlar:
                - audio_path: Ses dosyasi yolu.
                - audio_data: Ses verisi (bytes).
                - text: Dogrudan metin (ses dosyasi yerine).
                - language: Dil kodu (opsiyonel).
                - synthesize_response: Yaniti seslendir (bool, varsayilan True).
                - output_path: Yanit ses dosyasi yolu (opsiyonel).
            result: Sonuclarin yazilacagi nesne.
        """
        # 1. Transkripsiyon (metin verilmemisse)
        text = task.get("text", "")
        if not text:
            await self._handle_transcribe(task, result)
            if result.transcription:
                text = result.transcription.text

        if not text:
            raise ValueError("Komut metni alinamadi (ses veya text gerekli).")

        # 2. Komut analizi (LLM ile)
        command = await self._analyze_command(text)
        result.command = command

        # 3. Yanit sentezi (opsiyonel)
        if task.get("synthesize_response", True) and command.response_text:
            synthesis = await self._elevenlabs_synthesize(
                text=command.response_text,
                output_path=task.get("output_path", ""),
                voice_id=self.config.elevenlabs_voice_id,
            )
            result.synthesis = synthesis

    # === API entegrasyonlari ===

    async def _whisper_transcribe(
        self,
        audio_data: bytes,
        language: str = "",
    ) -> TranscriptionResult:
        """OpenAI Whisper API ile ses transkripsiyonu yapar.

        Args:
            audio_data: Ses dosyasi icerigi (bytes).
            language: Dil kodu (bossa otomatik algilar).

        Returns:
            Transkripsiyon sonucu.

        Raises:
            ValueError: OpenAI API key eksikse.
            httpx.HTTPStatusError: API hatasi.
        """
        api_key = settings.openai_api_key.get_secret_value()
        if not api_key:
            raise ValueError("OpenAI API key yapilandirilmamis.")

        client = await self._get_http_client()

        # multipart/form-data gonderimi
        files = {
            "file": ("audio.wav", audio_data, "audio/wav"),
        }
        data: dict[str, str] = {
            "model": self.config.whisper_model,
            "response_format": "verbose_json",
        }
        if language:
            data["language"] = language

        response = await client.post(
            "https://api.openai.com/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {api_key}"},
            files=files,
            data=data,
        )
        response.raise_for_status()
        resp_data = response.json()

        self.logger.info(
            "Whisper transkripsiyon tamamlandi: %d karakter",
            len(resp_data.get("text", "")),
        )

        return TranscriptionResult(
            text=resp_data.get("text", ""),
            language=resp_data.get("language", language),
            duration=resp_data.get("duration", 0.0),
        )

    async def _elevenlabs_synthesize(
        self,
        text: str,
        output_path: str = "",
        voice_id: str = "",
    ) -> SynthesisResult:
        """ElevenLabs API ile metin sentezler.

        Args:
            text: Sentezlenecek metin.
            output_path: Cikti dosya yolu. Bossa gecici dosya olusturur.
            voice_id: Ses kimlik numarasi.

        Returns:
            Sentez sonucu.

        Raises:
            ValueError: ElevenLabs API key eksikse.
            httpx.HTTPStatusError: API hatasi.
        """
        api_key = settings.elevenlabs_api_key.get_secret_value()
        if not api_key:
            raise ValueError("ElevenLabs API key yapilandirilmamis.")

        voice_id = voice_id or self.config.elevenlabs_voice_id
        client = await self._get_http_client()

        payload = {
            "text": text,
            "model_id": self.config.elevenlabs_model_id,
            "voice_settings": {
                "stability": self.config.stability,
                "similarity_boost": self.config.similarity_boost,
            },
        }

        response = await client.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
            headers={
                "xi-api-key": api_key,
                "Content-Type": "application/json",
                "Accept": "audio/mpeg",
            },
            json=payload,
        )
        response.raise_for_status()

        # Dosyaya kaydet
        if not output_path:
            tmp = tempfile.NamedTemporaryFile(
                suffix=".mp3", delete=False, prefix="atlas_voice_",
            )
            output_path = tmp.name
            tmp.close()

        Path(output_path).write_bytes(response.content)

        # Pydub ile sure hesapla
        duration = self._get_audio_duration(response.content)

        self.logger.info(
            "ElevenLabs sentez tamamlandi: %d karakter -> %s (%.1fs)",
            len(text), output_path, duration,
        )

        return SynthesisResult(
            audio_path=output_path,
            text=text,
            duration=duration,
            voice_id=voice_id,
            characters_used=len(text),
        )

    async def _analyze_command(self, text: str) -> CommandAnalysis:
        """Sesli komutu LLM ile analiz eder ve niyet cikarir.

        Args:
            text: Transkripsiyon metni.

        Returns:
            Komut analiz sonucu.
        """
        client = self._get_anthropic_client()

        user_message = _COMMAND_ANALYSIS_PROMPT.format(text=text)

        response = await client.messages.create(
            model=self.config.anthropic_model,
            max_tokens=500,
            system=(
                "Sen ATLAS AI asistaninin ses komut analizcisisin. "
                "Kullanicinin sesli komutlarini analiz edip uygun agent'a yonlendirirsin. "
                "Yaniti her zaman JSON formatinda dondur."
            ),
            messages=[{"role": "user", "content": user_message}],
        )

        llm_data = self._parse_llm_response(response.content[0].text)

        # Niyet siniflandirmasi
        try:
            intent = CommandIntent(llm_data.get("intent", "unknown"))
        except ValueError:
            intent = CommandIntent.UNKNOWN

        # Agent eslestirmesi
        target_agent = llm_data.get("target_agent", "")
        if not target_agent:
            target_agent = self._intent_to_agent(intent)

        return CommandAnalysis(
            original_text=text,
            intent=intent,
            target_agent=target_agent,
            parameters=llm_data.get("parameters", {}),
            confidence=float(llm_data.get("confidence", 0.0)),
            response_text=llm_data.get("response_text", ""),
        )

    # === Yardimci metodlar ===

    @staticmethod
    async def _load_audio(task: dict[str, Any]) -> bytes:
        """Gorevden ses verisini yukler.

        Oncelik sirasi: audio_data (bytes) > audio_path (dosya yolu).
        Pydub ile format donusumu destekler.

        Args:
            task: Gorev detaylari.

        Returns:
            Ses dosyasi icerigi (bytes).

        Raises:
            ValueError: Ses kaynagi belirtilmemisse.
            FileNotFoundError: Dosya bulunamadiysa.
        """
        # Dogrudan bytes verisi
        if task.get("audio_data"):
            return task["audio_data"]

        # Dosya yolundan yukle
        audio_path = task.get("audio_path", "")
        if not audio_path:
            raise ValueError("Ses kaynagi gerekli (audio_path veya audio_data).")

        path = Path(audio_path)
        if not path.exists():
            raise FileNotFoundError(f"Ses dosyasi bulunamadi: {audio_path}")

        raw_bytes = path.read_bytes()

        # Pydub ile WAV formatina donustur (Whisper uyumlulugu icin)
        if path.suffix.lower() not in (".wav", ".mp3", ".m4a", ".webm"):
            raw_bytes = VoiceAgent._convert_to_wav(raw_bytes, path.suffix)

        return raw_bytes

    @staticmethod
    def _convert_to_wav(audio_bytes: bytes, source_format: str) -> bytes:
        """Pydub ile ses dosyasini WAV formatina donusturur.

        Args:
            audio_bytes: Kaynak ses icerigi.
            source_format: Kaynak dosya uzantisi (orn: ".ogg").

        Returns:
            WAV formatinda ses icerigi.
        """
        try:
            from pydub import AudioSegment
        except ImportError:
            logger.warning("pydub yuklu degil, format donusumu atlanacak.")
            return audio_bytes

        fmt = source_format.lstrip(".").lower()
        audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format=fmt)
        buf = io.BytesIO()
        audio.export(buf, format="wav")
        return buf.getvalue()

    @staticmethod
    def _get_audio_duration(audio_bytes: bytes) -> float:
        """Pydub ile ses suresi hesaplar.

        Args:
            audio_bytes: Ses dosyasi icerigi.

        Returns:
            Sure (saniye). Pydub yuklu degilse 0.0 doner.
        """
        try:
            from pydub import AudioSegment
        except ImportError:
            return 0.0

        try:
            audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
            return len(audio) / 1000.0
        except Exception:
            return 0.0

    @staticmethod
    def _parse_llm_response(text: str) -> dict[str, Any]:
        """LLM yanitini JSON olarak parse eder.

        Args:
            text: LLM ham yaniti.

        Returns:
            Parse edilmis dict.
        """
        json_match = re.search(
            r"```(?:json)?\s*\n?(.*?)\n?```",
            text,
            re.DOTALL,
        )
        json_str = json_match.group(1) if json_match else text.strip()

        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            brace_match = re.search(r"\{.*\}", json_str, re.DOTALL)
            if brace_match:
                try:
                    return json.loads(brace_match.group(0))
                except json.JSONDecodeError:
                    pass
            return {"raw_text": text}

    @staticmethod
    def _intent_to_agent(intent: CommandIntent) -> str:
        """Niyet siniflandirmasini agent adina donusturur.

        Args:
            intent: Tespit edilen niyet.

        Returns:
            Hedef agent adi.
        """
        mapping = {
            CommandIntent.SERVER_CHECK: "server_monitor",
            CommandIntent.SECURITY_SCAN: "security",
            CommandIntent.SEND_EMAIL: "communication",
            CommandIntent.RESEARCH: "research",
            CommandIntent.MARKETING: "marketing",
            CommandIntent.CODE_REVIEW: "coding",
            CommandIntent.STATUS_REPORT: "",
            CommandIntent.GENERAL_QUESTION: "",
            CommandIntent.UNKNOWN: "",
        }
        return mapping.get(intent, "")

    # === Karar matrisi entegrasyonu ===

    @staticmethod
    def _map_to_risk_urgency(
        result: VoiceAnalysisResult,
    ) -> tuple[RiskLevel, UrgencyLevel]:
        """Ses bulgularini RiskLevel ve UrgencyLevel'a esler.

        Karar matrisi entegrasyonu:
        - Basarili transkripsiyon/sentez -> LOW/LOW (kaydet)
        - Komut anlasilamadi -> LOW/MEDIUM (bildir)
        - Acil agent yonlendirmesi -> komut niyetine gore

        Args:
            result: Ses analiz sonucu.

        Returns:
            (RiskLevel, UrgencyLevel) tuple.
        """
        risk = RiskLevel.LOW
        urgency = UrgencyLevel.LOW

        if result.command:
            # Komut anlasilamadiysa
            if result.command.intent == CommandIntent.UNKNOWN:
                urgency = UrgencyLevel.MEDIUM

            # Guvenlik veya sunucu komutu -> daha yuksek aciliyet
            if result.command.intent in (
                CommandIntent.SECURITY_SCAN,
                CommandIntent.SERVER_CHECK,
            ):
                urgency = UrgencyLevel.MEDIUM

        return risk, urgency

    @staticmethod
    def _determine_action(
        risk: RiskLevel,
        urgency: UrgencyLevel,
    ) -> ActionType:
        """Risk ve aciliyetten aksiyon tipini belirler.

        Args:
            risk: Risk seviyesi.
            urgency: Aciliyet seviyesi.

        Returns:
            Uygun aksiyon tipi.
        """
        action, _ = DECISION_RULES.get(
            (risk, urgency),
            (ActionType.NOTIFY, 0.5),
        )
        return action

    def _build_summary(self, result: VoiceAnalysisResult) -> str:
        """Analiz ozeti olusturur.

        Args:
            result: Ses analiz sonucu.

        Returns:
            Ozet metni.
        """
        parts: list[str] = []

        if result.transcription:
            text_preview = result.transcription.text[:80]
            parts.append(f"Transkripsiyon: \"{text_preview}...\"")

        if result.command:
            parts.append(
                f"Komut: {result.command.intent.value} "
                f"(guven: {result.command.confidence:.0%})"
            )
            if result.command.target_agent:
                parts.append(f"-> {result.command.target_agent}")

        if result.synthesis:
            parts.append(
                f"Sentez: {result.synthesis.duration:.1f}s ses olusturuldu"
            )

        return " | ".join(parts) if parts else "Ses gorevi tamamlandi."
