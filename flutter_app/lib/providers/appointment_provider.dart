import 'package:flutter/foundation.dart';
import '../models/appointment_model.dart';
import '../services/supabase_service.dart';

class AppointmentProvider with ChangeNotifier {
  final SupabaseService _supabaseService = SupabaseService();

  // State
  List<AppointmentModel> _appointments = [];
  List<AppointmentModel> _todayAppointments = [];
  AppointmentModel? _selectedAppointment;
  bool _isLoading = false;
  String? _error;

  // Getters
  List<AppointmentModel> get appointments => _appointments;
  List<AppointmentModel> get todayAppointments => _todayAppointments;
  AppointmentModel? get selectedAppointment => _selectedAppointment;
  bool get isLoading => _isLoading;
  String? get error => _error;
  bool get hasSelectedAppointment => _selectedAppointment != null;

  /// Get upcoming appointments (pending status, future dates only)
  List<AppointmentModel> get upcomingAppointments {
    final now = DateTime.now();
    return _appointments
        .where((a) => a.isPending && a.scheduledAt.isAfter(now))
        .toList()
      ..sort((a, b) => a.scheduledAt.compareTo(b.scheduledAt));
  }

  /// Get appointments that need reminders soon
  List<AppointmentModel> get appointmentsNeedingReminder {
    return _appointments.where((a) => a.shouldTriggerSoon).toList();
  }

  /// Get appointments that should start recording
  List<AppointmentModel> get appointmentsReadyToRecord {
    return _appointments.where((a) => a.shouldStartRecording).toList();
  }

  /// Get appointments that should be marked as missed
  List<AppointmentModel> get appointmentsShouldMarkMissed {
    return _appointments.where((a) => a.shouldMarkAsMissed).toList();
  }

  // ====================
  // FETCH OPERATIONS
  // ====================

  /// Fetch all appointments with optional filters
  Future<void> fetchAppointments({
    String? status,
    DateTime? fromDate,
    DateTime? toDate,
    int limit = 50,
    int offset = 0,
  }) async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      _appointments = await _supabaseService.getAppointments(
        status: status,
        fromDate: fromDate,
        toDate: toDate,
        limit: limit,
        offset: offset,
      );
      _error = null;
    } catch (e) {
      _error = e.toString();
      debugPrint('Fetch appointments error: $e');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Fetch today's appointments
  Future<void> fetchTodayAppointments() async {
    try {
      _todayAppointments = await _supabaseService.getTodayAppointments();
      notifyListeners();
    } catch (e) {
      _error = e.toString();
      debugPrint('Fetch today appointments error: $e');
      notifyListeners();
    }
  }

  /// Fetch upcoming appointments
  Future<void> fetchUpcomingAppointments({int limit = 10}) async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      _appointments = await _supabaseService.getUpcomingAppointments(
        limit: limit,
      );
      _error = null;
    } catch (e) {
      _error = e.toString();
      debugPrint('Fetch upcoming appointments error: $e');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Fetch single appointment by ID and set as selected
  Future<void> fetchAndSelectAppointment(String appointmentId) async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      _selectedAppointment = await _supabaseService.getAppointmentById(appointmentId);
      _error = null;
    } catch (e) {
      _error = e.toString();
      debugPrint('Fetch appointment error: $e');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  // ====================
  // CREATE & UPDATE OPERATIONS
  // ====================

  /// Create a new appointment
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
  }) async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      final appointment = await _supabaseService.createAppointment(
        title: title,
        description: description,
        scheduledAt: scheduledAt,
        reminderMinutes: reminderMinutes,
        durationMinutes: durationMinutes,
        templateId: templateId,
        tags: tags,
        autoRecord: autoRecord,
        fcmToken: fcmToken,
      );

      if (appointment != null) {
        // Insert in sorted order by scheduled time
        final insertIndex = _appointments.indexWhere(
          (a) => a.scheduledAt.isAfter(appointment.scheduledAt),
        );

        if (insertIndex == -1) {
          _appointments.add(appointment);
        } else {
          _appointments.insert(insertIndex, appointment);
        }

        // Update today's appointments if applicable
        if (appointment.isToday) {
          _todayAppointments.add(appointment);
          _todayAppointments.sort((a, b) => a.scheduledAt.compareTo(b.scheduledAt));
        }

        _error = null;
      }

      notifyListeners();
      return appointment;
    } catch (e) {
      _error = e.toString();
      debugPrint('Create appointment error: $e');
      notifyListeners();
      return null;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Update an existing appointment
  Future<bool> updateAppointment(
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
      final updatedAppointment = await _supabaseService.updateAppointment(
        appointmentId,
        title: title,
        description: description,
        scheduledAt: scheduledAt,
        reminderMinutes: reminderMinutes,
        durationMinutes: durationMinutes,
        templateId: templateId,
        tags: tags,
        status: status,
        autoRecord: autoRecord,
        fcmToken: fcmToken,
        notificationSent: notificationSent,
        meetingId: meetingId,
      );

      if (updatedAppointment != null) {
        // Update in main list
        final index = _appointments.indexWhere((a) => a.id == appointmentId);
        if (index != -1) {
          _appointments[index] = updatedAppointment;

          // Re-sort if scheduled time changed
          if (scheduledAt != null) {
            _appointments.sort((a, b) => a.scheduledAt.compareTo(b.scheduledAt));
          }
        }

        // Update in today's list
        final todayIndex = _todayAppointments.indexWhere((a) => a.id == appointmentId);
        if (todayIndex != -1) {
          if (updatedAppointment.isToday) {
            _todayAppointments[todayIndex] = updatedAppointment;
            _todayAppointments.sort((a, b) => a.scheduledAt.compareTo(b.scheduledAt));
          } else {
            // Removed from today
            _todayAppointments.removeAt(todayIndex);
          }
        } else if (updatedAppointment.isToday) {
          // Added to today
          _todayAppointments.add(updatedAppointment);
          _todayAppointments.sort((a, b) => a.scheduledAt.compareTo(b.scheduledAt));
        }

        // Update selected appointment
        if (_selectedAppointment?.id == appointmentId) {
          _selectedAppointment = updatedAppointment;
        }
      }

      notifyListeners();
      return true;
    } catch (e) {
      _error = e.toString();
      debugPrint('Update appointment error: $e');
      notifyListeners();
      return false;
    }
  }

  // ====================
  // DELETE OPERATIONS
  // ====================

  /// Delete an appointment
  Future<bool> deleteAppointment(String appointmentId) async {
    try {
      final success = await _supabaseService.deleteAppointment(appointmentId);

      if (success) {
        _appointments.removeWhere((a) => a.id == appointmentId);
        _todayAppointments.removeWhere((a) => a.id == appointmentId);

        if (_selectedAppointment?.id == appointmentId) {
          _selectedAppointment = null;
        }

        notifyListeners();
      }

      return success;
    } catch (e) {
      _error = e.toString();
      debugPrint('Delete appointment error: $e');
      notifyListeners();
      return false;
    }
  }

  // ====================
  // STATUS OPERATIONS
  // ====================

  /// Cancel an appointment
  Future<bool> cancelAppointment(String appointmentId) async {
    return await updateAppointment(
      appointmentId,
      status: 'cancelled',
    );
  }

  /// Mark appointment as completed (optionally link to meeting)
  Future<bool> markAsCompleted(String appointmentId, {String? meetingId}) async {
    return await updateAppointment(
      appointmentId,
      status: 'completed',
      meetingId: meetingId,
    );
  }

  /// Mark appointment as recording
  Future<bool> markAsRecording(String appointmentId) async {
    return await updateAppointment(
      appointmentId,
      status: 'recording',
    );
  }

  /// Mark appointment as missed
  Future<bool> markAsMissed(String appointmentId) async {
    return await updateAppointment(
      appointmentId,
      status: 'missed',
    );
  }

  /// Update notification sent flag
  Future<bool> markNotificationSent(String appointmentId) async {
    return await updateAppointment(
      appointmentId,
      notificationSent: true,
    );
  }

  /// Update FCM token for an appointment
  Future<bool> updateFcmToken(String appointmentId, String fcmToken) async {
    try {
      final success = await _supabaseService.updateAppointmentFcmToken(
        appointmentId,
        fcmToken,
      );

      if (success) {
        // Update local state
        final index = _appointments.indexWhere((a) => a.id == appointmentId);
        if (index != -1) {
          _appointments[index] = _appointments[index].copyWith(
            fcmToken: fcmToken,
          );
        }

        final todayIndex = _todayAppointments.indexWhere((a) => a.id == appointmentId);
        if (todayIndex != -1) {
          _todayAppointments[todayIndex] = _todayAppointments[todayIndex].copyWith(
            fcmToken: fcmToken,
          );
        }

        if (_selectedAppointment?.id == appointmentId) {
          _selectedAppointment = _selectedAppointment!.copyWith(
            fcmToken: fcmToken,
          );
        }

        notifyListeners();
      }

      return success;
    } catch (e) {
      _error = e.toString();
      debugPrint('Update FCM token error: $e');
      notifyListeners();
      return false;
    }
  }

  // ====================
  // BATCH OPERATIONS
  // ====================

  /// Process appointments that need status updates
  /// This should be called periodically (e.g., from a background service)
  Future<void> processAppointmentStatuses() async {
    try {
      // Mark missed appointments
      final missedAppointments = appointmentsShouldMarkMissed;
      for (final appointment in missedAppointments) {
        await markAsMissed(appointment.id);
      }
    } catch (e) {
      debugPrint('Process appointment statuses error: $e');
    }
  }

  // ====================
  // UTILITY METHODS
  // ====================

  /// Select an appointment
  void selectAppointment(AppointmentModel? appointment) {
    _selectedAppointment = appointment;
    notifyListeners();
  }

  /// Clear selection
  void clearSelection() {
    _selectedAppointment = null;
    notifyListeners();
  }

  /// Clear error message
  void clearError() {
    _error = null;
    notifyListeners();
  }

  /// Get appointments for a specific date
  List<AppointmentModel> getAppointmentsForDate(DateTime date) {
    final targetDate = DateTime(date.year, date.month, date.day);

    return _appointments.where((appointment) {
      final appointmentDate = DateTime(
        appointment.scheduledAt.year,
        appointment.scheduledAt.month,
        appointment.scheduledAt.day,
      );
      return appointmentDate == targetDate;
    }).toList()
      ..sort((a, b) => a.scheduledAt.compareTo(b.scheduledAt));
  }

  /// Alias for getAppointmentsForDate (for compatibility)
  List<AppointmentModel> getAppointmentsForDay(DateTime day) {
    return getAppointmentsForDate(day);
  }

  /// Load all appointments (alias for fetchAppointments)
  Future<void> loadAppointments() async {
    await fetchAppointments();
  }

  /// Get appointments by status
  List<AppointmentModel> getAppointmentsByStatus(String status) {
    return _appointments.where((a) => a.status == status).toList()
      ..sort((a, b) => a.scheduledAt.compareTo(b.scheduledAt));
  }

  /// Get appointments by template
  List<AppointmentModel> getAppointmentsByTemplate(String templateId) {
    return _appointments.where((a) => a.templateId == templateId).toList()
      ..sort((a, b) => a.scheduledAt.compareTo(b.scheduledAt));
  }

  /// Get appointments by tag
  List<AppointmentModel> getAppointmentsByTag(String tag) {
    return _appointments.where((a) => a.tags.contains(tag)).toList()
      ..sort((a, b) => a.scheduledAt.compareTo(b.scheduledAt));
  }

  /// Search appointments by title
  List<AppointmentModel> searchAppointments(String query) {
    if (query.isEmpty) return _appointments;

    final lowerQuery = query.toLowerCase();
    return _appointments.where((appointment) {
      final matchesTitle = appointment.title.toLowerCase().contains(lowerQuery);
      final matchesDescription = appointment.description?.toLowerCase().contains(lowerQuery) ?? false;
      final matchesTags = appointment.tags.any((tag) => tag.toLowerCase().contains(lowerQuery));

      return matchesTitle || matchesDescription || matchesTags;
    }).toList()
      ..sort((a, b) => a.scheduledAt.compareTo(b.scheduledAt));
  }

  /// Check if there are any conflicts with the given time slot
  bool hasTimeConflict({
    required DateTime scheduledAt,
    required int durationMinutes,
    String? excludeAppointmentId,
  }) {
    final endTime = scheduledAt.add(Duration(minutes: durationMinutes));

    return _appointments.any((appointment) {
      // Skip the appointment being edited
      if (excludeAppointmentId != null && appointment.id == excludeAppointmentId) {
        return false;
      }

      // Only check pending and recording appointments
      if (!appointment.isPending && !appointment.isRecording) {
        return false;
      }

      final appointmentEnd = appointment.scheduledAt.add(
        Duration(minutes: appointment.durationMinutes),
      );

      // Check for overlap
      return (scheduledAt.isBefore(appointmentEnd) &&
              endTime.isAfter(appointment.scheduledAt));
    });
  }

  /// Get statistics
  Map<String, int> getStatistics() {
    return {
      'total': _appointments.length,
      'pending': _appointments.where((a) => a.isPending).length,
      'recording': _appointments.where((a) => a.isRecording).length,
      'completed': _appointments.where((a) => a.isCompleted).length,
      'cancelled': _appointments.where((a) => a.isCancelled).length,
      'missed': _appointments.where((a) => a.isMissed).length,
      'upcoming': upcomingAppointments.length,
      'today': _todayAppointments.length,
    };
  }

  /// Reset provider state
  void reset() {
    _appointments = [];
    _todayAppointments = [];
    _selectedAppointment = null;
    _error = null;
    notifyListeners();
  }
}
