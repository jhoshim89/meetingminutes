import 'dart:async';
import 'package:flutter/foundation.dart';
import '../models/meeting_model.dart';
import '../models/search_result_model.dart';
import '../services/supabase_service.dart';

/// Search mode for the search provider
enum SearchMode {
  meetings,  // Search meeting titles
  chunks,    // Search transcript chunks (RAG)
}

class SearchProvider with ChangeNotifier {
  final SupabaseService _supabaseService = SupabaseService();

  String _query = '';
  SearchMode _searchMode = SearchMode.chunks;
  List<MeetingModel> _meetingResults = [];
  List<SearchResultModel> _chunkResults = [];
  bool _isSearching = false;
  String? _error;
  Timer? _debounceTimer;
  String? _selectedMeetingId;  // Filter by specific meeting

  // Getters
  String get query => _query;
  SearchMode get searchMode => _searchMode;
  List<MeetingModel> get meetingResults => _meetingResults;
  List<SearchResultModel> get chunkResults => _chunkResults;
  bool get isSearching => _isSearching;
  String? get error => _error;
  bool get hasQuery => _query.isNotEmpty;
  bool get hasResults => _searchMode == SearchMode.meetings
      ? _meetingResults.isNotEmpty
      : _chunkResults.isNotEmpty;
  String? get selectedMeetingId => _selectedMeetingId;

  /// Set search mode
  void setSearchMode(SearchMode mode) {
    if (_searchMode != mode) {
      _searchMode = mode;
      _meetingResults = [];
      _chunkResults = [];
      notifyListeners();

      // Re-run search with new mode
      if (_query.isNotEmpty) {
        _debounceTimer?.cancel();
        _debounceTimer = Timer(const Duration(milliseconds: 300), () {
          _performSearch(_query);
        });
      }
    }
  }

  /// Set meeting filter (null for all meetings)
  void setMeetingFilter(String? meetingId) {
    _selectedMeetingId = meetingId;
    notifyListeners();

    if (_query.isNotEmpty) {
      _debounceTimer?.cancel();
      _debounceTimer = Timer(const Duration(milliseconds: 300), () {
        _performSearch(_query);
      });
    }
  }

  /// Set search query with debounce
  void setQuery(String query) {
    _query = query;
    notifyListeners();

    // Debounce search
    _debounceTimer?.cancel();

    if (query.isEmpty) {
      _meetingResults = [];
      _chunkResults = [];
      notifyListeners();
      return;
    }

    _debounceTimer = Timer(const Duration(milliseconds: 500), () {
      _performSearch(query);
    });
  }

  /// Perform search based on current mode
  Future<void> _performSearch(String query) async {
    if (query.isEmpty) {
      _meetingResults = [];
      _chunkResults = [];
      notifyListeners();
      return;
    }

    _isSearching = true;
    _error = null;
    notifyListeners();

    try {
      if (_searchMode == SearchMode.meetings) {
        _meetingResults = await _supabaseService.searchMeetings(query);
        _chunkResults = [];
      } else {
        _chunkResults = await _supabaseService.hybridSearchChunks(
          query: query,
          meetingId: _selectedMeetingId,
          limit: 30,
        );
        _meetingResults = [];
      }
      _error = null;
    } catch (e) {
      _error = e.toString();
      debugPrint('Search error: $e');
    } finally {
      _isSearching = false;
      notifyListeners();
    }
  }

  /// Search meetings (legacy method for compatibility)
  Future<void> searchMeetings(String query) async {
    _searchMode = SearchMode.meetings;
    setQuery(query);
  }

  /// Search transcript chunks (RAG search)
  Future<void> searchChunks(String query, {String? meetingId}) async {
    _searchMode = SearchMode.chunks;
    _selectedMeetingId = meetingId;
    setQuery(query);
  }

  /// Clear all search state
  void clearSearch() {
    _query = '';
    _meetingResults = [];
    _chunkResults = [];
    _error = null;
    _selectedMeetingId = null;
    _debounceTimer?.cancel();
    notifyListeners();
  }

  /// Clear error only
  void clearError() {
    _error = null;
    notifyListeners();
  }

  /// Get unique meeting IDs from chunk results
  Set<String> get uniqueMeetingIds {
    return _chunkResults.map((r) => r.meetingId).toSet();
  }

  /// Group chunk results by meeting
  Map<String, List<SearchResultModel>> get resultsByMeeting {
    final Map<String, List<SearchResultModel>> grouped = {};
    for (final result in _chunkResults) {
      grouped.putIfAbsent(result.meetingId, () => []).add(result);
    }
    return grouped;
  }

  @override
  void dispose() {
    _debounceTimer?.cancel();
    super.dispose();
  }
}
