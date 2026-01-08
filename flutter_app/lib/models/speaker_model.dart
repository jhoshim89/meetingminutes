class SpeakerModel {
  final String id;
  final String? userId;
  final String? name;
  final List<double>? embeddings;
  final int sampleCount;
  final DateTime createdAt;
  final DateTime? updatedAt;
  final bool isRegistered;
  final Map<String, dynamic>? metadata;

  SpeakerModel({
    required this.id,
    this.userId,
    this.name,
    this.embeddings,
    required this.sampleCount,
    required this.createdAt,
    this.updatedAt,
    required this.isRegistered,
    this.metadata,
  });

  factory SpeakerModel.fromJson(Map<String, dynamic> json) {
    return SpeakerModel(
      id: json['id'] as String,
      userId: json['user_id'] as String?,
      name: json['name'] as String?,
      embeddings: json['embeddings'] != null
          ? (json['embeddings'] as List).map((e) => (e as num).toDouble()).toList()
          : null,
      sampleCount: json['sample_count'] as int? ?? 0,
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: json['updated_at'] != null
          ? DateTime.parse(json['updated_at'] as String)
          : null,
      isRegistered: json['is_registered'] as bool? ?? false,
      metadata: json['metadata'] as Map<String, dynamic>?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'user_id': userId,
      'name': name,
      'embeddings': embeddings,
      'sample_count': sampleCount,
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt?.toIso8601String(),
      'is_registered': isRegistered,
      'metadata': metadata,
    };
  }

  SpeakerModel copyWith({
    String? id,
    String? userId,
    String? name,
    List<double>? embeddings,
    int? sampleCount,
    DateTime? createdAt,
    DateTime? updatedAt,
    bool? isRegistered,
    Map<String, dynamic>? metadata,
  }) {
    return SpeakerModel(
      id: id ?? this.id,
      userId: userId ?? this.userId,
      name: name ?? this.name,
      embeddings: embeddings ?? this.embeddings,
      sampleCount: sampleCount ?? this.sampleCount,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      isRegistered: isRegistered ?? this.isRegistered,
      metadata: metadata ?? this.metadata,
    );
  }

  String get displayName {
    return name ?? 'Unknown Speaker';
  }
}
