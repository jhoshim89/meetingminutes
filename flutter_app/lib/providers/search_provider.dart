import 'dart:async';
import 'package:flutter/foundation.dart';
import '../models/meeting_model.dart';
import '../services/supabase_service.dart';

class SearchProvider with ChangeNotifier {
  final SupabaseService _supabaseService = SupabaseService();

  String _query = '';
  List<MeetingModel> _searchResults = [];
  bool _isSearching = false;
  String? _error;
  Timer? _debounceTimer;

  // Getters
  String get query => _query;
  List<MeetingModel> get searchResults => _searchResults;
  bool get isSearching => _isSearching;
  String? get error => _error;
  bool get hasQuery => _query.isNotEmpty;
  bool get hasResults => _searchResults.isNotEmpty;

  void setQuery(String query) {
    _query = query;
    notifyListeners();

    // Debounce search
    _debounceTimer?.cancel();

    if (query.isEmpty) {
      _searchResults = [];
      notifyListeners();
      return;
    }

    _debounceTimer = Timer(const Duration(milliseconds: 500), () {
      searchMeetings(query);
    });
  }

  Future<void> searchMeetings(String query) async {
    if (query.isEmpty) {
      _searchResults = [];
      notifyListeners();
      return;
    }

    _isSearching = true;
    _error = null;
    notifyListeners();

    try {
      _searchResults = await _supabaseService.searchMeetings(query);
      _error = null;
    } catch (e) {
      _error = e.toString();
      debugPrint('Search error: $e');
    } finally {
      _isSearching = false;
      notifyListeners();
    }
  }

  void clearSearch() {
    _query = '';
    _searchResults = [];
    _error = null;
    _debounceTimer?.cancel();
    notifyListeners();
  }

  void clearError() {
    _error = null;
    notifyListeners();
  }

  @override
  void dispose() {
    _debounceTimer?.cancel();
    super.dispose();
  }
}
