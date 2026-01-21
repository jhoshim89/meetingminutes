/**
 * 회의록 DOCX 생성기
 * sampledata_minutes.docx 양식과 완전 일치
 *
 * 사용법:
 *   node generate_minutes_docx.js <입력JSON> [출력DOCX]
 *   node generate_minutes_docx.js meeting_data.json ../data/회의록.docx
 */

const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, BorderStyle, WidthType, ShadingType, VerticalAlign
} = require('docx');
const fs = require('fs');
const path = require('path');

// ═══════════════════════════════════════════════════════════════════════════
// 설정: 테이블 레이아웃 (sampledata_minutes.docx 와 동일)
// ═══════════════════════════════════════════════════════════════════════════

const tableBorder = { style: BorderStyle.SINGLE, size: 4, color: "000000" };
const cellBorders = { top: tableBorder, bottom: tableBorder, left: tableBorder, right: tableBorder };

// 열 너비 (DXA 단위, 1440 = 1인치)
const COL1 = 1102;  // 레이블
const COL2 = 3860;  // 값1
const COL3 = 2135;  // 레이블2
const COL4 = 1585;  // 값2-1
const COL5 = 896;   // 값2-2 (인원수)
const TOTAL_WIDTH = COL1 + COL2 + COL3 + COL4 + COL5;  // 9578

// ═══════════════════════════════════════════════════════════════════════════
// 헬퍼 함수
// ═══════════════════════════════════════════════════════════════════════════

/**
 * 테이블 셀 생성
 */
function createCell(content, width, options = {}) {
  const {
    bold = false,
    shading = null,
    alignment = AlignmentType.LEFT,
    columnSpan = 1,
    rowSpan = 1,
    verticalAlign = VerticalAlign.CENTER
  } = options;

  const paragraphs = Array.isArray(content) ? content : [content];

  return new TableCell({
    borders: cellBorders,
    width: { size: width, type: WidthType.DXA },
    columnSpan: columnSpan,
    rowSpan: rowSpan,
    shading: shading ? { fill: shading, type: ShadingType.CLEAR } : undefined,
    verticalAlign: verticalAlign,
    children: paragraphs.map(text =>
      new Paragraph({
        alignment: alignment,
        children: [new TextRun({
          text: text,
          bold: bold,
          size: 20,
          font: "맑은 고딕"
        })]
      })
    )
  });
}

/**
 * 안건 요약 텍스트 생성
 */
function createAgendaSummaryContent(agendaSummary) {
  const lines = ["안 건 (요약)"];
  agendaSummary.forEach((item) => {
    lines.push(`- ${item}`);
  });
  return lines;
}

/**
 * 안건 상세 텍스트 생성
 */
function createAgendaDetailContent(agendaDetails) {
  const lines = [];
  agendaDetails.forEach((agenda, idx) => {
    lines.push(`${idx + 1}. ${agenda.title}`);
    agenda.items.forEach(item => {
      lines.push(`   ${item.label}: ${item.content}`);
    });
    lines.push(""); // 빈 줄
  });
  return lines.filter(l => l !== ""); // 마지막 빈줄 제거
}

// ═══════════════════════════════════════════════════════════════════════════
// 메인 문서 생성
// ═══════════════════════════════════════════════════════════════════════════

/**
 * 회의록 DOCX 문서 생성
 * @param {Object} meetingData - 회의록 데이터
 * @returns {Document} - docx Document 객체
 */
function createMinutesDocument(meetingData) {
  // 기본값 설정
  const data = {
    title: meetingData.title || "회  의  록",
    docNumber: meetingData.docNumber || "",
    department: meetingData.department || "",
    location: meetingData.location || "",
    datetime: meetingData.datetime || "",
    organizer: meetingData.organizer || "",
    agendaSummary: meetingData.agendaSummary || [],
    agendaDetails: meetingData.agendaDetails || [],
    attendees: meetingData.attendees || "",
    attendeeCount: meetingData.attendeeCount || "",
    absentees: meetingData.absentees || "",
    absenteeCount: meetingData.absenteeCount || ""
  };

  return new Document({
    styles: {
      default: {
        document: {
          run: { font: "맑은 고딕", size: 20 }
        }
      }
    },
    sections: [{
      properties: {
        page: {
          margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 }
        }
      },
      children: [
        new Table({
          width: { size: TOTAL_WIDTH, type: WidthType.DXA },
          columnWidths: [COL1, COL2, COL3, COL4, COL5],
          rows: [
            // ─────────────────────────────────────────────────────────────
            // 행 1: 제목 (5열 병합) - 회의록 가운데, NO 오른쪽 정렬
            // ─────────────────────────────────────────────────────────────
            new TableRow({
              children: [
                new TableCell({
                  borders: cellBorders,
                  width: { size: TOTAL_WIDTH, type: WidthType.DXA },
                  columnSpan: 5,
                  verticalAlign: VerticalAlign.CENTER,
                  children: [
                    new Paragraph({
                      alignment: AlignmentType.CENTER,
                      spacing: { before: 200, after: 0 },
                      children: [
                        new TextRun({ text: data.title, bold: true, size: 36, font: "맑은 고딕" })
                      ]
                    }),
                    ...(data.docNumber ? [new Paragraph({
                      alignment: AlignmentType.RIGHT,
                      spacing: { before: 0, after: 100 },
                      children: [
                        new TextRun({ text: data.docNumber, size: 20, font: "맑은 고딕" })
                      ]
                    })] : [])
                  ]
                })
              ]
            }),

            // ─────────────────────────────────────────────────────────────
            // 행 2: 부서명 / 장소
            // ─────────────────────────────────────────────────────────────
            new TableRow({
              children: [
                createCell("부서명", COL1, { bold: true, shading: "E7E6E6", alignment: AlignmentType.CENTER }),
                createCell(` ${data.department}`, COL2),
                createCell("장   소", COL3, { bold: true, shading: "E7E6E6", alignment: AlignmentType.CENTER }),
                new TableCell({
                  borders: cellBorders,
                  width: { size: COL4 + COL5, type: WidthType.DXA },
                  columnSpan: 2,
                  verticalAlign: VerticalAlign.CENTER,
                  children: [new Paragraph({
                    children: [new TextRun({ text: data.location, size: 20, font: "맑은 고딕" })]
                  })]
                })
              ]
            }),

            // ─────────────────────────────────────────────────────────────
            // 행 3: 일시 / 소집자
            // ─────────────────────────────────────────────────────────────
            new TableRow({
              children: [
                createCell("일  시", COL1, { bold: true, shading: "E7E6E6", alignment: AlignmentType.CENTER }),
                createCell(` ${data.datetime}`, COL2),
                createCell("소집 및 발안자", COL3, { bold: true, shading: "E7E6E6", alignment: AlignmentType.CENTER }),
                new TableCell({
                  borders: cellBorders,
                  width: { size: COL4 + COL5, type: WidthType.DXA },
                  columnSpan: 2,
                  verticalAlign: VerticalAlign.CENTER,
                  children: [new Paragraph({
                    children: [new TextRun({ text: data.organizer, size: 20, font: "맑은 고딕" })]
                  })]
                })
              ]
            }),

            // ─────────────────────────────────────────────────────────────
            // 행 4: 안건 요약 (5열 병합)
            // ─────────────────────────────────────────────────────────────
            new TableRow({
              children: [
                new TableCell({
                  borders: cellBorders,
                  width: { size: TOTAL_WIDTH, type: WidthType.DXA },
                  columnSpan: 5,
                  children: createAgendaSummaryContent(data.agendaSummary).map((text, idx) =>
                    new Paragraph({
                      spacing: idx === 0 ? { before: 100, after: 100 } : { before: 40 },
                      children: [new TextRun({
                        text: text,
                        bold: idx === 0,
                        size: 20,
                        font: "맑은 고딕"
                      })]
                    })
                  )
                })
              ]
            }),

            // ─────────────────────────────────────────────────────────────
            // 행 5: 안건 상세 (5열 병합)
            // ─────────────────────────────────────────────────────────────
            new TableRow({
              children: [
                new TableCell({
                  borders: cellBorders,
                  width: { size: TOTAL_WIDTH, type: WidthType.DXA },
                  columnSpan: 5,
                  children: createAgendaDetailContent(data.agendaDetails).map((text) => {
                    const isTitle = /^\d+\./.test(text);
                    return new Paragraph({
                      spacing: isTitle ? { before: 150, after: 50 } : { before: 30 },
                      children: [new TextRun({
                        text: text,
                        bold: isTitle,
                        size: 20,
                        font: "맑은 고딕"
                      })]
                    });
                  })
                })
              ]
            }),

            // ─────────────────────────────────────────────────────────────
            // 행 6: 서명 문구 (5열 병합)
            // ─────────────────────────────────────────────────────────────
            new TableRow({
              children: [
                new TableCell({
                  borders: cellBorders,
                  width: { size: TOTAL_WIDTH, type: WidthType.DXA },
                  columnSpan: 5,
                  verticalAlign: VerticalAlign.CENTER,
                  children: [new Paragraph({
                    alignment: AlignmentType.CENTER,
                    spacing: { before: 150, after: 150 },
                    children: [new TextRun({
                      text: "위 논의사항을 확인하기 위하여 서명함",
                      size: 20,
                      font: "맑은 고딕"
                    })]
                  })]
                })
              ]
            }),

            // ─────────────────────────────────────────────────────────────
            // 행 7: 참석자 (첫 번째 셀 rowSpan=2)
            // ─────────────────────────────────────────────────────────────
            new TableRow({
              children: [
                new TableCell({
                  borders: cellBorders,
                  width: { size: COL1, type: WidthType.DXA },
                  rowSpan: 2,
                  shading: { fill: "E7E6E6", type: ShadingType.CLEAR },
                  verticalAlign: VerticalAlign.CENTER,
                  children: [new Paragraph({
                    alignment: AlignmentType.CENTER,
                    children: [new TextRun({ text: "참석자", bold: true, size: 20, font: "맑은 고딕" })]
                  })]
                }),
                new TableCell({
                  borders: cellBorders,
                  width: { size: COL2 + COL3 + COL4, type: WidthType.DXA },
                  columnSpan: 3,
                  verticalAlign: VerticalAlign.CENTER,
                  children: [new Paragraph({
                    children: [new TextRun({ text: data.attendees, size: 20, font: "맑은 고딕" })]
                  })]
                }),
                createCell(data.attendeeCount, COL5, { alignment: AlignmentType.CENTER })
              ]
            }),

            // ─────────────────────────────────────────────────────────────
            // 행 8: 불참자 (첫 번째 셀은 위에서 병합됨)
            // ─────────────────────────────────────────────────────────────
            new TableRow({
              children: [
                new TableCell({
                  borders: cellBorders,
                  width: { size: COL2 + COL3 + COL4, type: WidthType.DXA },
                  columnSpan: 3,
                  children: data.absentees.split('\n').map(line =>
                    new Paragraph({
                      children: [new TextRun({ text: ` ${line}`, size: 20, font: "맑은 고딕" })]
                    })
                  )
                }),
                createCell(data.absenteeCount, COL5, { alignment: AlignmentType.CENTER })
              ]
            })
          ]
        })
      ]
    }]
  });
}

/**
 * 회의록 DOCX 파일 생성
 * @param {Object} meetingData - 회의록 데이터
 * @param {string} outputPath - 출력 파일 경로
 * @returns {Promise<string>} - 생성된 파일 경로
 */
async function generateMinutesDocx(meetingData, outputPath) {
  const doc = createMinutesDocument(meetingData);
  const buffer = await Packer.toBuffer(doc);
  fs.writeFileSync(outputPath, buffer);
  return outputPath;
}

// ═══════════════════════════════════════════════════════════════════════════
// CLI 실행
// ═══════════════════════════════════════════════════════════════════════════

async function main() {
  const args = process.argv.slice(2);

  if (args.length === 0) {
    // 샘플 데이터로 테스트
    console.log("사용법: node generate_minutes_docx.js <입력JSON> [출력DOCX]");
    console.log("       입력 없이 실행하면 샘플 데이터로 테스트합니다.\n");

    const sampleData = {
      title: "회  의  록",
      docNumber: "NO 2026-01",
      department: "수의과대학장",
      location: "수의과대학 교수회의실",
      datetime: "2026년 1월 15일 11시",
      organizer: "수의과대학장",
      agendaSummary: [
        "학과 회의 운영 방식 변경",
        "교학위원회 구성 변경",
        "김해 유회부지 활용 방안",
        "학과 운영 및 교육 관련 사항"
      ],
      agendaDetails: [
        {
          title: "학과 회의 운영 방식 변경",
          items: [
            { label: "배경", content: "교수님들 증가 및 회의 효율화 필요" },
            { label: "논의", content: "기존에는 학장이 주도하였으나, 앞으로는 학과장 또는 강찬근 부학장이 주도하도록 변경" },
            { label: "결의", content: "학과회의는 학과장이 주재하는 것으로 합의" }
          ]
        },
        {
          title: "교학위원회 구성 변경",
          items: [
            { label: "현황", content: "현 집행부 구성: 학장, 교학부학장, 연구부학장, 행정실장 총 7인" },
            { label: "논의", content: "1안: 기존 구성 유지 + 유관기관장 3인 추가 (총 10인). 2안: 현 집행부 6인 + 유관기관장 3인 (총 10인), 규정 개정 필요" },
            { label: "결의", content: "교수님들의 의견 수렴 후 진행 예정" }
          ]
        }
      ],
      attendees: "김학장, 강부학장, 박연구부학장, 이행정실장, 최교수, 정교수",
      attendeeCount: "총 6명",
      absentees: "연구년제: 문교수\n(출장) 국내: 송교수",
      absenteeCount: "총 2명"
    };

    const outputPath = path.join(__dirname, '..', 'data', '회의록_샘플.docx');
    await generateMinutesDocx(sampleData, outputPath);
    console.log(`샘플 회의록 생성 완료: ${outputPath}`);
    return;
  }

  // JSON 파일에서 데이터 읽기
  const inputPath = args[0];
  const outputPath = args[1] || inputPath.replace(/\.json$/i, '.docx');

  if (!fs.existsSync(inputPath)) {
    console.error(`입력 파일을 찾을 수 없습니다: ${inputPath}`);
    process.exit(1);
  }

  try {
    const jsonContent = fs.readFileSync(inputPath, 'utf-8');
    const meetingData = JSON.parse(jsonContent);

    await generateMinutesDocx(meetingData, outputPath);
    console.log(`회의록 생성 완료: ${outputPath}`);
  } catch (e) {
    console.error(`오류 발생: ${e.message}`);
    process.exit(1);
  }
}

// 모듈 내보내기
module.exports = {
  createMinutesDocument,
  generateMinutesDocx
};

// CLI 실행
if (require.main === module) {
  main().catch(console.error);
}
