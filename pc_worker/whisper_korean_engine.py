"""
Korean Fine-tuned Whisper Engine
HuggingFace Transformers 기반 한국어 최적화 모델 사용
"""

import asyncio
from pathlib import Path
from typing import List, Optional, Dict
from dataclasses import dataclass
import numpy as np
import torch
import soundfile as sf

from models import TranscriptSegment
from exceptions import TranscriptionError
from logger import get_logger

logger = get_logger("whisper_korean_engine")

# 사용 가능한 한국어 파인튜닝 모델들
KOREAN_MODELS = {
    "ghost613/whisper-large-v3-turbo-korean": {
        "size": "~3GB",
        "base": "large-v3-turbo",
        "description": "2024.10 최신, 빠른 속도"
    },
    "seastar105/whisper-medium-ko-zeroth": {
        "size": "~1.5GB",
        "base": "medium",
        "description": "Zeroth 한국어 데이터셋, 균형잡힌 성능"
    },
    "openai/whisper-large-v2": {
        "size": "~3GB",
        "base": "large-v2",
        "description": "원본 모델 (비교용)"
    }
}


@dataclass
class KoreanWhisperConfig:
    """한국어 Whisper 모델 설정"""
    model_id: str = "seastar105/whisper-medium-ko-zeroth"  # CER 1.48%, 가볍고 정확
    device: str = "cuda" if torch.cuda.is_available() else "cpu"
    torch_dtype: torch.dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    chunk_length_s: int = 30
    batch_size: int = 16
    return_timestamps: bool = True
    language: str = "korean"


class KoreanWhisperEngine:
    """
    HuggingFace Transformers 기반 한국어 Whisper 엔진
    한국어 파인튜닝 모델 사용으로 정확도 향상
    """

    def __init__(self, config: Optional[KoreanWhisperConfig] = None):
        self.config = config or KoreanWhisperConfig()
        self.pipe = None
        self._is_initialized = False

        logger.info(
            f"Korean Whisper Engine initialized: "
            f"model={self.config.model_id}, device={self.config.device}"
        )

    async def initialize(self) -> None:
        """모델 로드 (HuggingFace Transformers pipeline)"""
        if self._is_initialized:
            return

        logger.info(f"Loading Korean Whisper model: {self.config.model_id}")

        try:
            from transformers import pipeline

            self.pipe = await asyncio.to_thread(
                pipeline,
                "automatic-speech-recognition",
                model=self.config.model_id,
                torch_dtype=self.config.torch_dtype,
                device=self.config.device,
                chunk_length_s=self.config.chunk_length_s,
                batch_size=self.config.batch_size,
            )

            self._is_initialized = True
            logger.info(f"Model loaded successfully: {self.config.model_id}")

        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise TranscriptionError(f"Failed to initialize Korean Whisper: {e}")

    async def transcribe(
        self,
        audio_path: Path,
        meeting_id: str,
        language: Optional[str] = None
    ) -> List[TranscriptSegment]:
        """
        한국어 음성 인식 수행

        Args:
            audio_path: 오디오 파일 경로
            meeting_id: 회의 ID
            language: 언어 (기본: korean)

        Returns:
            TranscriptSegment 리스트
        """
        if not self._is_initialized:
            await self.initialize()

        logger.info(f"Transcribing: {audio_path}")

        try:
            # 오디오 로드
            audio = await self._load_audio(audio_path)

            # 음성 인식 실행
            generate_kwargs = {"language": language or self.config.language}

            result = await asyncio.to_thread(
                self.pipe,
                audio,
                return_timestamps=self.config.return_timestamps,
                generate_kwargs=generate_kwargs
            )

            # TranscriptSegment로 변환
            segments = self._convert_to_segments(result, meeting_id)

            logger.info(f"Transcription complete: {len(segments)} segments")
            return segments

        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise TranscriptionError(f"Failed to transcribe: {e}")

    async def _load_audio(self, audio_path: Path) -> Dict:
        """오디오 파일 로드 (16kHz 변환)"""
        SAMPLE_RATE = 16000

        def _load():
            audio_data, sr = sf.read(str(audio_path))
            audio_data = audio_data.astype(np.float32)

            # 스테레오 → 모노
            if len(audio_data.shape) > 1:
                audio_data = audio_data.mean(axis=1)

            # 리샘플링
            if sr != SAMPLE_RATE:
                import librosa
                audio_data = librosa.resample(audio_data, orig_sr=sr, target_sr=SAMPLE_RATE)

            return {"array": audio_data, "sampling_rate": SAMPLE_RATE}

        return await asyncio.to_thread(_load)

    def _convert_to_segments(
        self,
        result: Dict,
        meeting_id: str
    ) -> List[TranscriptSegment]:
        """Transformers 결과를 TranscriptSegment로 변환"""
        segments = []

        # chunks가 있으면 타임스탬프 포함
        if "chunks" in result:
            for chunk in result["chunks"]:
                timestamp = chunk.get("timestamp", (0, 0))
                start_time = timestamp[0] if timestamp[0] is not None else 0
                end_time = timestamp[1] if timestamp[1] is not None else start_time + 1

                segment = TranscriptSegment(
                    meeting_id=meeting_id,
                    start_time=float(start_time),
                    end_time=float(end_time),
                    text=chunk["text"].strip(),
                    confidence=None,  # Transformers pipeline은 confidence 미제공
                    speaker_id=None,
                    speaker_label=None
                )
                segments.append(segment)
        else:
            # 타임스탬프 없이 전체 텍스트만 있는 경우
            segment = TranscriptSegment(
                meeting_id=meeting_id,
                start_time=0.0,
                end_time=0.0,
                text=result["text"].strip(),
                confidence=None,
                speaker_id=None,
                speaker_label=None
            )
            segments.append(segment)

        return segments

    def get_model_info(self) -> Dict:
        """모델 정보 반환"""
        model_info = KOREAN_MODELS.get(self.config.model_id, {})
        return {
            "model_id": self.config.model_id,
            "device": self.config.device,
            "torch_dtype": str(self.config.torch_dtype),
            "initialized": self._is_initialized,
            "model_size": model_info.get("size", "unknown"),
            "base_model": model_info.get("base", "unknown"),
            "description": model_info.get("description", ""),
            "gpu_available": torch.cuda.is_available(),
            "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
        }

    async def cleanup(self) -> None:
        """리소스 정리"""
        logger.info("Cleaning up Korean Whisper resources")

        if self.pipe is not None:
            del self.pipe
            self.pipe = None

        self._is_initialized = False

        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        logger.info("Cleanup complete")


def get_korean_whisper_engine(
    model_id: Optional[str] = None,
    device: Optional[str] = None
) -> KoreanWhisperEngine:
    """
    한국어 Whisper 엔진 생성

    Args:
        model_id: HuggingFace 모델 ID (기본: ghost613/whisper-large-v3-turbo-korean)
        device: 디바이스 (cuda/cpu)

    Returns:
        KoreanWhisperEngine 인스턴스
    """
    config = KoreanWhisperConfig()

    if model_id:
        config.model_id = model_id
    if device:
        config.device = device

    return KoreanWhisperEngine(config)


def list_available_models() -> Dict:
    """사용 가능한 한국어 모델 목록"""
    return KOREAN_MODELS
