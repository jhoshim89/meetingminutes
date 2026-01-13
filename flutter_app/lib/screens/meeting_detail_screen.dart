import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';
import '../providers/meeting_provider.dart';
import '../providers/appointment_provider.dart';
import '../models/meeting_model.dart';
import '../models/meeting_summary_model.dart';
import '../models/transcript_model.dart';

class MeetingDetailScreen extends StatefulWidget {
  final String meetingId;
  final double? initialSeekTime;  // Time to seek to when opening from search

  const MeetingDetailScreen({
    Key? key,
    required this.meetingId,
    this.initialSeekTime,
  }) : super(key: key);

  @override
  State<MeetingDetailScreen> createState() => _MeetingDetailScreenState();
}

class _MeetingDetailScreenState extends State<MeetingDetailScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final provider = context.read<MeetingProvider>();
      provider.fetchMeetingById(widget.meetingId);
      provider.fetchTranscripts(widget.meetingId);
    });
  }

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 2,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Meeting Details'),
          bottom: const TabBar(
            tabs: [
              Tab(text: 'Summary'),
              Tab(text: 'Transcript'),
            ],
          ),
          actions: [
            IconButton(
              icon: const Icon(Icons.refresh),
              onPressed: () {
                final provider = context.read<MeetingProvider>();
                provider.fetchMeetingById(widget.meetingId);
                provider.fetchTranscripts(widget.meetingId);
              },
            ),
            PopupMenuButton(
              itemBuilder: (context) => [
                const PopupMenuItem(
                  value: 'delete',
                  child: Row(
                    children: [
                      Icon(Icons.delete, color: Colors.red),
                      SizedBox(width: 8),
                      Text('Delete Meeting', style: TextStyle(color: Colors.red)),
                    ],
                  ),
                ),
              ],
              onSelected: (value) {
                if (value == 'delete') {
                  _showDeleteDialog(context);
                }
              },
            ),
          ],
        ),
        body: Consumer<MeetingProvider>(
          builder: (context, provider, child) {
            if (provider.isLoading) {
              return const Center(child: CircularProgressIndicator());
            }

            if (provider.error != null) {
              return Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Icon(Icons.error_outline, size: 48, color: Colors.red),
                    const SizedBox(height: 16),
                    Text('Error: ${provider.error}'),
                    const SizedBox(height: 16),
                    ElevatedButton(
                      onPressed: () {
                        provider.fetchMeetingById(widget.meetingId);
                        provider.fetchTranscripts(widget.meetingId);
                      },
                      child: const Text('Retry'),
                    ),
                  ],
                ),
              );
            }

            final meeting = provider.currentMeeting;
            if (meeting == null) {
              return const Center(child: Text('Meeting not found'));
            }

            return TabBarView(
              children: [
                _buildSummaryTab(meeting, provider.currentSummary),
                _buildTranscriptTab(provider.transcripts),
              ],
            );
          },
        ),
      ),
    );
  }

  Widget _buildSummaryTab(MeetingModel meeting, MeetingSummaryModel? summaryData) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildMeetingHeader(meeting),
          const SizedBox(height: 24),
          if (summaryData != null)
            _buildDetailedSummary(summaryData)
          else if (meeting.summary != null && meeting.summary!.isNotEmpty)
            _buildSimpleSummary(meeting.summary!)
          else
             _buildEmptySummaryState(),
        ],
      ),
    );
  }

  Widget _buildTranscriptTab(List<TranscriptModel> transcripts) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: _buildTranscriptSection(transcripts),
    );
  }

  Widget _buildMeetingHeader(MeetingModel meeting) {
    final dateFormat = DateFormat('EEEE, MMMM d, yyyy - HH:mm');

    return Card(
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    meeting.title,
                    style: const TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
                _buildStatusBadge(meeting.status),
              ],
            ),
            const SizedBox(height: 16),
            _buildInfoRow(Icons.calendar_today, dateFormat.format(meeting.createdAt)),
            const SizedBox(height: 8),
            _buildInfoRow(Icons.timer, meeting.formattedDuration),
            if (meeting.speakerCount != null) ...[
              const SizedBox(height: 8),
              _buildInfoRow(Icons.people, '${meeting.speakerCount} speakers'),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildInfoRow(IconData icon, String text) {
    return Row(
      children: [
        Icon(icon, size: 16, color: Colors.grey[600]),
        const SizedBox(width: 8),
        Text(
          text,
          style: TextStyle(color: Colors.grey[700]),
        ),
      ],
    );
  }

  Widget _buildStatusBadge(String status) {
    Color color;
    String text;

    switch (status) {
      case 'completed':
        color = Colors.green;
        text = 'Completed';
        break;
      case 'processing':
        color = Colors.orange;
        text = 'Processing';
        break;
      case 'recording':
        color = Colors.red;
        text = 'Recording';
        break;
      case 'failed':
        color = Colors.red;
        text = 'Failed';
        break;
      default:
        color = Colors.grey;
        text = 'Unknown';
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color),
      ),
      child: Text(
        text,
        style: TextStyle(
          color: color,
          fontWeight: FontWeight.bold,
          fontSize: 12,
        ),
      ),
    );
  }

  Widget _buildDetailedSummary(MeetingSummaryModel summaryData) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildSectionTitle('Executive Summary'),
        const SizedBox(height: 8),
        Card(
          elevation: 2,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Text(
              summaryData.summary,
              style: TextStyle(
                color: Colors.grey[800],
                fontSize: 15,
                height: 1.6,
              ),
            ),
          ),
        ),
        const SizedBox(height: 24),
        if (summaryData.keyPoints.isNotEmpty) ...[
          _buildSectionTitle('Key Points'),
          const SizedBox(height: 8),
          ...summaryData.keyPoints.map((point) => _buildBulletPoint(point)).toList(),
          const SizedBox(height: 24),
        ],
        if (summaryData.actionItems.isNotEmpty) ...[
          _buildSectionTitle('Action Items'),
          const SizedBox(height: 8),
          ...summaryData.actionItems.map((item) => _buildActionItem(item)).toList(),
          const SizedBox(height: 24),
        ],
        if (summaryData.topics.isNotEmpty) ...[
          _buildSectionTitle('Topics'),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: summaryData.topics.map((topic) => Chip(
              label: Text(topic),
              backgroundColor: Colors.blue.withOpacity(0.1),
              labelStyle: const TextStyle(color: Colors.blue),
            )).toList(),
          ),
        ],
      ],
    );
  }

  Widget _buildSimpleSummary(String summary) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildSectionTitle('Summary'),
        const SizedBox(height: 12),
        Card(
          elevation: 2,
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Text(
              summary,
              style: TextStyle(
                color: Colors.grey[700],
                fontSize: 14,
                height: 1.5,
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildEmptySummaryState() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 32),
        child: Column(
          children: [
            Icon(Icons.summarize_outlined, size: 48, color: Colors.grey[300]),
            const SizedBox(height: 16),
            Text(
              'No summary available yet',
              style: TextStyle(color: Colors.grey[500], fontSize: 16),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSectionTitle(String title) {
    return Text(
      title,
      style: const TextStyle(
        fontSize: 18,
        fontWeight: FontWeight.bold,
        color: Colors.black87,
      ),
    );
  }

  Widget _buildBulletPoint(String text) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Padding(
            padding: EdgeInsets.only(top: 6),
            child: Icon(Icons.circle, size: 6, color: Colors.blue),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              text,
              style: TextStyle(
                fontSize: 14,
                color: Colors.grey[800],
                height: 1.5,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildActionItem(String text) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      elevation: 0,
      color: Colors.grey[50],
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(8),
        side: BorderSide(color: Colors.grey.withOpacity(0.2)),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Padding(
              padding: EdgeInsets.only(top: 2),
              child: Icon(Icons.check_box_outline_blank, color: Colors.blue, size: 20),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                text,
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w500,
                  color: Colors.grey[800],
                  height: 1.5,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSummarySection(String summary) {
    // Deprecated - kept for reference or removal
    return Container();
  }

  Widget _buildTranscriptSection(List<TranscriptModel> transcripts) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (transcripts.isEmpty)
          Card(
            elevation: 2,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Center(
                child: Column(
                  children: [
                    Icon(Icons.pending, size: 48, color: Colors.grey[400]),
                    const SizedBox(height: 8),
                    Text(
                      'Transcript is being processed',
                      style: TextStyle(color: Colors.grey[600]),
                    ),
                  ],
                ),
              ),
            ),
          )
        else
          Card(
            elevation: 2,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  for (int i = 0; i < transcripts.length; i++) ...[
                    _buildTranscriptLine(transcripts[i]),
                    if (i < transcripts.length - 1) const Divider(height: 24),
                  ],
                ],
              ),
            ),
          ),
      ],
    );
  }

  Widget _buildTranscriptLine(TranscriptModel transcript) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Container(
              width: 40,
              height: 40,
              decoration: BoxDecoration(
                color: Colors.blue.withOpacity(0.1),
                shape: BoxShape.circle,
              ),
              child: Center(
                child: Text(
                  transcript.speakerName?.substring(0, 1).toUpperCase() ?? '?',
                  style: const TextStyle(
                    fontWeight: FontWeight.bold,
                    color: Colors.blue,
                  ),
                ),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    transcript.displaySpeaker,
                    style: const TextStyle(
                      fontWeight: FontWeight.bold,
                      fontSize: 14,
                    ),
                  ),
                  Text(
                    transcript.formattedStartTime,
                    style: TextStyle(
                      fontSize: 12,
                      color: Colors.grey[600],
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        Text(
          transcript.text,
          style: TextStyle(
            color: Colors.grey[800],
            fontSize: 14,
            height: 1.5,
          ),
        ),
      ],
    );
  }

  void _showDeleteDialog(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Meeting?'),
        content: const Text(
          'This will permanently delete:\n'
          '• Audio recording file\n'
          '• Meeting record and transcripts\n'
          '• Calendar appointment (if linked)\n\n'
          'This action cannot be undone.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () async {
              Navigator.pop(context); // Close dialog first
              await _performDelete(context);
            },
            style: TextButton.styleFrom(foregroundColor: Colors.red),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
  }

  Future<void> _performDelete(BuildContext context) async {
    // Show loading indicator
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => const Center(
        child: Card(
          child: Padding(
            padding: EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                CircularProgressIndicator(),
                SizedBox(height: 16),
                Text('Deleting meeting...'),
              ],
            ),
          ),
        ),
      ),
    );

    try {
      final meetingProvider = context.read<MeetingProvider>();
      final appointmentProvider = context.read<AppointmentProvider>();

      final success = await meetingProvider.deleteMeetingComplete(
        widget.meetingId,
        appointmentProvider: appointmentProvider,
      );

      if (context.mounted) {
        Navigator.pop(context); // Close loading dialog

        if (success) {
          Navigator.pop(context); // Close detail screen
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Meeting deleted successfully'),
              backgroundColor: Colors.green,
            ),
          );
        } else {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('Failed to delete: ${meetingProvider.error ?? 'Unknown error'}'),
              backgroundColor: Colors.red,
              duration: const Duration(seconds: 4),
            ),
          );
        }
      }
    } catch (e) {
      if (context.mounted) {
        Navigator.pop(context); // Close loading dialog
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error deleting meeting: $e'),
            backgroundColor: Colors.red,
            duration: const Duration(seconds: 4),
          ),
        );
      }
    }
  }
}
