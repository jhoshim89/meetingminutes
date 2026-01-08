# STT + Speaker Diarization Accuracy Report
**Date**: 2026-01-08
**Version**: Phase 2 - Task 2.1
**Test Duration**: Pending

---

## Executive Summary

### Overall Performance
- **STT Accuracy (Korean)**: Pending validation
- **Speaker Identification**: Pending validation
- **Processing Speed**: Pending validation
- **System Stability**: Pending validation

### Status
- ⏳ **Awaiting real Korean audio samples for validation**
- ⏳ **Awaiting ground truth transcripts**
- ⏳ **Awaiting ground truth speaker labels**

---

## 1. Speech-to-Text (WhisperX) Accuracy

### Test Methodology
1. **Dataset**: Korean meeting audio samples (minimum 30 minutes)
2. **Ground Truth**: Human-verified transcripts
3. **Metrics**:
   - Word Error Rate (WER)
   - Character Error Rate (CER)
   - Confidence Score Distribution

### Target Metrics
- ✅ **WER < 10%** (90%+ accuracy)
- ✅ **CER < 5%**
- ✅ **Confidence > 0.8** for 80%+ of segments

### Results

#### Test Case 1: Clear Studio Recording
- Audio Duration: TBD
- Speakers: TBD
- WER: TBD
- CER: TBD
- Status: ⏳ Pending

#### Test Case 2: Meeting Room Recording
- Audio Duration: TBD
- Speakers: TBD
- WER: TBD
- CER: TBD
- Status: ⏳ Pending

#### Test Case 3: Noisy Environment
- Audio Duration: TBD
- Speakers: TBD
- WER: TBD
- CER: TBD
- Status: ⏳ Pending

### WER Calculation
```
WER = (S + D + I) / N

Where:
  S = Substitutions (wrong words)
  D = Deletions (missed words)
  I = Insertions (extra words)
  N = Total words in reference
```

### Common Errors
- [ ] Korean technical terms
- [ ] Names and proper nouns
- [ ] Numbers and dates
- [ ] English words in Korean context
- [ ] Fast speech
- [ ] Overlapping speech

---

## 2. Speaker Diarization Accuracy

### Test Methodology
1. **Dataset**: Multi-speaker Korean meetings
2. **Ground Truth**: Manual speaker labels with timestamps
3. **Metrics**:
   - Diarization Error Rate (DER)
   - Speaker Confusion
   - Missed Speaker
   - False Alarm

### Target Metrics
- ✅ **DER < 20%** (80%+ accuracy)
- ✅ **Speaker Confusion < 10%**
- ✅ **Missed Speaker < 5%**
- ✅ **False Alarm < 5%**

### Results

#### Test Case 1: 2 Speakers
- Audio Duration: TBD
- Actual Speakers: 2
- Detected Speakers: TBD
- DER: TBD
- Status: ⏳ Pending

#### Test Case 2: 3-4 Speakers
- Audio Duration: TBD
- Actual Speakers: 3-4
- Detected Speakers: TBD
- DER: TBD
- Status: ⏳ Pending

#### Test Case 3: 5+ Speakers
- Audio Duration: TBD
- Actual Speakers: 5+
- Detected Speakers: TBD
- DER: TBD
- Status: ⏳ Pending

### DER Calculation
```
DER = (Missed Speaker + False Alarm + Speaker Confusion) / Total Speech Time

Components:
  - Missed Speaker: Speech incorrectly detected as non-speech
  - False Alarm: Non-speech incorrectly detected as speech
  - Speaker Confusion: Speech assigned to wrong speaker
```

### Common Issues
- [ ] Similar voices
- [ ] Overlapping speech
- [ ] Background noise
- [ ] Short utterances
- [ ] Speaker turn frequency

---

## 3. Performance Benchmarks

### Hardware Configuration
- **GPU**: TBD
- **CPU**: TBD
- **RAM**: TBD
- **VRAM**: TBD

### Processing Time (10-minute audio)

#### GPU Performance
| Component | Time (s) | Real-time Factor |
|-----------|----------|------------------|
| Preprocessing | TBD | TBD |
| WhisperX STT | TBD | TBD |
| Diarization | TBD | TBD |
| Alignment | TBD | TBD |
| **Total** | **TBD** | **TBD** |

**Target**: < 180 seconds (3 minutes) = **0.3x real-time**

#### CPU Performance
| Component | Time (s) | Real-time Factor |
|-----------|----------|------------------|
| Preprocessing | TBD | TBD |
| WhisperX STT | TBD | TBD |
| Diarization | TBD | TBD |
| Alignment | TBD | TBD |
| **Total** | **TBD** | **TBD** |

**Target**: < 600 seconds (10 minutes) = **1.0x real-time**

### Memory Usage
- **Peak RAM**: TBD
- **Peak VRAM**: TBD
- **Memory Leaks**: TBD

---

## 4. Korean Language Specific Tests

### Korean-Specific Challenges
1. **Honorifics and Formality Levels**
   - 존댓말 (Formal speech)
   - 반말 (Informal speech)
   - Accuracy: TBD

2. **Konglish (Korean + English)**
   - Mixed language segments
   - Accuracy: TBD

3. **Technical Terms**
   - IT terminology
   - Academic vocabulary
   - Accuracy: TBD

4. **Regional Dialects**
   - 서울 (Seoul) accent
   - 부산 (Busan) accent
   - 전라도 (Jeolla) accent
   - Accuracy: TBD

### Results
- [ ] Test with formal Korean speech
- [ ] Test with informal Korean speech
- [ ] Test with Konglish terms
- [ ] Test with technical vocabulary
- [ ] Test with different regional accents

---

## 5. Edge Cases and Error Handling

### Tested Scenarios
- [ ] Very short audio (< 10 seconds)
- [ ] Very long audio (> 60 minutes)
- [ ] Single speaker
- [ ] Many speakers (> 5)
- [ ] Silent audio
- [ ] Pure noise
- [ ] Corrupted audio file
- [ ] Unsupported format
- [ ] Extremely quiet audio
- [ ] Clipped/distorted audio

### Error Recovery
- [ ] Graceful failure handling
- [ ] Informative error messages
- [ ] Logging completeness
- [ ] Retry mechanisms

---

## 6. Test Data Requirements

### Required Audio Samples
1. **Studio Quality**
   - 2-speaker conversation: 10 minutes
   - 3-speaker discussion: 10 minutes
   - 4+ speaker meeting: 10 minutes

2. **Real Meeting Recordings**
   - Office meeting: 20 minutes
   - Classroom lecture: 20 minutes
   - Conference presentation: 20 minutes

3. **Challenging Conditions**
   - Background noise: 10 minutes
   - Overlapping speech: 10 minutes
   - Phone/VoIP quality: 10 minutes

**Total Required**: ~90 minutes of labeled Korean audio

### Ground Truth Requirements
For each audio sample:
- [ ] Full transcript (human-verified)
- [ ] Speaker labels with timestamps
- [ ] Audio quality notes
- [ ] Recording environment details

---

## 7. Validation Checklist

### Pre-Testing
- [ ] WhisperX model downloaded (large-v2)
- [ ] Pyannote models downloaded (with HF token)
- [ ] Test audio samples prepared
- [ ] Ground truth transcripts ready
- [ ] GPU/CPU environment configured

### During Testing
- [ ] Record all metrics systematically
- [ ] Log errors and warnings
- [ ] Monitor resource usage
- [ ] Note edge cases and failures

### Post-Testing
- [ ] Calculate WER for all samples
- [ ] Calculate DER for all samples
- [ ] Analyze error patterns
- [ ] Document improvements needed
- [ ] Update accuracy metrics

---

## 8. Acceptance Criteria

### Minimum Requirements (Phase 2 - Task 2.1)
- ✅ STT accuracy ≥ 90% (WER ≤ 10%)
- ✅ Diarization accuracy ≥ 80% (DER ≤ 20%)
- ✅ Processing time ≤ 0.3x real-time (GPU)
- ✅ Processing time ≤ 1.0x real-time (CPU)
- ✅ Memory stable (no leaks)
- ✅ All tests pass

### Current Status
- ⏳ **Awaiting real audio samples for validation**
- ⏳ **Unit tests: Pending**
- ⏳ **Integration tests: Pending**
- ⏳ **Performance benchmarks: Pending**

---

## 9. Next Steps

### Immediate Actions
1. [ ] Collect Korean meeting audio samples
2. [ ] Create ground truth transcripts
3. [ ] Label speaker segments
4. [ ] Run comprehensive test suite
5. [ ] Calculate accuracy metrics
6. [ ] Optimize based on results

### Improvements Needed
- [ ] TBD after testing
- [ ] TBD after testing
- [ ] TBD after testing

---

## 10. Appendix

### Test Commands
```bash
# Run all tests
pytest tests/test_stt_diarization.py -v

# Run only fast tests
pytest tests/test_stt_diarization.py -v -m "not slow"

# Run integration tests
pytest tests/test_stt_diarization.py -v -m integration

# Run with coverage
pytest tests/test_stt_diarization.py -v --cov=. --cov-report=html

# Run benchmarks
pytest tests/test_stt_diarization.py -v -m benchmark
```

### References
- WhisperX Paper: https://arxiv.org/abs/2303.00747
- Pyannote.audio: https://github.com/pyannote/pyannote-audio
- WER Calculation: https://en.wikipedia.org/wiki/Word_error_rate
- DER Calculation: https://pyannote.github.io/pyannote-metrics/reference.html

---

**Report Status**: 🟡 In Progress
**Last Updated**: 2026-01-08
**Next Review**: After collecting test audio samples
