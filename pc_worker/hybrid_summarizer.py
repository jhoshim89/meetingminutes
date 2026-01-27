"""
Hybrid Summarizer - 통합 회의 요약기
====================================
구조화/비구조화 회의 모두 처리하는 단일 요약기

출력:
- 주요 주제 + 다음 할 일 (자연스러운 요약)
- 안건별 상세 (현황/논의/결의 등 자동 분류)
- 단락별 타임라인 요약
"""

import json
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field

from summarizer_utils import (
    call_ollama, chunk_transcript, parse_bullet_list,
    infer_category, CATEGORIES, DEFAULT_MODEL, OLLAMA_URL,
    ensure_ollama_ready, OllamaConnectionError, OllamaEmptyResponseError,
    logger
)


@dataclass
class HybridSummary:
    """통합 요약 결과"""
    main_topics: List[str] = field(default_factory=list)
    action_items: List[str] = field(default_factory=list)
    timeline_summaries: List[Dict] = field(default_factory=list)
    agenda_items: List[Dict] = field(default_factory=list)
    raw_text: str = ""
    processing_time: float = 0.0

    @property
    def summary(self) -> str:
        """MeetingSummary 호환: main_topics를 요약문으로 변환"""
        if self.main_topics:
            return " ".join(self.main_topics)
        return self.raw_text[:500] if self.raw_text else "(요약 없음)"

    @property
    def key_points(self) -> List[str]:
        """MeetingSummary 호환: main_topics 반환"""
        return self.main_topics

    @property
    def topics(self) -> List[str]:
        """MeetingSummary 호환: main_topics 반환"""
        return self.main_topics

    @property
    def categories(self) -> List[str]:
        """MeetingSummary 호환: 빈 리스트 반환"""
        return []


class SummaryValidationError(Exception):
    """요약 결과 검증 실패"""
    pass


class HybridSummarizer:
    """통합 회의 요약기"""

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        ollama_url: str = OLLAMA_URL,
        check_health_on_init: bool = True,
        strict_validation: bool = True
    ):
        """
        Args:
            model: Ollama 모델명
            ollama_url: Ollama 서버 URL
            check_health_on_init: 초기화 시 서버 헬스체크 수행 여부
            strict_validation: 엄격한 결과 검증 (빈 결과 시 예외 발생)
        """
        self.model = model
        self.ollama_url = ollama_url
        self.strict_validation = strict_validation

        if check_health_on_init:
            ensure_ollama_ready(ollama_url, model)

    def _call_llm(self, prompt: str, temperature: float = 0.3) -> str:
        """LLM 호출 래퍼"""
        return call_ollama(
            prompt, self.model, self.ollama_url, temperature,
            raise_on_empty=self.strict_validation
        )

    def _summarize_chunk(self, time_range: str, chunk: str) -> Dict:
        """청크를 하이브리드 방식으로 요약"""
        prompt = f"""다음 회의 내용을 분석하세요.

[회의 내용]
{chunk}

[출력 형식]
제목: (핵심 주제 5-15자)
요약: (전체 내용을 2-3문장으로)
포인트:
- 포인트1
- 포인트2
- 포인트3

위 형식으로만 작성하세요:"""

        response = self._call_llm(prompt)

        # 파싱
        lines = response.strip().split('\n')
        title = ""
        summary = ""
        points = []

        for line in lines:
            line = line.strip()
            if line.startswith('제목:'):
                title = line.replace('제목:', '').strip()
            elif line.startswith('요약:'):
                summary = line.replace('요약:', '').strip()
            elif line.startswith('-') or line.startswith('•'):
                point = line.lstrip('-•').strip()
                if point:
                    points.append(point)

        if not title and lines:
            title = lines[0].replace('제목:', '').strip()[:20]

        # 포인트에 카테고리 할당
        categorized_items = [
            {"label": infer_category(point), "content": point}
            for point in points[:5]
        ]

        return {
            "time": time_range,
            "title": title,
            "summary": summary,
            "points": points[:5],
            "categorized_items": categorized_items
        }

    def _cluster_into_agendas(self, chunk_summaries: List[Dict]) -> List[Dict]:
        """청크 요약들을 안건별로 클러스터링"""
        all_content = "\n".join([
            f"- {s['title']}: {s['summary']}"
            for s in chunk_summaries
        ])

        prompt = f"""다음 회의 내용들을 3-5개의 주요 안건으로 그룹화하세요.

{all_content}

각 안건에 대해:
안건1: (안건 제목)
- 관련 내용 요약

안건2: (안건 제목)
- 관련 내용 요약

형식으로 작성하세요:"""

        response = self._call_llm(prompt)

        # 파싱하여 안건 목록 생성
        agendas = []
        current_agenda = None

        for line in response.strip().split('\n'):
            line = line.strip()
            if re.match(r'^안건\d+:', line):
                if current_agenda:
                    agendas.append(current_agenda)
                title = re.sub(r'^안건\d+:\s*', '', line).strip()
                current_agenda = {"title": title, "items": []}
            elif line.startswith('-') and current_agenda:
                content = line.lstrip('-').strip()
                if content:
                    current_agenda["items"].append({
                        "label": infer_category(content),
                        "content": content
                    })

        if current_agenda:
            agendas.append(current_agenda)

        # 안건이 없으면 청크별로 안건 생성
        if not agendas:
            agendas = [
                {"title": chunk["title"], "items": chunk["categorized_items"]}
                for chunk in chunk_summaries
            ]

        return agendas

    def _extract_main_topics(self, chunk_summaries: List[Dict]) -> List[str]:
        """주요 주제 추출"""
        all_content = "\n".join([
            f"{s['title']}: {', '.join(s['points'])}"
            for s in chunk_summaries
        ])

        prompt = f"""다음 회의 내용에서 가장 중요한 주요 주제 3-5개를 추출하세요.

{all_content}

주요 주제만 간결하게 나열하세요 (각 줄에 - 로 시작):"""

        response = self._call_llm(prompt)
        return parse_bullet_list(response, max_items=5, max_length=60)

    def _extract_action_items(self, chunk_summaries: List[Dict]) -> List[str]:
        """다음 할 일 추출"""
        all_content = "\n".join([
            f"{s['title']}: {', '.join(s['points'])}"
            for s in chunk_summaries
        ])

        prompt = f"""다음 회의 내용에서 앞으로 해야 할 일(액션 아이템)을 추출하세요.
결정된 사항, 누군가 해야 할 일, 검토가 필요한 사항 등을 찾으세요.

{all_content}

다음 할 일만 간결하게 나열하세요 (각 줄에 - 로 시작):"""

        response = self._call_llm(prompt)
        return parse_bullet_list(response, max_items=7, max_length=80)

    def summarize(self, transcript: str, verbose: bool = True) -> HybridSummary:
        """전사본을 하이브리드 방식으로 요약"""
        start_time = time.time()

        # 1. 청크 분할
        chunks = chunk_transcript(transcript)
        if verbose:
            print(f"청크 수: {len(chunks)}")

        # 2. Map: 각 청크 하이브리드 요약
        chunk_summaries = []
        for i, (time_range, chunk) in enumerate(chunks):
            if verbose:
                print(f"  [{i+1}/{len(chunks)}] {time_range} 처리 중...", end=" ")

            chunk_start = time.time()
            summary = self._summarize_chunk(time_range, chunk)
            chunk_summaries.append(summary)

            if verbose:
                print(f"완료 ({time.time() - chunk_start:.1f}초)")

        # 3. Reduce: 주요 정보 추출
        if verbose:
            print("\n주요 주제 추출 중...")
        main_topics = self._extract_main_topics(chunk_summaries)

        if verbose:
            print("다음 할 일 추출 중...")
        action_items = self._extract_action_items(chunk_summaries)

        if verbose:
            print("안건별 클러스터링 중...")
        agenda_items = self._cluster_into_agendas(chunk_summaries)

        # 4. 타임라인 요약 정리
        timeline_summaries = [
            {"time": s["time"], "title": s["title"], "points": s["points"]}
            for s in chunk_summaries
        ]

        # 5. 결과 검증
        self._validate_summary(
            main_topics=main_topics,
            action_items=action_items,
            agenda_items=agenda_items,
            chunk_summaries=chunk_summaries,
            verbose=verbose
        )

        # 6. 결과 포맷팅
        raw_text = self._format_output(
            main_topics, action_items, agenda_items, timeline_summaries
        )

        processing_time = time.time() - start_time
        if verbose:
            print(f"\n총 소요 시간: {processing_time:.1f}초")

        return HybridSummary(
            main_topics=main_topics,
            action_items=action_items,
            timeline_summaries=timeline_summaries,
            agenda_items=agenda_items,
            raw_text=raw_text,
            processing_time=processing_time
        )

    def _validate_summary(
        self,
        main_topics: List[str],
        action_items: List[str],
        agenda_items: List[Dict],
        chunk_summaries: List[Dict],
        verbose: bool = True
    ) -> None:
        """
        요약 결과 검증

        Raises:
            SummaryValidationError: 결과가 비어있을 때 (strict_validation=True)
        """
        issues = []

        # 1. 주요 주제 체크
        if not main_topics:
            issues.append("주요 주제가 비어있음")

        # 2. 안건 체크
        empty_agendas = sum(1 for a in agenda_items if not a.get('title'))
        if empty_agendas == len(agenda_items) and agenda_items:
            issues.append(f"모든 안건({len(agenda_items)}개)이 비어있음")

        # 3. 청크 요약 체크
        empty_chunks = sum(1 for c in chunk_summaries if not c.get('title'))
        if empty_chunks > len(chunk_summaries) * 0.5:
            issues.append(f"청크 요약의 {empty_chunks}/{len(chunk_summaries)}개가 비어있음")

        if issues:
            warning_msg = "요약 결과 검증 경고:\n" + "\n".join(f"  - {i}" for i in issues)

            if verbose:
                print(f"\n⚠️ {warning_msg}")

            logger.warning(warning_msg)

            if self.strict_validation:
                raise SummaryValidationError(
                    f"요약 결과가 비어있습니다. LLM 응답을 확인하세요.\n{warning_msg}"
                )

    def _format_output(
        self,
        topics: List[str],
        actions: List[str],
        agendas: List[Dict],
        timeline: List[Dict]
    ) -> str:
        """통합 출력 포맷"""
        lines = []

        # Part 1: 자연 요약
        lines.append("=" * 50)
        lines.append("📋 요약")
        lines.append("=" * 50)
        lines.append("")
        lines.append("【주요 주제】")
        lines.extend(f"• {topic}" for topic in topics)
        lines.append("")
        lines.append("【다음 할 일】")
        lines.extend(f"☐ {item}" for item in actions)
        lines.append("")

        # Part 2: 구조화 요약
        lines.append("=" * 50)
        lines.append("📝 안건별 상세")
        lines.append("=" * 50)
        lines.append("")

        for i, agenda in enumerate(agendas, 1):
            lines.append(f"{i}. {agenda['title']}")
            for item in agenda.get('items', []):
                lines.append(f"   [{item['label']}] {item['content']}")
            lines.append("")

        # Part 3: 타임라인
        lines.append("=" * 50)
        lines.append("⏱️ 타임라인")
        lines.append("=" * 50)
        lines.append("")

        for section in timeline:
            lines.append(f"▸ {section['time']}")
            lines.append(f"  {section['title']}")
            for point in section['points'][:3]:
                lines.append(f"    - {point}")
            lines.append("")

        return '\n'.join(lines)

    def to_minutes_json(self, summary: HybridSummary, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """HybridSummary를 회의록 JSON으로 변환"""
        now = datetime.now()
        meta = metadata or {}

        return {
            "title": "회  의  록",
            "docNumber": meta.get("docNumber", f"NO {now.year}-{now.month:02d}"),
            "department": meta.get("department", ""),
            "location": meta.get("location", ""),
            "datetime": meta.get("datetime", now.strftime("%Y년 %m월 %d일 %H시")),
            "organizer": meta.get("organizer", ""),
            "agendaSummary": summary.main_topics,
            "agendaDetails": summary.agenda_items,
            "attendees": meta.get("attendees", ""),
            "attendeeCount": meta.get("attendeeCount", ""),
            "absentees": meta.get("absentees", ""),
            "absenteeCount": meta.get("absenteeCount", "")
        }

    def to_meeting_summary(
        self,
        summary: HybridSummary,
        meeting_id: str,
        model_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        HybridSummary를 MeetingSummary 호환 딕셔너리로 변환
        (main_worker.py에서 Supabase 저장용)
        """
        # 안건에서 카테고리 추출
        categories = set()
        for agenda in summary.agenda_items:
            for item in agenda.get('items', []):
                categories.add(item.get('label', ''))

        return {
            "meeting_id": meeting_id,
            "summary": summary.raw_text,
            "key_points": summary.main_topics,
            "action_items": summary.action_items,
            "topics": [agenda['title'] for agenda in summary.agenda_items],
            "categories": list(categories - {''}),  # 빈 문자열 제거
            "sentiment": None,
            "model_used": model_name or self.model
        }

    def generate_docx(
        self,
        transcript: str,
        output_path: str,
        metadata: Optional[Dict[str, Any]] = None,
        verbose: bool = True
    ) -> str:
        """전사본에서 DOCX 회의록 직접 생성"""
        summary = self.summarize(transcript, verbose=verbose)
        minutes_json = self.to_minutes_json(summary, metadata)

        # JSON 저장
        json_path = Path(output_path).with_suffix('.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(minutes_json, f, ensure_ascii=False, indent=2)

        if verbose:
            print(f"\n회의록 JSON 저장: {json_path}")

        # DOCX 생성
        script_path = Path(__file__).parent / "generate_minutes_docx.js"

        try:
            result = subprocess.run(
                ["node", str(script_path), str(json_path), output_path],
                capture_output=True,
                text=True,
                cwd=str(Path(__file__).parent)
            )

            if result.returncode == 0:
                if verbose:
                    print(f"DOCX 생성 완료: {output_path}")
                return output_path
            else:
                print(f"DOCX 생성 오류: {result.stderr}")
                return str(json_path)

        except FileNotFoundError:
            print("Node.js가 설치되지 않음 - JSON만 생성됨")
            return str(json_path)


def summarize_file(
    input_path: str,
    output_path: Optional[str] = None,
    model: str = DEFAULT_MODEL,
    output_format: str = "text",
    strict: bool = True
) -> None:
    """
    파일에서 전사본을 읽어 하이브리드 요약

    Args:
        input_path: 입력 전사본 파일 경로
        output_path: 출력 파일 경로 (없으면 자동 생성)
        model: Ollama 모델명
        output_format: 출력 형식 (text, json, docx)
        strict: 엄격 모드 (빈 결과 시 예외 발생)
    """
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 타임스탬프 라인 추출
    lines = content.strip().split('\n')
    transcript_lines = [
        line.strip() for line in lines
        if line.strip().startswith('[') and 's]' in line
    ]
    transcript = '\n'.join(transcript_lines) if transcript_lines else content

    print(f"입력 파일: {input_path}")
    print(f"전사본 길이: {len(transcript)} 자")
    print(f"모델: {model}")
    print(f"출력 형식: {output_format}")
    print(f"엄격 모드: {strict}")
    print("-" * 50)

    try:
        summarizer = HybridSummarizer(
            model=model,
            check_health_on_init=True,
            strict_validation=strict
        )
    except OllamaConnectionError as e:
        print(f"\n❌ Ollama 연결 실패:\n{e}")
        return

    base_path = input_path.rsplit('.', 1)[0]

    try:
        if output_format == "docx":
            output_path = output_path or f"{base_path}_회의록.docx"
            summarizer.generate_docx(transcript, output_path)

        elif output_format == "json":
            output_path = output_path or f"{base_path}_회의록.json"
            summary = summarizer.summarize(transcript)
            minutes_json = summarizer.to_minutes_json(summary)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(minutes_json, f, ensure_ascii=False, indent=2)
            print(f"\n✅ 저장 완료: {output_path}")

        else:
            output_path = output_path or f"{base_path}_하이브리드요약.txt"
            summary = summarizer.summarize(transcript)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(summary.raw_text)
            print(f"\n✅ 저장 완료: {output_path}")
            print("=" * 50)
            print(summary.raw_text)

    except (OllamaConnectionError, OllamaEmptyResponseError) as e:
        print(f"\n❌ LLM 오류: {e}")
    except SummaryValidationError as e:
        print(f"\n❌ 요약 검증 실패: {e}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="하이브리드 회의 요약기 (구조화 + 비구조화 통합)"
    )
    parser.add_argument('input_file', help='입력 전사본 파일')
    parser.add_argument('-o', '--output', help='출력 파일 경로')
    parser.add_argument('-f', '--format', default='text',
                        choices=['text', 'json', 'docx'],
                        help='출력 형식')
    parser.add_argument('-m', '--model', default=DEFAULT_MODEL,
                        help='Ollama 모델명')
    parser.add_argument('--no-strict', action='store_true',
                        help='엄격 모드 비활성화 (빈 결과 허용)')

    args = parser.parse_args()

    summarize_file(
        args.input_file,
        args.output,
        args.model,
        args.format,
        strict=not args.no_strict
    )
