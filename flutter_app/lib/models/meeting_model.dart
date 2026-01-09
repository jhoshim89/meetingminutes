class MeetingModel {
  final String id;
  final String? userId;
  final String title;
  final int durationSeconds;
  final DateTime createdAt;
  final DateTime? updatedAt;
  final String status; // 'recording', 'processing', 'completed', 'failed'
  final String? audioUrl;
  final String? transcriptUrl;
  final String? summary;
  final int? speakerCount;
  final Map<String, dynamic>? metadata;
  final String? templateId;
  final List<String> tags;

  MeetingModel({
    required this.id,
    this.userId,
    required this.title,
    required this.durationSeconds,
    required this.createdAt,
    this.updatedAt,
    required this.status,
    this.audioUrl,
    this.transcriptUrl,
    this.summary,
    this.speakerCount,
    this.metadata,
    this.templateId,
    this.tags = const [],
  });

  factory MeetingModel.fromJson(Map<String, dynamic> json) {
    return MeetingModel(
      id: json['id'] as String,
      userId: json['user_id'] as String?,
      title: json['title'] as String? ?? 'Untitled Meeting',
      durationSeconds: json['duration_seconds'] as int? ?? 0,
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: json['updated_at'] != null
          ? DateTime.parse(json['updated_at'] as String)
          : null,
      status: json['status'] as String? ?? 'recording',
      audioUrl: json['audio_url'] as String?,
      transcriptUrl: json['transcript_url'] as String?,
      summary: json['summary'] as String?,
      speakerCount: json['speaker_count'] as int?,
      metadata: json['metadata'] as Map<String, dynamic>?,
      templateId: json['template_id'] as String?,
      tags: (json['tags'] as List<dynamic>?)?.cast<String>() ?? [],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'user_id': userId,
      'title': title,
      'duration_seconds': durationSeconds,
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt?.toIso8601String(),
      'status': status,
      'audio_url': audioUrl,
      'transcript_url': transcriptUrl,
      'summary': summary,
      'speaker_count': speakerCount,
      'metadata': metadata,
      'template_id': templateId,
      'tags': tags,
    };
  }

  MeetingModel copyWith({
    String? id,
    String? userId,
    String? title,
    int? durationSeconds,
    DateTime? createdAt,
    DateTime? updatedAt,
    String? status,
    String? audioUrl,
    String? transcriptUrl,
    String? summary,
    int? speakerCount,
    Map<String, dynamic>? metadata,
    String? templateId,
    List<String>? tags,
  }) {
    return MeetingModel(
      id: id ?? this.id,
      userId: userId ?? this.userId,
      title: title ?? this.title,
      durationSeconds: durationSeconds ?? this.durationSeconds,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      status: status ?? this.status,
      audioUrl: audioUrl ?? this.audioUrl,
      transcriptUrl: transcriptUrl ?? this.transcriptUrl,
      summary: summary ?? this.summary,
      speakerCount: speakerCount ?? this.speakerCount,
      metadata: metadata ?? this.metadata,
      templateId: templateId ?? this.templateId,
      tags: tags ?? this.tags,
    );
  }

  String get formattedDuration {
    final hours = durationSeconds ~/ 3600;
    final minutes = (durationSeconds % 3600) ~/ 60;
    final seconds = durationSeconds % 60;

    if (hours > 0) {
      return '${hours}h ${minutes}m';
    } else if (minutes > 0) {
      return '${minutes}m ${seconds}s';
    } else {
      return '${seconds}s';
    }
  }

  String get statusDisplay {
    switch (status) {
      case 'recording':
        return 'Recording';
      case 'processing':
        return 'Processing';
      case 'completed':
        return 'Completed';
      case 'failed':
        return 'Failed';
      default:
        return 'Unknown';
    }
  }

  String get tagsDisplay => tags.isEmpty ? '' : tags.join(', ');
}
