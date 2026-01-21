"""
Faster-Whisper STT Engine Module
CPU 최적화된 STT 엔진 (Oracle ARM 호환)
"""

import asyncio
from pathlib import Path
from typing import List, Dict, Optional
import numpy as np
from dataclasses import dataclass

from faster_whisper import WhisperModel
import soundfile as sf

from models import TranscriptSegment
from exceptions import TranscriptionError
from logger import get_logger

logger = get_logger("faster_whisper_engine")


@dataclass
class FasterWhisperConfig:
    """Configuration for Faster-Whisper engine"""
    model_size: str = "large-v3-turbo"
    device: str = "cpu"  # "cpu" or "cuda"
    compute_type: str = "int8"  # CPU: "int8", GPU: "float16"
    language: str = "ko"
    beam_size: int = 5
    confidence_threshold: float = 0.4
    cpu_threads: int = 4  # Oracle ARM A1 = 4 OCPU
    # VAD 설정
    vad_filter: bool = True
    vad_min_silence_duration_ms: int = 500
    vad_speech_pad_ms: int = 400
    # 세그먼트 병합 설정
    merge_segments: bool = True
    merge_gap_threshold: float = 0.5  # 0.5초 이내 간격은 병합
    merge_max_duration: float = 30.0  # 최대 30초까지 병합


class FasterWhisperEngine:
    """
    Faster-Whisper 기반 STT 엔진
    CPU에서 최적화된 성능, Oracle ARM 호환
    """

    def __init__(self, config: Optional[FasterWhisperConfig] = None):
        self.config = config or FasterWhisperConfig()
        self.model = None
        self._is_initialized = False

        logger.info(
            f"Faster-Whisper Engine initialized: "
            f"model={self.config.model_size}, "
            f"device={self.config.device}, "
            f"compute_type={self.config.compute_type}"
        )

    async def initialize(self) -> None:
        """모델 로드"""
        if self._is_initialized:
            return

        logger.log_operation_start("initialize_faster_whisper")

        try:
            logger.info(f"Loading Faster-Whisper model: {self.config.model_size}")

            self.model = await asyncio.to_thread(
                WhisperModel,
                self.config.model_size,
                device=self.config.device,
                compute_type=self.config.compute_type,
                cpu_threads=self.config.cpu_threads,
            )

            self._is_initialized = True
            logger.log_operation_success("initialize_faster_whisper")

        except Exception as e:
            logger.log_operation_failure("initialize_faster_whisper", e)
            raise TranscriptionError(f"Failed to initialize Faster-Whisper: {e}")

    async def transcribe(
        self,
        audio_path: Path,
        meeting_id: str,
        language: Optional[str] = None
    ) -> List[TranscriptSegment]:
        """오디오 파일 전사"""
        if not self._is_initialized:
            await self.initialize()

        logger.log_operation_start("transcribe_audio", meeting_id=meeting_id)

        try:
            lang = language or self.config.language

            # VAD 파라미터
            vad_params = None
            if self.config.vad_filter:
                vad_params = dict(
                    min_silence_duration_ms=self.config.vad_min_silence_duration_ms,
                    speech_pad_ms=self.config.vad_speech_pad_ms,
                )

            # 전사 실행
            segments_iter, info = await asyncio.to_thread(
                self.model.transcribe,
                str(audio_path),
                language=lang,
                beam_size=self.config.beam_size,
                vad_filter=self.config.vad_filter,
                vad_parameters=vad_params,
            )

            # 세그먼트 수집
            raw_segments = []
            for segment in segments_iter:
                raw_segments.append({
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text.strip(),
                    "confidence": getattr(segment, 'avg_logprob', None),
                })

            logger.info(f"Raw segments: {len(raw_segments)}")

            # 세그먼트 병합
            if self.config.merge_segments:
                merged_segments = self._merge_segments(raw_segments)
                logger.info(f"Merged segments: {len(merged_segments)}")
            else:
                merged_segments = raw_segments

            # TranscriptSegment 변환
            transcript_segments = []
            for seg in merged_segments:
                # confidence 변환 (log_prob → 0-1 스케일)
                confidence = None
                if seg.get("confidence") is not None:
                    # avg_logprob는 보통 -1 ~ 0 범위, 0에 가까울수록 높은 신뢰도
                    confidence = max(0, min(1, 1 + seg["confidence"]))

                if confidence is None or confidence >= self.config.confidence_threshold:
                    transcript_segments.append(TranscriptSegment(
                        meeting_id=meeting_id,
                        start_time=float(seg["start"]),
                        end_time=float(seg["end"]),
                        text=seg["text"],
                        confidence=confidence,
                        speaker_id=None,
                        speaker_label=None,
                    ))

            logger.log_operation_success(
                "transcribe_audio",
                meeting_id=meeting_id,
                segment_count=len(transcript_segments),
                audio_duration=info.duration,
            )

            return transcript_segments

        except Exception as e:
            logger.log_operation_failure("transcribe_audio", e, meeting_id=meeting_id)
            raise TranscriptionError(f"Failed to transcribe: {e}")

    def _merge_segments(self, segments: List[Dict]) -> List[Dict]:
        """
        작은 세그먼트를 문장 단위로 병합

        병합 기준:
        1. 시간 간격이 threshold 이내
        2. 병합 후 길이가 max_duration 이내
        3. 문장 부호로 끝나면 분리
        """
        if not segments:
            return []

        merged = []
        current = {
            "start": segments[0]["start"],
            "end": segments[0]["end"],
            "text": segments[0]["text"],
            "confidence": segments[0].get("confidence"),
        }

        for seg in segments[1:]:
            gap = seg["start"] - current["end"]
            merged_duration = seg["end"] - current["start"]
            ends_with_punct = current["text"].rstrip().endswith((".", "?", "!", "。", "？", "！"))

            # 병합 조건 확인
            should_merge = (
                gap <= self.config.merge_gap_threshold
                and merged_duration <= self.config.merge_max_duration
                and not ends_with_punct
            )

            if should_merge:
                # 병합
                current["end"] = seg["end"]
                current["text"] = current["text"].rstrip() + " " + seg["text"].lstrip()
                # confidence 평균
                if current["confidence"] is not None and seg.get("confidence") is not None:
                    current["confidence"] = (current["confidence"] + seg["confidence"]) / 2
            else:
                # 새 세그먼트 시작
                merged.append(current)
                current = {
                    "start": seg["start"],
                    "end": seg["end"],
                    "text": seg["text"],
                    "confidence": seg.get("confidence"),
                }

        # 마지막 세그먼트 추가
        merged.append(current)

        return merged

    def get_model_info(self) -> Dict:
        """모델 정보 반환"""
        return {
            "engine": "faster-whisper",
            "model_size": self.config.model_size,
            "device": self.config.device,
            "compute_type": self.config.compute_type,
            "language": self.config.language,
            "initialized": self._is_initialized,
            "cpu_threads": self.config.cpu_threads,
            "vad_filter": self.config.vad_filter,
            "merge_segments": self.config.merge_segments,
        }

    async def cleanup(self) -> None:
        """리소스 정리"""
        if self.model is not None:
            del self.model
            self.model = None
        self._is_initialized = False
        logger.info("Faster-Whisper cleanup complete")


# Factory function
def get_stt_engine(
    model_size: Optional[str] = None,
    device: str = "cpu",
    language: str = "ko",
    cpu_threads: int = 4,
) -> FasterWhisperEngine:
    """
    STT 엔진 생성

    Oracle ARM CPU 환경에서 사용하려면:
        engine = get_stt_engine(device="cpu", cpu_threads=4)
    """
    config = FasterWhisperConfig(
        model_size=model_size or "large-v3-turbo",
        device=device,
        compute_type="int8" if device == "cpu" else "float16",
        language=language,
        cpu_threads=cpu_threads,
    )
    return FasterWhisperEngine(config)
