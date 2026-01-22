import 'package:flutter/foundation.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import '../services/supabase_service.dart';

class AuthProvider with ChangeNotifier {
  final SupabaseService _supabaseService = SupabaseService();

  User? _user;
  bool _isLoading = false;
  String? _error;
  bool _needsLogin = true; // PIN 로그인 필요 여부

  // Getters
  User? get user => _user;
  bool get isAuthenticated => _user != null;
  bool get isLoading => _isLoading;
  String? get error => _error;
  String? get userId => _user?.id;
  bool get needsLogin => _needsLogin;
  bool get hasValidSession => _supabaseService.hasValidSession;

  AuthProvider() {
    _initialize();
  }

  void _initialize() {
    // Listen to auth state changes
    _supabaseService.client.auth.onAuthStateChange.listen((data) {
      final event = data.event;
      if (event == AuthChangeEvent.signedIn) {
        _user = data.session?.user;
        _needsLogin = false;
        notifyListeners();
      } else if (event == AuthChangeEvent.signedOut) {
        _user = null;
        _needsLogin = true;
        notifyListeners();
      }
    });

    // Check current session
    _user = _supabaseService.currentUser;
    _needsLogin = _user == null;
  }

  /// 기존 세션 복원 시도
  /// 성공하면 true, 세션이 없으면 false 반환
  Future<bool> tryRestoreSession() async {
    _isLoading = true;
    notifyListeners();

    try {
      final user = await _supabaseService.tryRestoreSession();
      if (user != null) {
        _user = user;
        _needsLogin = false;
        _error = null;
        return true;
      }
      _needsLogin = true;
      return false;
    } catch (e) {
      debugPrint('Session restore error: $e');
      _needsLogin = true;
      return false;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// PIN 코드로 로그인
  Future<bool> signInWithPin(String pin) async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      final user = await _supabaseService.signInWithPin(pin);
      if (user != null) {
        _user = user;
        _needsLogin = false;
        _error = null;
        return true;
      }
      _error = 'Login failed';
      return false;
    } catch (e) {
      _error = 'Invalid PIN';
      debugPrint('PIN sign in error: $e');
      return false;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// 로그인 필요 상태로 설정 (Sign Out 시 호출)
  void setNeedsLogin() {
    _needsLogin = true;
    notifyListeners();
  }

  Future<void> signInAnonymously() async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      await _supabaseService.signInAnonymously();
      _user = _supabaseService.currentUser;
      _needsLogin = false;
      _error = null;
    } catch (e) {
      _error = e.toString();
      debugPrint('Sign in error: $e');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> signOut() async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      await _supabaseService.signOut();
      _user = null;
      _needsLogin = true; // Sign Out 후 PIN 로그인 화면으로
      _error = null;
    } catch (e) {
      _error = e.toString();
      debugPrint('Sign out error: $e');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  void clearError() {
    _error = null;
    notifyListeners();
  }
}
