import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/upload_provider.dart';
import '../services/realtime_service.dart';

/// Widget that displays processing progress for a meeting
///
/// Shows different states:
/// - Uploading (with progress bar)
/// - Processing (with status messages)
/// - Completed (with success indicator)
/// - Failed (with error message)
class ProcessingProgressIndicator extends StatefulWidget {
  final String meetingId;
  final bool showDetails;

  const ProcessingProgressIndicator({
    Key? key,
    required this.meetingId,
    this.showDetails = true,
  }) : super(key: key);

  @override
  State<ProcessingProgressIndicator> createState() =>
      _ProcessingProgressIndicatorState();
}

class _ProcessingProgressIndicatorState
    extends State<ProcessingProgressIndicator> with SingleTickerProviderStateMixin {
  late AnimationController _animationController;
  ProcessingUpdate? _latestUpdate;

  @override
  void initState() {
    super.initState();
    _animationController = AnimationController(
      duration: const Duration(milliseconds: 1500),
      vsync: this,
    )..repeat();
  }

  @override
  void dispose() {
    _animationController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<UploadProvider>(
      builder: (context, uploadProvider, child) {
        return StreamBuilder<ProcessingUpdate>(
          stream: RealtimeService()
              .listenToMeeting(widget.meetingId),
          builder: (context, snapshot) {
            if (snapshot.hasData) {
              _latestUpdate = snapshot.data;
            }

            return _buildProgressWidget(uploadProvider, _latestUpdate);
          },
        );
      },
    );
  }

  Widget _buildProgressWidget(
    UploadProvider uploadProvider,
    ProcessingUpdate? update,
  ) {
    // Uploading state
    if (uploadProvider.isUploading) {
      return _buildUploadingWidget(uploadProvider);
    }

    // Processing state (from realtime)
    if (update != null) {
      if (update.isProcessing) {
        return _buildProcessingWidget(update);
      } else if (update.isCompleted) {
        return _buildCompletedWidget(update);
      } else if (update.isFailed) {
        return _buildFailedWidget(update);
      }
    }

    // Default: pending state
    return _buildPendingWidget();
  }

  Widget _buildUploadingWidget(UploadProvider provider) {
    final progress = provider.progress;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const CircularProgressIndicator(strokeWidth: 2),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Uploading...',
                        style: TextStyle(
                          fontWeight: FontWeight.bold,
                          fontSize: 16,
                        ),
                      ),
                      if (progress != null) ...[
                        const SizedBox(height: 4),
                        Text(
                          progress.toString(),
                          style: TextStyle(
                            color: Colors.grey[600],
                            fontSize: 14,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              ],
            ),
            if (progress != null && widget.showDetails) ...[
              const SizedBox(height: 12),
              LinearProgressIndicator(
                value: progress.percentage / 100,
                backgroundColor: Colors.grey[200],
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildProcessingWidget(ProcessingUpdate update) {
    return Card(
      color: Colors.blue[50],
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                RotationTransition(
                  turns: _animationController,
                  child: const Icon(
                    Icons.sync,
                    color: Colors.blue,
                    size: 24,
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Processing...',
                        style: TextStyle(
                          fontWeight: FontWeight.bold,
                          fontSize: 16,
                          color: Colors.blue,
                        ),
                      ),
                      if (update.message != null && widget.showDetails) ...[
                        const SizedBox(height: 4),
                        Text(
                          update.message!,
                          style: TextStyle(
                            color: Colors.grey[700],
                            fontSize: 14,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              ],
            ),
            if (update.data != null &&
                update.data!.containsKey('progress') &&
                widget.showDetails) ...[
              const SizedBox(height: 12),
              LinearProgressIndicator(
                value: (update.data!['progress'] as num).toDouble() / 100,
                backgroundColor: Colors.grey[200],
                color: Colors.blue,
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildCompletedWidget(ProcessingUpdate update) {
    return Card(
      color: Colors.green[50],
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Row(
          children: [
            const Icon(
              Icons.check_circle,
              color: Colors.green,
              size: 32,
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Processing Complete',
                    style: TextStyle(
                      fontWeight: FontWeight.bold,
                      fontSize: 16,
                      color: Colors.green,
                    ),
                  ),
                  if (update.message != null && widget.showDetails) ...[
                    const SizedBox(height: 4),
                    Text(
                      update.message!,
                      style: TextStyle(
                        color: Colors.grey[700],
                        fontSize: 14,
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildFailedWidget(ProcessingUpdate update) {
    return Card(
      color: Colors.red[50],
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(
                  Icons.error,
                  color: Colors.red,
                  size: 32,
                ),
                const SizedBox(width: 16),
                const Expanded(
                  child: Text(
                    'Processing Failed',
                    style: TextStyle(
                      fontWeight: FontWeight.bold,
                      fontSize: 16,
                      color: Colors.red,
                    ),
                  ),
                ),
              ],
            ),
            if (update.message != null && widget.showDetails) ...[
              const SizedBox(height: 8),
              Text(
                update.message!,
                style: TextStyle(
                  color: Colors.grey[700],
                  fontSize: 14,
                ),
              ),
            ],
            if (widget.showDetails) ...[
              const SizedBox(height: 12),
              ElevatedButton.icon(
                onPressed: () {
                  // Retry logic
                  // TODO: Implement retry
                },
                icon: const Icon(Icons.refresh),
                label: const Text('Retry'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.red,
                  foregroundColor: Colors.white,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildPendingWidget() {
    return Card(
      color: Colors.grey[100],
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Row(
          children: [
            Icon(
              Icons.pending,
              color: Colors.grey[600],
              size: 24,
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Text(
                'Waiting to process...',
                style: TextStyle(
                  color: Colors.grey[700],
                  fontSize: 14,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Compact version for list items
class CompactProcessingIndicator extends StatelessWidget {
  final String status;
  final String? message;

  const CompactProcessingIndicator({
    Key? key,
    required this.status,
    this.message,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    IconData icon;
    Color color;
    String displayText;

    switch (status) {
      case 'pending':
        icon = Icons.schedule;
        color = Colors.orange;
        displayText = 'Pending';
        break;
      case 'processing':
        icon = Icons.sync;
        color = Colors.blue;
        displayText = 'Processing';
        break;
      case 'completed':
        icon = Icons.check_circle;
        color = Colors.green;
        displayText = 'Completed';
        break;
      case 'failed':
        icon = Icons.error;
        color = Colors.red;
        displayText = 'Failed';
        break;
      default:
        icon = Icons.help;
        color = Colors.grey;
        displayText = 'Unknown';
    }

    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 16, color: color),
        const SizedBox(width: 4),
        Text(
          displayText,
          style: TextStyle(
            color: color,
            fontSize: 12,
            fontWeight: FontWeight.w500,
          ),
        ),
        if (message != null) ...[
          const SizedBox(width: 4),
          Flexible(
            child: Text(
              message!,
              style: TextStyle(
                color: Colors.grey[600],
                fontSize: 11,
              ),
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ],
      ],
    );
  }
}
