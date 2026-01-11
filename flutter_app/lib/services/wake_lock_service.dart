import 'package:flutter/foundation.dart' show kIsWeb, debugPrint;

// Conditional import for platform-specific implementation
import 'wake_lock_service_io.dart' if (dart.library.html) 'wake_lock_service_web.dart'
    as platform;

/// Service to manage screen wake lock during recording
/// Prevents screen from turning off while recording is active
class WakeLockService {
  static final WakeLockService _instance = WakeLockService._internal();
  factory WakeLockService() => _instance;
  WakeLockService._internal();

  bool _isEnabled = false;

  /// Check if Wake Lock API is supported on current platform
  Future<bool> isSupported() async {
    return await platform.isWakeLockSupported();
  }

  /// Enable wake lock - prevents screen from turning off
  /// Returns true if successfully enabled
  Future<bool> enable() async {
    if (_isEnabled) return true;

    final success = await platform.requestWakeLock();
    _isEnabled = success;

    if (kIsWeb && success) {
      debugPrint('WakeLockService: Screen will stay on during recording');
    }

    return success;
  }

  /// Disable wake lock - allows screen to turn off normally
  Future<void> disable() async {
    if (!_isEnabled) return;

    await platform.releaseWakeLock();
    _isEnabled = false;

    if (kIsWeb) {
      debugPrint('WakeLockService: Screen wake lock released');
    }
  }

  /// Check if wake lock is currently active
  bool get isActive => _isEnabled && platform.isWakeLockActive();
}
