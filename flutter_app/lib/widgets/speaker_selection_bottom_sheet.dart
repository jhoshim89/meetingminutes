import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/speaker_model.dart';
import '../models/transcript_model.dart';
import '../providers/speaker_provider.dart';
import '../providers/meeting_provider.dart';

/// Bottom sheet for selecting a speaker to assign to a transcript line
/// Shows recommended speakers based on embedding similarity at the top
class SpeakerSelectionBottomSheet extends StatefulWidget {
  final TranscriptModel transcript;
  final VoidCallback? onSpeakerChanged;

  const SpeakerSelectionBottomSheet({
    super.key,
    required this.transcript,
    this.onSpeakerChanged,
  });

  /// Show the bottom sheet and return the selected speaker (or null if cancelled)
  static Future<void> show(
    BuildContext context, {
    required TranscriptModel transcript,
    VoidCallback? onSpeakerChanged,
  }) {
    return showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => SpeakerSelectionBottomSheet(
        transcript: transcript,
        onSpeakerChanged: onSpeakerChanged,
      ),
    );
  }

  @override
  State<SpeakerSelectionBottomSheet> createState() =>
      _SpeakerSelectionBottomSheetState();
}

enum UpdateRange {
  thisOnly,      // 이 구간만
  fromThisOn,    // 이후 구간부터
  all,           // 전체 구간
}

class _SpeakerSelectionBottomSheetState
    extends State<SpeakerSelectionBottomSheet> {
  String _searchQuery = '';
  bool _isUpdating = false;
  UpdateRange _selectedRange = UpdateRange.thisOnly;

  @override
  void initState() {
    super.initState();
    // Ensure speakers are loaded
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<SpeakerProvider>().fetchSpeakers();
    });
  }

  @override
  Widget build(BuildContext context) {
    return DraggableScrollableSheet(
      initialChildSize: 0.6,
      minChildSize: 0.4,
      maxChildSize: 0.9,
      builder: (context, scrollController) {
        return Container(
          decoration: const BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
          ),
          child: Column(
            children: [
              // Handle bar
              Container(
                margin: const EdgeInsets.only(top: 12, bottom: 8),
                width: 40,
                height: 4,
                decoration: BoxDecoration(
                  color: Colors.grey[300],
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
              // Title
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                child: Row(
                  children: [
                    const Icon(Icons.person, color: Colors.blue),
                    const SizedBox(width: 8),
                    const Expanded(
                      child: Text(
                        '화자 선택',
                        style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                    if (_isUpdating)
                      const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      ),
                  ],
                ),
              ),
              // Range selection section
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '적용 범위',
                      style: TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.bold,
                        color: Colors.grey[700],
                      ),
                    ),
                    const SizedBox(height: 8),
                    SegmentedButton<UpdateRange>(
                      segments: const [
                        ButtonSegment<UpdateRange>(
                          value: UpdateRange.thisOnly,
                          label: Text('이 구간만', style: TextStyle(fontSize: 12)),
                          icon: Icon(Icons.edit, size: 16),
                        ),
                        ButtonSegment<UpdateRange>(
                          value: UpdateRange.fromThisOn,
                          label: Text('이후 구간', style: TextStyle(fontSize: 12)),
                          icon: Icon(Icons.arrow_forward, size: 16),
                        ),
                        ButtonSegment<UpdateRange>(
                          value: UpdateRange.all,
                          label: Text('전체 구간', style: TextStyle(fontSize: 12)),
                          icon: Icon(Icons.select_all, size: 16),
                        ),
                      ],
                      selected: {_selectedRange},
                      onSelectionChanged: (Set<UpdateRange> newSelection) {
                        setState(() {
                          _selectedRange = newSelection.first;
                        });
                      },
                    ),
                    if (_selectedRange == UpdateRange.fromThisOn)
                      Padding(
                        padding: const EdgeInsets.only(top: 4),
                        child: Text(
                          '현재 시간(${widget.transcript.formattedStartTime}) 이후의 같은 화자 구간 모두 변경',
                          style: TextStyle(fontSize: 11, color: Colors.grey[600]),
                        ),
                      ),
                    if (_selectedRange == UpdateRange.all)
                      Padding(
                        padding: const EdgeInsets.only(top: 4),
                        child: Text(
                          '회의 전체에서 같은 화자의 모든 구간 변경',
                          style: TextStyle(fontSize: 11, color: Colors.grey[600]),
                        ),
                      ),
                  ],
                ),
              ),
              const Divider(height: 16),
              // Search field
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                child: TextField(
                  decoration: InputDecoration(
                    hintText: '화자 검색...',
                    prefixIcon: const Icon(Icons.search),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                    contentPadding: const EdgeInsets.symmetric(vertical: 12),
                  ),
                  onChanged: (value) {
                    setState(() {
                      _searchQuery = value.toLowerCase();
                    });
                  },
                ),
              ),
              // Speaker list
              Expanded(
                child: Consumer<SpeakerProvider>(
                  builder: (context, speakerProvider, child) {
                    if (speakerProvider.isLoading) {
                      return const Center(child: CircularProgressIndicator());
                    }

                    final registeredSpeakers = speakerProvider.registeredSpeakers;
                    final similarSpeakers = widget.transcript.speakerId != null
                        ? speakerProvider.getSimilarSpeakers(
                            widget.transcript.speakerId!,
                            maxResults: 3,
                          )
                        : <({SpeakerModel speaker, double similarity})>[];

                    // Filter by search query
                    final filteredSpeakers = _searchQuery.isEmpty
                        ? registeredSpeakers
                        : registeredSpeakers.where((s) {
                            return s.displayName
                                .toLowerCase()
                                .contains(_searchQuery);
                          }).toList();

                    return ListView(
                      controller: scrollController,
                      padding: const EdgeInsets.symmetric(horizontal: 16),
                      children: [
                        // Recommended speakers section
                        if (similarSpeakers.isNotEmpty &&
                            _searchQuery.isEmpty) ...[
                          _buildSectionHeader('추천 화자', Icons.auto_awesome),
                          ...similarSpeakers.map((result) {
                            return _buildSpeakerTile(
                              result.speaker,
                              similarity: result.similarity,
                              isRecommended: true,
                            );
                          }),
                          const SizedBox(height: 16),
                        ],

                        // All speakers section
                        _buildSectionHeader('전체 화자', Icons.people),

                        // Keep unknown option
                        _buildUnknownSpeakerTile(),

                        // All registered speakers
                        ...filteredSpeakers.map((speaker) {
                          return _buildSpeakerTile(speaker);
                        }),

                        if (filteredSpeakers.isEmpty && _searchQuery.isNotEmpty)
                          const Padding(
                            padding: EdgeInsets.all(32),
                            child: Center(
                              child: Text(
                                '검색 결과가 없습니다',
                                style: TextStyle(color: Colors.grey),
                              ),
                            ),
                          ),

                        const SizedBox(height: 16),
                      ],
                    );
                  },
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildSectionHeader(String title, IconData icon) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        children: [
          Icon(icon, size: 18, color: Colors.grey[600]),
          const SizedBox(width: 8),
          Text(
            title,
            style: TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.bold,
              color: Colors.grey[600],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSpeakerTile(
    SpeakerModel speaker, {
    double? similarity,
    bool isRecommended = false,
  }) {
    final isCurrentSpeaker = speaker.id == widget.transcript.speakerId;

    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      color: isCurrentSpeaker ? Colors.blue.shade50 : null,
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: isRecommended ? Colors.amber : Colors.blue,
          child: Text(
            speaker.displayName.isNotEmpty
                ? speaker.displayName[0].toUpperCase()
                : '?',
            style: const TextStyle(
              color: Colors.white,
              fontWeight: FontWeight.bold,
            ),
          ),
        ),
        title: Row(
          children: [
            Expanded(
              child: Text(
                speaker.displayName,
                style: TextStyle(
                  fontWeight:
                      isCurrentSpeaker ? FontWeight.bold : FontWeight.normal,
                ),
              ),
            ),
            if (isRecommended && similarity != null)
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                decoration: BoxDecoration(
                  color: Colors.amber.shade100,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(
                  '${(similarity * 100).toInt()}%',
                  style: TextStyle(
                    fontSize: 12,
                    color: Colors.amber.shade800,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            if (isCurrentSpeaker)
              const Icon(Icons.check_circle, color: Colors.blue, size: 20),
          ],
        ),
        subtitle: isCurrentSpeaker
            ? const Text('현재 선택됨', style: TextStyle(color: Colors.blue))
            : null,
        onTap: _isUpdating
            ? null
            : () => _selectSpeaker(speaker.id, speaker.displayName),
      ),
    );
  }

  Widget _buildUnknownSpeakerTile() {
    final isCurrentSpeaker = widget.transcript.speakerId == null;

    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      color: isCurrentSpeaker ? Colors.grey.shade100 : null,
      child: ListTile(
        leading: const CircleAvatar(
          backgroundColor: Colors.grey,
          child: Icon(Icons.person_outline, color: Colors.white),
        ),
        title: Row(
          children: [
            const Expanded(child: Text('Unknown')),
            if (isCurrentSpeaker)
              const Icon(Icons.check_circle, color: Colors.grey, size: 20),
          ],
        ),
        subtitle: const Text('화자를 알 수 없음'),
        onTap: _isUpdating ? null : () => _selectSpeaker(null, null),
      ),
    );
  }

  Future<void> _selectSpeaker(String? speakerId, String? speakerName) async {
    // Skip if already selected
    if (speakerId == widget.transcript.speakerId) {
      Navigator.pop(context);
      return;
    }

    setState(() {
      _isUpdating = true;
    });

    try {
      final meetingProvider = context.read<MeetingProvider>();
      bool success;
      int updatedCount = 0;

      switch (_selectedRange) {
        case UpdateRange.thisOnly:
          // Update only this transcript
          success = await meetingProvider.updateTranscriptSpeaker(
            widget.transcript.id,
            speakerId: speakerId,
            speakerName: speakerName,
          );
          updatedCount = success ? 1 : 0;
          break;

        case UpdateRange.fromThisOn:
          // Update this and all future transcripts with the same speaker
          updatedCount = await meetingProvider.bulkUpdateTranscriptSpeaker(
            meetingId: widget.transcript.meetingId,
            oldSpeakerId: widget.transcript.speakerId,
            newSpeakerId: speakerId,
            newSpeakerName: speakerName,
            fromTime: widget.transcript.startTime,
          );
          success = updatedCount > 0;
          break;

        case UpdateRange.all:
          // Update all transcripts with the same speaker
          updatedCount = await meetingProvider.bulkUpdateTranscriptSpeaker(
            meetingId: widget.transcript.meetingId,
            oldSpeakerId: widget.transcript.speakerId,
            newSpeakerId: speakerId,
            newSpeakerName: speakerName,
          );
          success = updatedCount > 0;
          break;
      }

      if (success && mounted) {
        widget.onSpeakerChanged?.call();
        Navigator.pop(context);

        String message;
        if (_selectedRange == UpdateRange.thisOnly) {
          message = speakerName != null
              ? '화자가 "$speakerName"(으)로 변경되었습니다'
              : '화자가 "Unknown"으로 변경되었습니다';
        } else {
          message = speakerName != null
              ? '$updatedCount개 구간의 화자가 "$speakerName"(으)로 변경되었습니다'
              : '$updatedCount개 구간의 화자가 "Unknown"으로 변경되었습니다';
        }

        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(message),
            duration: const Duration(seconds: 2),
          ),
        );
      } else if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('화자 변경에 실패했습니다'),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isUpdating = false;
        });
      }
    }
  }
}
