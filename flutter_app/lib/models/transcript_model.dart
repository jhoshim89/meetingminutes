class TranscriptModel {
  final String id;
  final String meetingId;
  final String? speakerId;
  final String? speakerName;
  final String text;
  final double startTime;
  final double endTime;
  final double? confidence;
  final DateTime createdAt;
  final Map<String, dynamic>? metadata;

  TranscriptModel({
    required this.id,
    required this.meetingId,
    this.speakerId,
    this.speakerName,
    required this.text,
    required this.startTime,
    required this.endTime,
    this.confidence,
    required this.createdAt,
    this.metadata,
  });

  factory TranscriptModel.fromJson(Map<String, dynamic> json) {
    return TranscriptModel(
      id: json['id'] as String,
      meetingId: json['meeting_id'] as String,
      speakerId: json['speaker_id'] as String?,
      speakerName: json['speaker_name'] as String? ??
          (json['speakers'] is Map ? json['speakers']['name'] as String? : null),
      text: json['text'] as String,
      startTime: (json['start_time'] as num).toDouble(),
      endTime: (json['end_time'] as num).toDouble(),
      confidence: json['confidence'] != null
          ? (json['confidence'] as num).toDouble()
          : null,
      createdAt: DateTime.parse(json['created_at'] as String),
      metadata: json['metadata'] as Map<String, dynamic>?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'meeting_id': meetingId,
      'speaker_id': speakerId,
      'speaker_name': speakerName,
      'text': text,
      'start_time': startTime,
      'end_time': endTime,
      'confidence': confidence,
      'created_at': createdAt.toIso8601String(),
      'metadata': metadata,
    };
  }

  TranscriptModel copyWith({
    String? id,
    String? meetingId,
    String? speakerId,
    String? speakerName,
    String? text,
    double? startTime,
    double? endTime,
    double? confidence,
    DateTime? createdAt,
    Map<String, dynamic>? metadata,
  }) {
    return TranscriptModel(
      id: id ?? this.id,
      meetingId: meetingId ?? this.meetingId,
      speakerId: speakerId ?? this.speakerId,
      speakerName: speakerName ?? this.speakerName,
      text: text ?? this.text,
      startTime: startTime ?? this.startTime,
      endTime: endTime ?? this.endTime,
      confidence: confidence ?? this.confidence,
      createdAt: createdAt ?? this.createdAt,
      metadata: metadata ?? this.metadata,
    );
  }

  String get formattedStartTime {
    final minutes = startTime ~/ 60;
    final seconds = (startTime % 60).toInt();
    return '${minutes.toString().padLeft(2, '0')}:${seconds.toString().padLeft(2, '0')}';
  }

  String get displaySpeaker {
    return speakerName ?? 'Unknown Speaker';
  }

  double get duration {
    return endTime - startTime;
  }
}
