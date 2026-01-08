/// Search result model for RAG hybrid search
class SearchResultModel {
  final String chunkId;
  final String meetingId;
  final int chunkIndex;
  final double startTime;
  final double endTime;
  final String? speakerId;
  final String text;
  final double keywordScore;
  final double semanticScore;
  final double combinedScore;

  SearchResultModel({
    required this.chunkId,
    required this.meetingId,
    required this.chunkIndex,
    required this.startTime,
    required this.endTime,
    this.speakerId,
    required this.text,
    required this.keywordScore,
    required this.semanticScore,
    required this.combinedScore,
  });

  factory SearchResultModel.fromJson(Map<String, dynamic> json) {
    return SearchResultModel(
      chunkId: json['chunk_id'] as String,
      meetingId: json['meeting_id'] as String,
      chunkIndex: json['chunk_index'] as int,
      startTime: (json['start_time'] as num).toDouble(),
      endTime: (json['end_time'] as num).toDouble(),
      speakerId: json['speaker_id'] as String?,
      text: json['text'] as String,
      keywordScore: (json['keyword_score'] as num?)?.toDouble() ?? 0.0,
      semanticScore: (json['semantic_score'] as num?)?.toDouble() ?? 0.0,
      combinedScore: (json['combined_score'] as num?)?.toDouble() ?? 0.0,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'chunk_id': chunkId,
      'meeting_id': meetingId,
      'chunk_index': chunkIndex,
      'start_time': startTime,
      'end_time': endTime,
      'speaker_id': speakerId,
      'text': text,
      'keyword_score': keywordScore,
      'semantic_score': semanticScore,
      'combined_score': combinedScore,
    };
  }

  /// Duration of the chunk in seconds
  double get duration => endTime - startTime;

  /// Format start time as MM:SS
  String get formattedStartTime {
    final minutes = (startTime / 60).floor();
    final seconds = (startTime % 60).floor();
    return '${minutes.toString().padLeft(2, '0')}:${seconds.toString().padLeft(2, '0')}';
  }

  /// Format time range as MM:SS - MM:SS
  String get formattedTimeRange {
    final startMin = (startTime / 60).floor();
    final startSec = (startTime % 60).floor();
    final endMin = (endTime / 60).floor();
    final endSec = (endTime % 60).floor();
    return '${startMin.toString().padLeft(2, '0')}:${startSec.toString().padLeft(2, '0')} - '
        '${endMin.toString().padLeft(2, '0')}:${endSec.toString().padLeft(2, '0')}';
  }

  /// Relevance percentage (0-100)
  int get relevancePercent => (combinedScore * 100).round();

  @override
  String toString() {
    return 'SearchResultModel(chunkId: $chunkId, text: ${text.length > 50 ? '${text.substring(0, 50)}...' : text})';
  }
}
