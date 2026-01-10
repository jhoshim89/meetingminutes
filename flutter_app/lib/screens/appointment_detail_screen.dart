import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';
import '../providers/appointment_provider.dart';
import '../providers/meeting_provider.dart';
import '../models/appointment_model.dart';
import 'appointment_form_screen.dart';
import 'meeting_detail_screen.dart';
import 'recorder_screen.dart';

/// Appointment Detail Screen showing full appointment information
class AppointmentDetailScreen extends StatefulWidget {
  final String appointmentId;

  const AppointmentDetailScreen({
    Key? key,
    required this.appointmentId,
  }) : super(key: key);

  @override
  State<AppointmentDetailScreen> createState() => _AppointmentDetailScreenState();
}

class _AppointmentDetailScreenState extends State<AppointmentDetailScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<AppointmentProvider>().fetchAndSelectAppointment(widget.appointmentId);
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Appointment Details'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () {
              context.read<AppointmentProvider>().fetchAndSelectAppointment(widget.appointmentId);
            },
          ),
          PopupMenuButton(
            itemBuilder: (context) => [
              const PopupMenuItem(
                value: 'edit',
                child: Row(
                  children: [
                    Icon(Icons.edit),
                    SizedBox(width: 8),
                    Text('Edit'),
                  ],
                ),
              ),
              const PopupMenuItem(
                value: 'delete',
                child: Row(
                  children: [
                    Icon(Icons.delete, color: Colors.red),
                    SizedBox(width: 8),
                    Text('Delete', style: TextStyle(color: Colors.red)),
                  ],
                ),
              ),
            ],
            onSelected: (value) {
              if (value == 'edit') {
                _navigateToEdit();
              } else if (value == 'delete') {
                _showDeleteDialog();
              }
            },
          ),
        ],
      ),
      body: Consumer<AppointmentProvider>(
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
                      provider.fetchAndSelectAppointment(widget.appointmentId);
                    },
                    child: const Text('Retry'),
                  ),
                ],
              ),
            );
          }

          final appointment = provider.selectedAppointment;
          if (appointment == null) {
            return const Center(child: Text('Appointment not found'));
          }

          return SingleChildScrollView(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _buildHeader(appointment),
                const SizedBox(height: 24),
                _buildDetailsSection(appointment),
                const SizedBox(height: 24),
                _buildActionsSection(appointment),
                if (appointment.meetingId != null) ...[
                  const SizedBox(height: 24),
                  _buildLinkedMeetingSection(appointment),
                ],
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _buildHeader(AppointmentModel appointment) {
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
                    appointment.title,
                    style: const TextStyle(
                      fontSize: 24,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
                _buildStatusBadge(appointment.status),
              ],
            ),
            if (appointment.description != null && appointment.description!.isNotEmpty) ...[
              const SizedBox(height: 12),
              Text(
                appointment.description!,
                style: TextStyle(
                  fontSize: 14,
                  color: Colors.grey[700],
                  height: 1.5,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildStatusBadge(String status) {
    Color color;
    IconData icon;
    String text;

    switch (status) {
      case 'pending':
        color = Colors.blue;
        icon = Icons.schedule;
        text = 'Pending';
        break;
      case 'recording':
        color = Colors.red;
        icon = Icons.fiber_manual_record;
        text = 'Recording';
        break;
      case 'completed':
        color = Colors.green;
        icon = Icons.check_circle;
        text = 'Completed';
        break;
      case 'cancelled':
        color = Colors.grey;
        icon = Icons.cancel;
        text = 'Cancelled';
        break;
      case 'missed':
        color = Colors.orange;
        icon = Icons.warning;
        text = 'Missed';
        break;
      default:
        color = Colors.grey;
        icon = Icons.help;
        text = 'Unknown';
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 16, color: color),
          const SizedBox(width: 4),
          Text(
            text,
            style: TextStyle(
              color: color,
              fontWeight: FontWeight.bold,
              fontSize: 12,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDetailsSection(AppointmentModel appointment) {
    final dateFormat = DateFormat('EEEE, MMMM d, yyyy');
    final timeFormat = DateFormat('h:mm a');

    return Card(
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Details',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
            const Divider(height: 24),
            _buildDetailRow(
              Icons.calendar_today,
              'Date',
              dateFormat.format(appointment.scheduledAt),
            ),
            const SizedBox(height: 12),
            _buildDetailRow(
              Icons.access_time,
              'Time',
              timeFormat.format(appointment.scheduledAt),
            ),
            const SizedBox(height: 12),
            _buildDetailRow(
              Icons.timer,
              'Duration',
              appointment.formattedDuration,
            ),
            const SizedBox(height: 12),
            _buildDetailRow(
              Icons.notifications,
              'Reminder',
              appointment.formattedReminder,
            ),
            const SizedBox(height: 12),
            _buildDetailRow(
              Icons.mic,
              'Auto Record',
              appointment.autoRecord ? 'Enabled' : 'Disabled',
              valueColor: appointment.autoRecord ? Colors.green : Colors.grey,
            ),
            if (appointment.tags.isNotEmpty) ...[
              const SizedBox(height: 12),
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(Icons.label, size: 20, color: Colors.grey[600]),
                  const SizedBox(width: 12),
                  const SizedBox(
                    width: 80,
                    child: Text(
                      'Tags:',
                      style: TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ),
                  Expanded(
                    child: Wrap(
                      spacing: 6,
                      runSpacing: 6,
                      children: appointment.tags.map((tag) {
                        return Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 10,
                            vertical: 4,
                          ),
                          decoration: BoxDecoration(
                            color: Colors.blue.withOpacity(0.1),
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(color: Colors.blue.withOpacity(0.3)),
                          ),
                          child: Text(
                            tag,
                            style: const TextStyle(
                              fontSize: 12,
                              color: Colors.blue,
                            ),
                          ),
                        );
                      }).toList(),
                    ),
                  ),
                ],
              ),
            ],
            if (appointment.notificationSent) ...[
              const SizedBox(height: 12),
              Row(
                children: [
                  Icon(Icons.notifications_active, size: 20, color: Colors.green[600]),
                  const SizedBox(width: 12),
                  Text(
                    'Reminder notification sent',
                    style: TextStyle(
                      fontSize: 14,
                      color: Colors.green[600],
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildDetailRow(
    IconData icon,
    String label,
    String value, {
    Color? valueColor,
  }) {
    return Row(
      children: [
        Icon(icon, size: 20, color: Colors.grey[600]),
        const SizedBox(width: 12),
        SizedBox(
          width: 80,
          child: Text(
            '$label:',
            style: const TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.w500,
            ),
          ),
        ),
        Expanded(
          child: Text(
            value,
            style: TextStyle(
              fontSize: 14,
              color: valueColor ?? Colors.grey[800],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildActionsSection(AppointmentModel appointment) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Start Recording Button (pending status only)
        if (appointment.isPending)
          ElevatedButton.icon(
            onPressed: () => _startRecording(appointment),
            icon: const Icon(Icons.mic),
            label: const Text('Start Recording Now'),
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.red,
              foregroundColor: Colors.white,
              padding: const EdgeInsets.symmetric(vertical: 16),
            ),
          ),

        // Edit Button
        if (appointment.isPending) ...[
          const SizedBox(height: 12),
          OutlinedButton.icon(
            onPressed: _navigateToEdit,
            icon: const Icon(Icons.edit),
            label: const Text('Edit Appointment'),
            style: OutlinedButton.styleFrom(
              padding: const EdgeInsets.symmetric(vertical: 16),
            ),
          ),
        ],

        // Cancel Button (pending status only)
        if (appointment.isPending) ...[
          const SizedBox(height: 12),
          OutlinedButton.icon(
            onPressed: () => _cancelAppointment(appointment),
            icon: const Icon(Icons.cancel),
            label: const Text('Cancel Appointment'),
            style: OutlinedButton.styleFrom(
              foregroundColor: Colors.orange,
              padding: const EdgeInsets.symmetric(vertical: 16),
            ),
          ),
        ],

        // Delete Button
        const SizedBox(height: 12),
        OutlinedButton.icon(
          onPressed: _showDeleteDialog,
          icon: const Icon(Icons.delete),
          label: const Text('Delete Appointment'),
          style: OutlinedButton.styleFrom(
            foregroundColor: Colors.red,
            padding: const EdgeInsets.symmetric(vertical: 16),
          ),
        ),
      ],
    );
  }

  Widget _buildLinkedMeetingSection(AppointmentModel appointment) {
    return Card(
      elevation: 2,
      child: InkWell(
        onTap: () => _navigateToMeeting(appointment.meetingId!),
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.green.withOpacity(0.1),
                  shape: BoxShape.circle,
                ),
                child: const Icon(Icons.description, color: Colors.green),
              ),
              const SizedBox(width: 16),
              const Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Linked Meeting',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    SizedBox(height: 4),
                    Text(
                      'View meeting transcript',
                      style: TextStyle(
                        fontSize: 13,
                        color: Colors.grey,
                      ),
                    ),
                  ],
                ),
              ),
              const Icon(Icons.arrow_forward_ios, size: 16),
            ],
          ),
        ),
      ),
    );
  }

  void _navigateToEdit() async {
    final result = await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => AppointmentFormScreen(
          appointmentId: widget.appointmentId,
        ),
      ),
    );

    if (result == true && mounted) {
      context.read<AppointmentProvider>().fetchAndSelectAppointment(widget.appointmentId);
    }
  }

  void _startRecording(AppointmentModel appointment) {
    // Mark as recording
    context.read<AppointmentProvider>().markAsRecording(appointment.id);

    // Navigate to recorder screen
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => const RecorderScreen(),
      ),
    );
  }

  void _cancelAppointment(AppointmentModel appointment) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Cancel Appointment?'),
        content: const Text(
          'Are you sure you want to cancel this appointment?',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('No'),
          ),
          TextButton(
            onPressed: () async {
              Navigator.pop(context);
              final success = await context
                  .read<AppointmentProvider>()
                  .cancelAppointment(appointment.id);

              if (success && mounted) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text('Appointment cancelled'),
                    backgroundColor: Colors.orange,
                  ),
                );
                context.read<AppointmentProvider>().fetchAndSelectAppointment(widget.appointmentId);
              }
            },
            style: TextButton.styleFrom(foregroundColor: Colors.orange),
            child: const Text('Yes, Cancel'),
          ),
        ],
      ),
    );
  }

  void _showDeleteDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Appointment?'),
        content: const Text(
          'Are you sure you want to delete this appointment? This action cannot be undone.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () async {
              Navigator.pop(context);
              final success = await context
                  .read<AppointmentProvider>()
                  .deleteAppointment(widget.appointmentId);

              if (success && mounted) {
                Navigator.pop(context);
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text('Appointment deleted'),
                    backgroundColor: Colors.green,
                  ),
                );
              }
            },
            style: TextButton.styleFrom(foregroundColor: Colors.red),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
  }

  void _navigateToMeeting(String meetingId) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => MeetingDetailScreen(meetingId: meetingId),
      ),
    );
  }
}
