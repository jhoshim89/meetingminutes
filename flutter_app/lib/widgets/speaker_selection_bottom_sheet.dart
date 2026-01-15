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
    // 호출 시점의 Provider 인스턴스 캡처 (showModalBottomSheet의 새 context는 Provider 범위 밖)
    final speakerProvider = context.read<SpeakerProvider>();
    final meetingProvider = context.read<MeetingProvider>();

    return showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => MultiProvider(
        providers: [
          ChangeNotifierProvider.value(value: speakerProvider),
          ChangeNotifierProvider.value(value: meetingProvider),
        ],
        child: SpeakerSelectionBottomSheet(
          transcript: transcript,
          onSpeakerChanged: onSpeakerChanged,
        ),
      ),
    );
  }

  @override
  State<SpeakerSelectionBottomSheet> createState() =>
      _SpeakerSelectionBottomSheetState();
}

class _SpeakerSelectionBottomSheetState
    extends State<SpeakerSelectionBottomSheet> {
  String _searchQuery = '';
  bool _isUpdating = false;

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
                      )
                    else
                      TextButton.icon(
                        onPressed: _showAddSpeakerDialog,
                        icon: const Icon(Icons.person_add, size: 20),
                        label: const Text('화자 추가', style: TextStyle(fontWeight: FontWeight.bold)),
                        style: TextButton.styleFrom(
                          foregroundColor: Colors.blue,
                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                          backgroundColor: Colors.blue.withOpacity(0.1),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(20),
                          ),
                        ),
                      ),
                  ],
                ),
              ),
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

                        // Always show "Add New Speaker" option at the top of the list for easy access
                        _buildAddNewSpeakerTile(),

                        // Keep unknown option
                        _buildUnknownSpeakerTile(),

                        // All registered speakers
                        ...filteredSpeakers.map((speaker) {
                          return _buildSpeakerTile(speaker);
                        }),

                        if (filteredSpeakers.isEmpty)
                          const Padding(
                            padding: EdgeInsets.all(32),
                            child: Center(
                              child: Text(
                                '검색 결과가 없습니다',
                                style: TextStyle(color: Colors.grey),
                              ),
                            ),
                          ),

                        // Create new speaker option (if search query is not empty)
                        if (_searchQuery.isNotEmpty &&
                            !filteredSpeakers.any((s) =>
                                s.displayName.toLowerCase() == _searchQuery))
                          _buildCreateSpeakerTile(_searchQuery),

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

  Future<void> _showAddSpeakerDialog() async {
    final controller = TextEditingController();
    
    final name = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('새 화자 추가'),
        content: TextField(
          controller: controller,
          decoration: const InputDecoration(
            labelText: '화자 이름',
            hintText: '이름을 입력하세요',
          ),
          autofocus: true,
          textCapitalization: TextCapitalization.words,
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('취소'),
          ),
          TextButton(
            onPressed: () {
              if (controller.text.trim().isNotEmpty) {
                Navigator.pop(context, controller.text.trim());
              }
            },
            child: const Text('추가'),
          ),
        ],
      ),
    );

    if (name != null && name.isNotEmpty) {
      // Clear search query to show the new speaker
      setState(() {
        _searchQuery = '';
      });
      await _createNewSpeaker(name);
    }
  }

  Widget _buildCreateSpeakerTile(String speakerName) {
    return Card(
      margin: const EdgeInsets.only(top: 8, bottom: 8),
      color: Colors.green.shade50,
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: Colors.green,
          child: const Icon(Icons.add, color: Colors.white),
        ),
        title: Text(
          '새 화자 생성: "$speakerName"',
          style: const TextStyle(
            fontWeight: FontWeight.bold,
            color: Colors.green,
          ),
        ),
        subtitle: const Text('새로운 화자로 등록하고 선택합니다'),
        onTap: _isUpdating ? null : () => _createNewSpeaker(speakerName),
      ),
    );
  }

  Future<void> _createNewSpeaker(String name) async {
    setState(() {
      _isUpdating = true;
    });

    try {
      final speakerProvider = context.read<SpeakerProvider>();
      final newSpeaker = await speakerProvider.createSpeaker(name);

      if (newSpeaker != null && mounted) {
        // Automatically select the newly created speaker
        await _selectSpeaker(newSpeaker.id, newSpeaker.displayName);
      } else if (mounted) {
        setState(() {
          _isUpdating = false;
        });
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('화자 생성에 실패했습니다'),
            backgroundColor: Colors.red,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _isUpdating = false;
        });
      }
    }
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

  Widget _buildAddNewSpeakerTile() {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      color: Colors.blue.shade50,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(color: Colors.blue.shade100),
      ),
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: Colors.white,
          child: const Icon(Icons.add, color: Colors.blue),
        ),
        title: const Text(
          '새 화자 추가하기',
          style: TextStyle(
            fontWeight: FontWeight.bold,
            color: Colors.blue,
          ),
        ),
        subtitle: const Text('목록에 없는 경우 직접 추가하세요'),
        onTap: _isUpdating ? null : _showAddSpeakerDialog,
      ),
    );
  }

  Widget _buildUnknownSpeakerTile() {
    final isCurrentSpeaker = widget.transcript.speakerId == null;

    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      color: isCurrentSpeaker ? Colors.grey.shade100 : null,
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: Colors.grey,
          child: const Icon(Icons.person_outline, color: Colors.white),
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

    // Check for other segments with the same current speaker
    final meetingProvider = context.read<MeetingProvider>();
    final currentSpeakerId = widget.transcript.speakerId;
    final currentSpeakerName = widget.transcript.speakerName;
    
    // Find matching transcripts (excluding current one)
    final sameSpeakerSegments = meetingProvider.transcripts.where((t) {
      if (t.id == widget.transcript.id) return false;
      
      if (currentSpeakerId != null) {
        return t.speakerId == currentSpeakerId;
      } else {
        // If ID is null, match by name (e.g. "Speaker 0")
        return t.speakerId == null && t.speakerName == currentSpeakerName;
      }
    }).toList();

    bool applyToAll = false;

    if (sameSpeakerSegments.isNotEmpty) {
      // Ask user if they want to apply to all
      final result = await showDialog<bool>(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('일괄 변경'),
          content: Text(
            '동일한 화자("${currentSpeakerName ?? 'Unknown'}")로 표시된 세그먼트가 ${sameSpeakerSegments.length}개 더 있습니다.\n\n모두 "${speakerName ?? 'Unknown'}"(으)로 변경하시겠습니까?'
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('이것만 변경'),
            ),
            ElevatedButton(
              onPressed: () => Navigator.pop(context, true),
              child: const Text('모두 변경'),
            ),
          ],
        ),
      );

      if (result == null) return; // Cancelled
      applyToAll = result;
    }

    setState(() {
      _isUpdating = true;
    });

    try {
      bool success;
      
      if (applyToAll) {
        // Merge logic
        final sourceIds = currentSpeakerId != null ? [currentSpeakerId] : <String>[];
        final sourceNames = currentSpeakerName != null ? [currentSpeakerName] : <String>[];
        
        // Ensure we at least have matched by name if ID is missing
        if (sourceIds.isEmpty && sourceNames.isEmpty) {
          // Should not happen if we found segments, but safe fallback
          if (currentSpeakerName != null) sourceNames.add(currentSpeakerName);
        }

        success = await meetingProvider.mergeSpeakers(
          meetingId: widget.transcript.meetingId,
          sourceSpeakerIds: sourceIds,
          sourceSpeakerNames: sourceNames,
          targetSpeakerId: speakerId,
          targetSpeakerName: speakerName,
        );
      } else {
        // Single update logic
        success = await meetingProvider.updateTranscriptSpeaker(
          widget.transcript.id,
          speakerId: speakerId,
          speakerName: speakerName,
        );
      }

      if (success && mounted) {
        widget.onSpeakerChanged?.call();
        Navigator.pop(context);

        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(speakerName != null
                ? '화자가 "$speakerName"(으)로 변경되었습니다${applyToAll ? ' (일괄 적용)' : ''}'
                : '화자가 "Unknown"으로 변경되었습니다'),
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
