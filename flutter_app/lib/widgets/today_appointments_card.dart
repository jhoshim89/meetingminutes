import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';
import '../providers/appointment_provider.dart';
import '../models/appointment_model.dart';
import '../screens/appointment_detail_screen.dart';
import '../screens/appointment_form_screen.dart';

/// Widget displaying today's appointments in a card
class TodayAppointmentsCard extends StatelessWidget {
  const TodayAppointmentsCard({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Consumer<AppointmentProvider>(
      builder: (context, provider, child) {
        return Card(
          margin: const EdgeInsets.all(16),
          elevation: 2,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Padding(
                padding: const EdgeInsets.all(16),
                child: Row(
                  children: [
                    const Icon(Icons.today, color: Colors.blue),
                    const SizedBox(width: 8),
                    const Text(
                      'Today\'s Appointments',
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const Spacer(),
                    IconButton(
                      icon: const Icon(Icons.add_circle_outline),
                      onPressed: () => _navigateToAddAppointment(context),
                      tooltip: 'Add Appointment',
                    ),
                  ],
                ),
              ),
              const Divider(height: 1),
              if (provider.isLoading)
                const Padding(
                  padding: EdgeInsets.all(24),
                  child: Center(child: CircularProgressIndicator()),
                )
              else if (provider.todayAppointments.isEmpty)
                _buildEmptyState(context)
              else
                _buildAppointmentsList(context, provider.todayAppointments),
            ],
          ),
        );
      },
    );
  }

  Widget _buildEmptyState(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(24),
      child: Center(
        child: Column(
          children: [
            Icon(
              Icons.event_available,
              size: 48,
              color: Colors.grey[400],
            ),
            const SizedBox(height: 12),
            Text(
              'No appointments scheduled for today',
              style: TextStyle(
                fontSize: 14,
                color: Colors.grey[600],
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 12),
            TextButton.icon(
              onPressed: () => _navigateToAddAppointment(context),
              icon: const Icon(Icons.add),
              label: const Text('Add Appointment'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildAppointmentsList(BuildContext context, List<AppointmentModel> appointments) {
    return ListView.separated(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      itemCount: appointments.length > 3 ? 3 : appointments.length,
      separatorBuilder: (context, index) => const Divider(height: 1, indent: 16),
      itemBuilder: (context, index) {
        final appointment = appointments[index];
        return _AppointmentListItem(
          appointment: appointment,
          onTap: () => _navigateToDetail(context, appointment.id),
        );
      },
    );
  }

  void _navigateToAddAppointment(BuildContext context) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => AppointmentFormScreen(
          initialDate: DateTime.now(),
        ),
      ),
    ).then((_) {
      // Refresh today's appointments
      context.read<AppointmentProvider>().fetchTodayAppointments();
    });
  }

  void _navigateToDetail(BuildContext context, String appointmentId) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => AppointmentDetailScreen(
          appointmentId: appointmentId,
        ),
      ),
    ).then((_) {
      // Refresh today's appointments
      context.read<AppointmentProvider>().fetchTodayAppointments();
    });
  }
}

/// Individual appointment list item
class _AppointmentListItem extends StatelessWidget {
  final AppointmentModel appointment;
  final VoidCallback onTap;

  const _AppointmentListItem({
    required this.appointment,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final timeFormat = DateFormat('h:mm a');
    final now = DateTime.now();
    final isUpcoming = appointment.scheduledAt.isAfter(now);
    final isPast = appointment.scheduledAt.isBefore(now) &&
                   appointment.scheduledAt.add(Duration(minutes: appointment.durationMinutes)).isBefore(now);

    return InkWell(
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        child: Row(
          children: [
            // Time indicator
            Container(
              width: 70,
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
              decoration: BoxDecoration(
                color: _getStatusColor(appointment).withOpacity(0.1),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(
                  color: _getStatusColor(appointment).withOpacity(0.3),
                ),
              ),
              child: Column(
                children: [
                  Text(
                    timeFormat.format(appointment.scheduledAt),
                    style: TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.bold,
                      color: _getStatusColor(appointment),
                    ),
                  ),
                  Text(
                    appointment.formattedDuration,
                    style: TextStyle(
                      fontSize: 11,
                      color: Colors.grey[600],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 12),

            // Appointment details
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    appointment.title,
                    style: const TextStyle(
                      fontSize: 15,
                      fontWeight: FontWeight.w600,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 4),
                  Row(
                    children: [
                      _buildStatusBadge(appointment.status),
                      if (appointment.autoRecord) ...[
                        const SizedBox(width: 8),
                        Icon(
                          Icons.mic,
                          size: 14,
                          color: Colors.grey[600],
                        ),
                      ],
                      if (appointment.notificationSent) ...[
                        const SizedBox(width: 8),
                        Icon(
                          Icons.notifications_active,
                          size: 14,
                          color: Colors.green[600],
                        ),
                      ],
                    ],
                  ),
                  if (appointment.description != null && appointment.description!.isNotEmpty) ...[
                    const SizedBox(height: 4),
                    Text(
                      appointment.description!,
                      style: TextStyle(
                        fontSize: 12,
                        color: Colors.grey[600],
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ],
              ),
            ),

            // Status indicator and arrow
            Column(
              children: [
                if (isPast && appointment.isPending)
                  Icon(Icons.warning, size: 20, color: Colors.orange[700])
                else if (isUpcoming && appointment.isPending)
                  Icon(Icons.schedule, size: 20, color: Colors.blue[700])
                else if (appointment.isCompleted)
                  Icon(Icons.check_circle, size: 20, color: Colors.green[700])
                else if (appointment.isRecording)
                  Icon(Icons.fiber_manual_record, size: 20, color: Colors.red[700]),
                const SizedBox(height: 4),
                const Icon(Icons.arrow_forward_ios, size: 14),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStatusBadge(String status) {
    String text;
    Color color;

    switch (status) {
      case 'pending':
        text = 'Pending';
        color = Colors.blue;
        break;
      case 'recording':
        text = 'Recording';
        color = Colors.red;
        break;
      case 'completed':
        text = 'Completed';
        color = Colors.green;
        break;
      case 'cancelled':
        text = 'Cancelled';
        color = Colors.grey;
        break;
      case 'missed':
        text = 'Missed';
        color = Colors.orange;
        break;
      default:
        text = 'Unknown';
        color = Colors.grey;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(
        text,
        style: TextStyle(
          fontSize: 11,
          fontWeight: FontWeight.w600,
          color: color,
        ),
      ),
    );
  }

  Color _getStatusColor(AppointmentModel appointment) {
    switch (appointment.status) {
      case 'recording':
        return Colors.red;
      case 'completed':
        return Colors.green;
      case 'cancelled':
        return Colors.grey;
      case 'missed':
        return Colors.orange;
      case 'pending':
      default:
        final now = DateTime.now();
        if (appointment.scheduledAt.isBefore(now)) {
          return Colors.orange;
        }
        return Colors.blue;
    }
  }
}
