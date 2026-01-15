import 'dart:io';
import 'package:supabase_flutter/supabase_flutter.dart';
import '../models/meeting_model.dart';
import '../models/meeting_summary_model.dart';
import '../models/speaker_model.dart';
import '../models/transcript_model.dart';
import '../models/search_result_model.dart';
import '../models/template_model.dart';
import '../models/appointment_model.dart';

class SupabaseService {
  static final SupabaseService _instance = SupabaseService._internal();
  factory SupabaseService() => _instance;
  SupabaseService._internal();

  SupabaseClient get client => Supabase.instance.client;

  // Auth helpers
  User? get currentUser => client.auth.currentUser;
  String? get userId => currentUser?.id;
  bool get isAuthenticated => currentUser != null;

  // ====================
  // MEETINGS
  // ====================

  Future<List<MeetingModel>> getMeetings({
    int limit = 50,
    int offset = 0,
    String? status,
    String? templateId,
  }) async {
    try {
      var query = client.from('meetings').select();

      if (status != null) {
        query = query.eq('status', status);
      }
      
      if (templateId != null) {
        query = query.eq('template_id', templateId);
      }

      final response = await query
          .order('created_at', ascending: false)
          .range(offset, offset + limit - 1);

      return (response as List)
          .map((json) => MeetingModel.fromJson(json))
          .toList();
    } catch (e) {
      throw Exception('Failed to fetch meetings: $e');
    }
  }

  Future<MeetingModel> getMeetingById(String meetingId) async {
    try {
      final response = await client
          .from('meetings')
          .select()
          .eq('id', meetingId)
          .single();

      return MeetingModel.fromJson(response);
    } catch (e) {
      throw Exception('Failed to fetch meeting: $e');
    }
  }

  Future<MeetingModel> createMeeting({
    required String title,
    String? audioUrl,
    Map<String, dynamic>? metadata,
    String? templateId,
    List<String>? tags,
  }) async {
    try {
      final response = await client.from('meetings').insert({
        'user_id': userId,
        'title': title,
        'duration_seconds': 0,
        'status': 'recording',
        'audio_url': audioUrl,
        'metadata': metadata,
        'template_id': templateId,
        'tags': tags ?? [],
      }).select().single();

      return MeetingModel.fromJson(response);
    } catch (e) {
      throw Exception('Failed to create meeting: $e');
    }
  }

  Future<MeetingModel> updateMeeting(String meetingId, {
    String? title,
    int? durationSeconds,
    String? status,
    String? audioUrl,
    String? transcriptUrl,
    String? summary,
    int? speakerCount,
    Map<String, dynamic>? metadata,
    String? templateId,
    List<String>? tags,
  }) async {
    try {
      final updates = <String, dynamic>{
        'updated_at': DateTime.now().toIso8601String(),
      };

      if (title != null) updates['title'] = title;
      if (durationSeconds != null) updates['duration_seconds'] = durationSeconds;
      if (status != null) updates['status'] = status;
      if (audioUrl != null) updates['audio_url'] = audioUrl;
      if (transcriptUrl != null) updates['transcript_url'] = transcriptUrl;
      if (summary != null) updates['summary'] = summary;
      if (speakerCount != null) updates['speaker_count'] = speakerCount;
      if (metadata != null) updates['metadata'] = metadata;
      if (templateId != null) updates['template_id'] = templateId;
      if (tags != null) updates['tags'] = tags;

      final response = await client
          .from('meetings')
          .update(updates)
          .eq('id', meetingId)
          .eq('user_id', userId!)
          .select()
          .single();

      return MeetingModel.fromJson(response);
    } catch (e) {
      throw Exception('Failed to update meeting: $e');
    }
  }

  Future<void> deleteMeeting(String meetingId) async {
    try {
      await client
          .from('meetings')
          .delete()
          .eq('id', meetingId)
          .eq('user_id', userId!);
    } catch (e) {
      throw Exception('Failed to delete meeting: $e');
    }
  }

  Future<List<MeetingModel>> searchMeetings(String query) async {
    try {
      final response = await client
          .from('meetings')
          .select()
          .eq('user_id', userId!)
          .ilike('title', '%$query%')
          .order('created_at', ascending: false)
          .limit(20);

      return (response as List)
          .map((json) => MeetingModel.fromJson(json))
          .toList();
    } catch (e) {
      throw Exception('Failed to search meetings: $e');
    }
  }

  Future<MeetingSummaryModel?> getMeetingSummary(String meetingId) async {
    try {
      final response = await client
          .from('meeting_summaries')
          .select()
          .eq('meeting_id', meetingId)
          .maybeSingle();

      if (response == null) return null;

      return MeetingSummaryModel.fromJson(response);
    } catch (e) {
      print('Error fetching summary: $e');
      return null;
    }
  }

  /// RAG Hybrid Search - combines keyword and semantic search
  /// Returns transcript chunks ranked by relevance
  Future<List<SearchResultModel>> hybridSearchChunks({
    required String query,
    String? meetingId,
    int limit = 20,
    double keywordWeight = 0.3,
    double semanticWeight = 0.7,
  }) async {
    try {
      // Note: This requires the query embedding to be generated server-side
      // For now, we use a simplified keyword search until embedding API is ready
      final response = await client.rpc(
        'hybrid_search_chunks_simple',
        params: {
          'p_query_text': query,
          'p_user_id': userId,
          'p_meeting_id': meetingId,
          'p_limit': limit,
        },
      );

      if (response == null) return [];

      return (response as List)
          .map((json) => SearchResultModel.fromJson(json))
          .toList();
    } catch (e) {
      // Fallback to simple text search if RPC not available
      return await _fallbackTextSearch(query, meetingId, limit);
    }
  }

  /// Fallback text search when hybrid search is not available
  Future<List<SearchResultModel>> _fallbackTextSearch(
    String query,
    String? meetingId,
    int limit,
  ) async {
    try {
      var queryBuilder = client
          .from('transcript_chunks')
          .select()
          .eq('user_id', userId!);

      if (meetingId != null) {
        queryBuilder = queryBuilder.eq('meeting_id', meetingId);
      }

      final response = await queryBuilder
          .textSearch('text', query, config: 'simple')
          .limit(limit);

      return (response as List).map((json) {
        return SearchResultModel(
          chunkId: json['id'] as String,
          meetingId: json['meeting_id'] as String,
          chunkIndex: json['chunk_index'] as int,
          startTime: (json['start_time'] as num).toDouble(),
          endTime: (json['end_time'] as num).toDouble(),
          speakerId: json['speaker_id'] as String?,
          text: json['text'] as String,
          keywordScore: 1.0,
          semanticScore: 0.0,
          combinedScore: 1.0,
        );
      }).toList();
    } catch (e) {
      throw Exception('Failed to search chunks: $e');
    }
  }

  /// Get chunks for a specific meeting (for context display)
  Future<List<SearchResultModel>> getMeetingChunks(
    String meetingId, {
    int limit = 100,
  }) async {
    try {
      final response = await client
          .from('transcript_chunks')
          .select()
          .eq('meeting_id', meetingId)
          .eq('user_id', userId!)
          .order('chunk_index', ascending: true)
          .limit(limit);

      return (response as List).map((json) {
        return SearchResultModel(
          chunkId: json['id'] as String,
          meetingId: json['meeting_id'] as String,
          chunkIndex: json['chunk_index'] as int,
          startTime: (json['start_time'] as num).toDouble(),
          endTime: (json['end_time'] as num).toDouble(),
          speakerId: json['speaker_id'] as String?,
          text: json['text'] as String,
          keywordScore: 0.0,
          semanticScore: 0.0,
          combinedScore: 0.0,
        );
      }).toList();
    } catch (e) {
      throw Exception('Failed to get meeting chunks: $e');
    }
  }

  // ====================
  // SPEAKERS
  // ====================

  Future<List<SpeakerModel>> getSpeakers({
    bool? isRegistered,
  }) async {
    try {
      var query = client.from('speakers').select().eq('user_id', userId!);

      if (isRegistered != null) {
        query = query.eq('is_registered', isRegistered);
      }

      final response = await query.order('created_at', ascending: false);

      return (response as List)
          .map((json) => SpeakerModel.fromJson(json))
          .toList();
    } catch (e) {
      throw Exception('Failed to fetch speakers: $e');
    }
  }

  Future<SpeakerModel> getSpeakerById(String speakerId) async {
    try {
      final response = await client
          .from('speakers')
          .select()
          .eq('id', speakerId)
          .eq('user_id', userId!)
          .single();

      return SpeakerModel.fromJson(response);
    } catch (e) {
      throw Exception('Failed to fetch speaker: $e');
    }
  }

  Future<SpeakerModel> updateSpeaker(
    String speakerId, {
    String? name,
    bool? isRegistered,
    Map<String, dynamic>? metadata,
  }) async {
    try {
      final updates = <String, dynamic>{
        'updated_at': DateTime.now().toIso8601String(),
      };

      if (name != null) updates['name'] = name;
      if (isRegistered != null) updates['is_registered'] = isRegistered;
      if (metadata != null) updates['metadata'] = metadata;

      final response = await client
          .from('speakers')
          .update(updates)
          .eq('id', speakerId)
          .eq('user_id', userId!)
          .select()
          .single();

      return SpeakerModel.fromJson(response);
    } catch (e) {
      throw Exception('Failed to update speaker: $e');
    }
  }

  Future<SpeakerModel> createSpeaker({
    required String name,
    bool isRegistered = true,
  }) async {
    try {
      final response = await client.from('speakers').insert({
        'user_id': userId,
        'name': name,
        'is_registered': isRegistered,
        'created_at': DateTime.now().toIso8601String(),
        'updated_at': DateTime.now().toIso8601String(),
      }).select().single();

      return SpeakerModel.fromJson(response);
    } catch (e) {
      throw Exception('Failed to create speaker: $e');
    }
  }

  // ====================
  // TRANSCRIPTS
  // ====================

  Future<List<TranscriptModel>> getTranscripts(String meetingId) async {
    try {
      final response = await client
          .from('transcripts')
          .select()
          .eq('meeting_id', meetingId)
          .order('start_time', ascending: true);

      return (response as List)
          .map((json) => TranscriptModel.fromJson(json))
          .toList();
    } catch (e) {
      throw Exception('Failed to fetch transcripts: $e');
    }
  }

  /// Update transcript speaker assignment
  /// Allows users to reassign a transcript line to a different speaker
  Future<TranscriptModel> updateTranscriptSpeaker(
    String transcriptId, {
    String? speakerId,
    String? speakerName,
  }) async {
    try {
      final updates = <String, dynamic>{};

      // Allow setting speakerId to null (unknown speaker)
      updates['speaker_id'] = speakerId;

      if (speakerName != null) {
        updates['speaker_name'] = speakerName;
      }

      final response = await client
          .from('transcripts')
          .update(updates)
          .eq('id', transcriptId)
          .select()
          .single();

      return TranscriptModel.fromJson(response);
    } catch (e) {
      throw Exception('Failed to update transcript speaker: $e');
    }
  }

  /// Merge multiple speakers into one target speaker
  /// Updates all transcript segments for the given meeting that match any of the source speaker IDs or names
  Future<bool> mergeTranscriptSpeakers({
    required String meetingId,
    required List<String> sourceSpeakerIds,
    required List<String> sourceSpeakerNames,
    required String? targetSpeakerId,
    required String? targetSpeakerName,
  }) async {
    try {
      final updates = <String, dynamic>{
        'speaker_id': targetSpeakerId,
        'speaker_name': targetSpeakerName,
      };

      // We need to construct a filter that matches EITHER speaker_id IN sourceSpeakerIds OR speaker_name IN sourceSpeakerNames
      // However, Supabase/PostgREST 'or' syntax can be tricky with complex conditions.
      // It's safer and clearer to do two updates if we have both IDs and Names to match.
      
      // 1. Update by IDs
      if (sourceSpeakerIds.isNotEmpty) {
        await client
            .from('transcripts')
            .update(updates)
            .eq('meeting_id', meetingId)
            .in_('speaker_id', sourceSpeakerIds);
      }

      // 2. Update by Names (for those without IDs or just matching by name string)
      // Note: This might overlap with step 1, but that's harmless (idempotent for the result)
      if (sourceSpeakerNames.isNotEmpty) {
        await client
            .from('transcripts')
            .update(updates)
            .eq('meeting_id', meetingId)
            .in_('speaker_name', sourceSpeakerNames);
      }

      return true;
    } catch (e) {
      print('Failed to merge transcript speakers: $e');
      throw Exception('Failed to merge transcript speakers: $e');
    }
  }

  // ====================
  // STORAGE
  // ====================

  Future<String> uploadAudio(String filePath, String meetingId) async {
    try {
      final file = File(filePath);
      if (!await file.exists()) {
        throw Exception('Audio file not found');
      }

      final fileName = '$meetingId-${DateTime.now().millisecondsSinceEpoch}.m4a';
      final storagePath = 'audio/$userId/$fileName';

      await client.storage.from('meetings').upload(
        storagePath,
        file,
        fileOptions: const FileOptions(
          contentType: 'audio/m4a',
        ),
      );

      final publicUrl = client.storage.from('meetings').getPublicUrl(storagePath);
      return publicUrl;
    } catch (e) {
      throw Exception('Failed to upload audio: $e');
    }
  }

  Future<void> deleteAudio(String audioUrl) async {
    try {
      // Extract path from URL
      final uri = Uri.parse(audioUrl);
      final pathSegments = uri.pathSegments;
      final storagePath = pathSegments.sublist(pathSegments.indexOf('meetings') + 1).join('/');

      await client.storage.from('meetings').remove([storagePath]);
    } catch (e) {
      throw Exception('Failed to delete audio: $e');
    }
  }

  /// Get audio sample URL for a speaker
  /// Returns a signed URL for the speaker's audio sample
  String getAudioSampleUrl(String speakerId) {
    try {
      // Storage path format: audio/{user_id}/{speaker_id}_sample.wav
      final storagePath = 'audio/$userId/${speakerId}_sample.wav';

      // Generate signed URL with 7 day expiry
      final signedUrl = client.storage.from('meetings').getPublicUrl(
        storagePath,
      );

      return signedUrl;
    } catch (e) {
      throw Exception('Failed to get audio sample URL: $e');
    }
  }

  /// Download audio sample file to temporary location
  /// Returns the file path
  Future<String> downloadAudioSample(String speakerId) async {
    try {
      final storagePath = 'audio/$userId/${speakerId}_sample.wav';
      final bytes = await client.storage.from('meetings').download(storagePath);

      // Save to temporary directory
      final tempDir = Directory.systemTemp;
      final tempFile = File('${tempDir.path}/speaker_${speakerId}_sample.wav');
      await tempFile.writeAsBytes(bytes);

      return tempFile.path;
    } catch (e) {
      throw Exception('Failed to download audio sample: $e');
    }
  }

  // ====================
  // TEMPLATES
  // ====================

  Future<List<TemplateModel>> getTemplates() async {
    try {
      final response = await client
          .from('templates')
          .select()
          .eq('user_id', userId!)
          .order('created_at', ascending: false);

      return (response as List)
          .map((json) => TemplateModel.fromJson(json))
          .toList();
    } catch (e) {
      throw Exception('Failed to fetch templates: $e');
    }
  }

  Future<TemplateModel> getTemplateById(String templateId) async {
    try {
      final response = await client
          .from('templates')
          .select()
          .eq('id', templateId)
          .eq('user_id', userId!)
          .single();

      return TemplateModel.fromJson(response);
    } catch (e) {
      throw Exception('Failed to fetch template: $e');
    }
  }

  Future<TemplateModel> createTemplate({
    required String name,
    String? description,
    List<String>? tags,
  }) async {
    try {
      final response = await client.from('templates').insert({
        'user_id': userId,
        'name': name,
        'description': description,
        'tags': tags ?? [],
      }).select().single();

      return TemplateModel.fromJson(response);
    } catch (e) {
      throw Exception('Failed to create template: $e');
    }
  }

  Future<TemplateModel> updateTemplate(
    String templateId, {
    String? name,
    String? description,
    List<String>? tags,
  }) async {
    try {
      final updates = <String, dynamic>{
        'updated_at': DateTime.now().toIso8601String(),
      };

      if (name != null) updates['name'] = name;
      if (description != null) updates['description'] = description;
      if (tags != null) updates['tags'] = tags;

      final response = await client
          .from('templates')
          .update(updates)
          .eq('id', templateId)
          .eq('user_id', userId!)
          .select()
          .single();

      return TemplateModel.fromJson(response);
    } catch (e) {
      throw Exception('Failed to update template: $e');
    }
  }

  Future<void> deleteTemplate(String templateId) async {
    try {
      await client
          .from('templates')
          .delete()
          .eq('id', templateId)
          .eq('user_id', userId!);
    } catch (e) {
      throw Exception('Failed to delete template: $e');
    }
  }

  // ====================
  // ARCHIVE (Local Save)
  // ====================

  /// Archive meeting audio (Delete from cloud, mark as archived)
  Future<void> archiveMeetingAudio({
    required String meetingId,
    required String audioPath,
  }) async {
    try {
      // 1. Delete from Storage
      // audioPath usually comes from the URL or stored path.
      // If it's a full URL, we might need to extract the path.
      // Assuming audioPath passed here is the relative path in the bucket (e.g. "user_id/meeting_id.m4a")

      // If checks are needed on path format:
      // final path = audioPath.replaceFirst(RegExp(r'.*/meetings/'), '');

      // However, usually we store the relative path or full URL.
      // Let's assume we need to handle the removal carefully.
      // If the caller passes the relative path:
      if (audioPath.isNotEmpty) {
          await client.storage.from('meetings').remove([audioPath]);
      }

      // 2. Update Metadata
      // First fetch current metadata to avoid overwriting other fields
      final meeting = await getMeetingById(meetingId);
      final currentMetadata = meeting.metadata ?? {};
      final updatedMetadata = Map<String, dynamic>.from(currentMetadata);
      
      updatedMetadata['archived'] = true;
      updatedMetadata['archived_at'] = DateTime.now().toIso8601String();

      await client
          .from('meetings')
          .update({
            'metadata': updatedMetadata,
            // Optionally clear audio_url if we want to be strict, 
            // but keeping it might be useful for history unless we want to force UI to see it's gone.
            // Let's clear it to ensure no component tries to play it.
            'audio_url': null, 
          })
          .eq('id', meetingId);

    } catch (e) {
      throw Exception('Failed to archive meeting audio: $e');
    }
  }

  // ====================
  // APPOINTMENTS
  // ====================

  /// Get appointments with optional filtering and pagination
  Future<List<AppointmentModel>> getAppointments({
    String? status,
    DateTime? fromDate,
    DateTime? toDate,
    int limit = 50,
    int offset = 0,
  }) async {
    try {
      var query = client
          .from('appointments')
          .select();

      if (status != null) {
        query = query.eq('status', status);
      }

      if (fromDate != null) {
        query = query.gte('scheduled_at', fromDate.toIso8601String());
      }

      if (toDate != null) {
        query = query.lte('scheduled_at', toDate.toIso8601String());
      }

      final response = await query
          .order('scheduled_at', ascending: true)
          .range(offset, offset + limit - 1);

      return (response as List)
          .map((json) => AppointmentModel.fromJson(json))
          .toList();
    } catch (e) {
      throw Exception('Failed to fetch appointments: $e');
    }
  }

  /// Get single appointment by ID
  Future<AppointmentModel?> getAppointmentById(String appointmentId) async {
    try {
      final response = await client
          .from('appointments')
          .select()
          .eq('id', appointmentId)
          .eq('user_id', userId!)
          .single();

      return AppointmentModel.fromJson(response);
    } catch (e) {
      throw Exception('Failed to fetch appointment: $e');
    }
  }

  /// Create a new appointment
  /// [status] defaults to 'pending', use 'completed' for recordings
  /// [meetingId] links to a completed meeting record
  Future<AppointmentModel?> createAppointment({
    required String title,
    String? description,
    required DateTime scheduledAt,
    int reminderMinutes = 5,
    int durationMinutes = 60,
    String? templateId,
    List<String>? tags,
    bool autoRecord = true,
    String? fcmToken,
    String status = 'pending',
    String? meetingId,
  }) async {
    try {
      final response = await client.from('appointments').insert({
        'user_id': userId,
        'title': title,
        'description': description,
        'scheduled_at': scheduledAt.toIso8601String(),
        'reminder_minutes': reminderMinutes,
        'duration_minutes': durationMinutes,
        'template_id': templateId,
        'tags': tags ?? [],
        'status': status,
        'auto_record': autoRecord,
        'fcm_token': fcmToken,
        'notification_sent': false,
        'meeting_id': meetingId,
      }).select().single();

      return AppointmentModel.fromJson(response);
    } catch (e) {
      throw Exception('Failed to create appointment: $e');
    }
  }

  /// Update an existing appointment
  Future<AppointmentModel?> updateAppointment(
    String appointmentId, {
    String? title,
    String? description,
    DateTime? scheduledAt,
    int? reminderMinutes,
    int? durationMinutes,
    String? templateId,
    List<String>? tags,
    String? status,
    bool? autoRecord,
    String? fcmToken,
    bool? notificationSent,
    String? meetingId,
  }) async {
    try {
      final updates = <String, dynamic>{
        'updated_at': DateTime.now().toIso8601String(),
      };

      if (title != null) updates['title'] = title;
      if (description != null) updates['description'] = description;
      if (scheduledAt != null) updates['scheduled_at'] = scheduledAt.toIso8601String();
      if (reminderMinutes != null) updates['reminder_minutes'] = reminderMinutes;
      if (durationMinutes != null) updates['duration_minutes'] = durationMinutes;
      if (templateId != null) updates['template_id'] = templateId;
      if (tags != null) updates['tags'] = tags;
      if (status != null) updates['status'] = status;
      if (autoRecord != null) updates['auto_record'] = autoRecord;
      if (fcmToken != null) updates['fcm_token'] = fcmToken;
      if (notificationSent != null) updates['notification_sent'] = notificationSent;
      if (meetingId != null) updates['meeting_id'] = meetingId;

      final response = await client
          .from('appointments')
          .update(updates)
          .eq('id', appointmentId)
          .eq('user_id', userId!)
          .select()
          .single();

      return AppointmentModel.fromJson(response);
    } catch (e) {
      throw Exception('Failed to update appointment: $e');
    }
  }

  /// Delete an appointment
  Future<bool> deleteAppointment(String appointmentId) async {
    try {
      await client
          .from('appointments')
          .delete()
          .eq('id', appointmentId)
          .eq('user_id', userId!);
      return true;
    } catch (e) {
      throw Exception('Failed to delete appointment: $e');
    }
  }

  /// Get today's appointments
  Future<List<AppointmentModel>> getTodayAppointments() async {
    try {
      final now = DateTime.now();
      final startOfDay = DateTime(now.year, now.month, now.day);
      final endOfDay = startOfDay.add(const Duration(days: 1));

      final response = await client
          .from('appointments')
          .select()
          .eq('user_id', userId!)
          .gte('scheduled_at', startOfDay.toIso8601String())
          .lt('scheduled_at', endOfDay.toIso8601String())
          .order('scheduled_at', ascending: true);

      return (response as List)
          .map((json) => AppointmentModel.fromJson(json))
          .toList();
    } catch (e) {
      throw Exception('Failed to fetch today\'s appointments: $e');
    }
  }

  /// Get upcoming appointments (future only, sorted by scheduled time)
  Future<List<AppointmentModel>> getUpcomingAppointments({
    int limit = 10,
  }) async {
    try {
      final now = DateTime.now();

      final response = await client
          .from('appointments')
          .select()
          .eq('user_id', userId!)
          .eq('status', 'pending')
          .gte('scheduled_at', now.toIso8601String())
          .order('scheduled_at', ascending: true)
          .limit(limit);

      return (response as List)
          .map((json) => AppointmentModel.fromJson(json))
          .toList();
    } catch (e) {
      throw Exception('Failed to fetch upcoming appointments: $e');
    }
  }

  /// Update FCM token for push notifications
  Future<bool> updateAppointmentFcmToken(
    String appointmentId,
    String fcmToken,
  ) async {
    try {
      await client
          .from('appointments')
          .update({
            'fcm_token': fcmToken,
            'updated_at': DateTime.now().toIso8601String(),
          })
          .eq('id', appointmentId)
          .eq('user_id', userId!);
      return true;
    } catch (e) {
      throw Exception('Failed to update FCM token: $e');
    }
  }

  // ====================
  // AUTH
  // ====================

  Future<void> signInAnonymously() async {
    try {
      await client.auth.signInAnonymously();
    } catch (e) {
      throw Exception('Failed to sign in: $e');
    }
  }

  Future<void> signOut() async {
    try {
      await client.auth.signOut();
    } catch (e) {
      throw Exception('Failed to sign out: $e');
    }
  }
}
