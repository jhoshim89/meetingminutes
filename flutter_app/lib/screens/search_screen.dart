import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/search_provider.dart';
import '../models/search_result_model.dart';
import 'meeting_detail_screen.dart';

/// Search screen for RAG hybrid search
/// Allows searching through meeting transcripts with relevance scores
class SearchScreen extends StatefulWidget {
  const SearchScreen({super.key});

  @override
  State<SearchScreen> createState() => _SearchScreenState();
}

class _SearchScreenState extends State<SearchScreen> {
  final TextEditingController _searchController = TextEditingController();
  final FocusNode _searchFocusNode = FocusNode();

  @override
  void initState() {
    super.initState();
    // Auto-focus search field
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _searchFocusNode.requestFocus();
    });
  }

  @override
  void dispose() {
    _searchController.dispose();
    _searchFocusNode.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('검색'),
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(60),
          child: _buildSearchBar(),
        ),
      ),
      body: Consumer<SearchProvider>(
        builder: (context, searchProvider, child) {
          return Column(
            children: [
              _buildSearchModeToggle(searchProvider),
              Expanded(
                child: _buildSearchResults(searchProvider),
              ),
            ],
          );
        },
      ),
    );
  }

  Widget _buildSearchBar() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Consumer<SearchProvider>(
        builder: (context, searchProvider, child) {
          return TextField(
            controller: _searchController,
            focusNode: _searchFocusNode,
            decoration: InputDecoration(
              hintText: '회의 내용 검색...',
              prefixIcon: const Icon(Icons.search),
              suffixIcon: searchProvider.hasQuery
                  ? IconButton(
                      icon: const Icon(Icons.clear),
                      onPressed: () {
                        _searchController.clear();
                        searchProvider.clearSearch();
                      },
                    )
                  : null,
              filled: true,
              fillColor: Theme.of(context).colorScheme.surfaceContainerHighest,
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(12),
                borderSide: BorderSide.none,
              ),
            ),
            onChanged: (value) {
              searchProvider.setQuery(value);
            },
          );
        },
      ),
    );
  }

  Widget _buildSearchModeToggle(SearchProvider searchProvider) {
    return Padding(
      padding: const EdgeInsets.all(8),
      child: SegmentedButton<SearchMode>(
        segments: const [
          ButtonSegment(
            value: SearchMode.chunks,
            label: Text('내용 검색'),
            icon: Icon(Icons.text_snippet),
          ),
          ButtonSegment(
            value: SearchMode.meetings,
            label: Text('회의 검색'),
            icon: Icon(Icons.folder),
          ),
        ],
        selected: {searchProvider.searchMode},
        onSelectionChanged: (Set<SearchMode> selected) {
          searchProvider.setSearchMode(selected.first);
        },
      ),
    );
  }

  Widget _buildSearchResults(SearchProvider searchProvider) {
    if (searchProvider.isSearching) {
      return const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            CircularProgressIndicator(),
            SizedBox(height: 16),
            Text('검색 중...'),
          ],
        ),
      );
    }

    if (searchProvider.error != null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.error_outline,
              size: 64,
              color: Theme.of(context).colorScheme.error,
            ),
            const SizedBox(height: 16),
            Text(
              '검색 오류',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 8),
            Text(
              searchProvider.error!,
              textAlign: TextAlign.center,
              style: TextStyle(
                color: Theme.of(context).colorScheme.error,
              ),
            ),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: () {
                searchProvider.clearError();
                searchProvider.setQuery(_searchController.text);
              },
              child: const Text('다시 시도'),
            ),
          ],
        ),
      );
    }

    if (!searchProvider.hasQuery) {
      return _buildEmptyState();
    }

    if (!searchProvider.hasResults) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.search_off,
              size: 64,
              color: Theme.of(context).colorScheme.outline,
            ),
            const SizedBox(height: 16),
            Text(
              '검색 결과 없음',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 8),
            Text(
              '"${searchProvider.query}"에 대한 결과를 찾을 수 없습니다.',
              textAlign: TextAlign.center,
              style: TextStyle(
                color: Theme.of(context).colorScheme.outline,
              ),
            ),
          ],
        ),
      );
    }

    if (searchProvider.searchMode == SearchMode.chunks) {
      return _buildChunkResults(searchProvider.chunkResults);
    } else {
      return _buildMeetingResults(searchProvider.meetingResults);
    }
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.manage_search,
            size: 80,
            color: Theme.of(context).colorScheme.outline,
          ),
          const SizedBox(height: 24),
          Text(
            '회의 내용을 검색하세요',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 8),
          Text(
            '키워드를 입력하면 관련된 회의 내용을\n빠르게 찾을 수 있습니다.',
            textAlign: TextAlign.center,
            style: TextStyle(
              color: Theme.of(context).colorScheme.outline,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildChunkResults(List<SearchResultModel> results) {
    return ListView.builder(
      padding: const EdgeInsets.symmetric(horizontal: 8),
      itemCount: results.length,
      itemBuilder: (context, index) {
        final result = results[index];
        return _SearchResultTile(
          result: result,
          onTap: () => _navigateToMeeting(result),
        );
      },
    );
  }

  Widget _buildMeetingResults(List meetingResults) {
    return ListView.builder(
      padding: const EdgeInsets.symmetric(horizontal: 8),
      itemCount: meetingResults.length,
      itemBuilder: (context, index) {
        final meeting = meetingResults[index];
        return Card(
          margin: const EdgeInsets.symmetric(vertical: 4),
          child: ListTile(
            leading: const Icon(Icons.folder),
            title: Text(meeting.title),
            subtitle: Text(
              _formatDate(meeting.createdAt),
              style: TextStyle(
                color: Theme.of(context).colorScheme.outline,
              ),
            ),
            trailing: const Icon(Icons.chevron_right),
            onTap: () {
              Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (context) => MeetingDetailScreen(
                    meetingId: meeting.id,
                  ),
                ),
              );
            },
          ),
        );
      },
    );
  }

  String _formatDate(DateTime? date) {
    if (date == null) return '';
    return '${date.year}.${date.month.toString().padLeft(2, '0')}.${date.day.toString().padLeft(2, '0')}';
  }

  void _navigateToMeeting(SearchResultModel result) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => MeetingDetailScreen(
          meetingId: result.meetingId,
          initialSeekTime: result.startTime,
        ),
      ),
    );
  }
}

/// Individual search result tile
class _SearchResultTile extends StatelessWidget {
  final SearchResultModel result;
  final VoidCallback onTap;

  const _SearchResultTile({
    required this.result,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;

    return Card(
      margin: const EdgeInsets.symmetric(vertical: 4),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header with time and relevance
              Row(
                children: [
                  // Time badge
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 8,
                      vertical: 4,
                    ),
                    decoration: BoxDecoration(
                      color: colorScheme.primaryContainer,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          Icons.access_time,
                          size: 14,
                          color: colorScheme.onPrimaryContainer,
                        ),
                        const SizedBox(width: 4),
                        Text(
                          result.formattedTimeRange,
                          style: TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w500,
                            color: colorScheme.onPrimaryContainer,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const Spacer(),
                  // Relevance score
                  _buildRelevanceIndicator(context),
                ],
              ),
              const SizedBox(height: 8),
              // Text content
              Text(
                result.text,
                style: Theme.of(context).textTheme.bodyMedium,
                maxLines: 3,
                overflow: TextOverflow.ellipsis,
              ),
              const SizedBox(height: 8),
              // Footer
              Row(
                children: [
                  Icon(
                    Icons.play_circle_outline,
                    size: 16,
                    color: colorScheme.primary,
                  ),
                  const SizedBox(width: 4),
                  Text(
                    '탭하여 재생',
                    style: TextStyle(
                      fontSize: 12,
                      color: colorScheme.primary,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildRelevanceIndicator(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final percent = result.relevancePercent;

    Color getColor() {
      if (percent >= 70) return Colors.green;
      if (percent >= 40) return Colors.orange;
      return Colors.grey;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: getColor().withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: getColor().withOpacity(0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            Icons.analytics,
            size: 14,
            color: getColor(),
          ),
          const SizedBox(width: 4),
          Text(
            '$percent%',
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.bold,
              color: getColor(),
            ),
          ),
        ],
      ),
    );
  }
}
