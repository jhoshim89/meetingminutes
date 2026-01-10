import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';
import '../providers/appointment_provider.dart';
import '../providers/template_provider.dart';
import '../models/appointment_model.dart';
import '../utils/quick_input_parser.dart';

/// Appointment Form Screen for creating/editing appointments
class AppointmentFormScreen extends StatefulWidget {
  final String? appointmentId;
  final DateTime? initialDate;

  const AppointmentFormScreen({
    Key? key,
    this.appointmentId,
    this.initialDate,
  }) : super(key: key);

  @override
  State<AppointmentFormScreen> createState() => _AppointmentFormScreenState();
}

class _AppointmentFormScreenState extends State<AppointmentFormScreen> {
  final _formKey = GlobalKey<FormState>();
  final _titleController = TextEditingController();
  final _descriptionController = TextEditingController();
  final _tagController = TextEditingController();
  final _quickInputController = TextEditingController();
  QuickInputResult? _parsePreview;

  late DateTime _selectedDateTime;
  int _durationMinutes = 60;
  int _reminderMinutes = 15;
  String? _selectedTemplateId;
  List<String> _tags = [];
  bool _autoRecord = true;
  bool _isLoading = true;
  bool _isEditMode = false;
  AppointmentModel? _existingAppointment;

  final List<int> _durationOptions = [15, 30, 45, 60, 90, 120];
  final List<int> _reminderOptions = [5, 10, 15, 30, 60];

  @override
  void initState() {
    super.initState();
    _selectedDateTime = widget.initialDate ?? DateTime.now().add(const Duration(hours: 1));
    _isEditMode = widget.appointmentId != null;
    _initializeForm();
  }

  Future<void> _initializeForm() async {
    final templateProvider = context.read<TemplateProvider>();
    await templateProvider.fetchTemplates();

    if (_isEditMode && widget.appointmentId != null) {
      final appointmentProvider = context.read<AppointmentProvider>();
      await appointmentProvider.fetchAndSelectAppointment(widget.appointmentId!);
      _existingAppointment = appointmentProvider.selectedAppointment;

      if (_existingAppointment != null) {
        _titleController.text = _existingAppointment!.title;
        _descriptionController.text = _existingAppointment!.description ?? '';
        _selectedDateTime = _existingAppointment!.scheduledAt;
        _durationMinutes = _existingAppointment!.durationMinutes;
        _reminderMinutes = _existingAppointment!.reminderMinutes;
        _selectedTemplateId = _existingAppointment!.templateId;
        _tags = List.from(_existingAppointment!.tags);
        _autoRecord = _existingAppointment!.autoRecord;
      }
    }

    setState(() {
      _isLoading = false;
    });
  }

  @override
  void dispose() {
    _titleController.dispose();
    _descriptionController.dispose();
    _tagController.dispose();
    _quickInputController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return Scaffold(
        appBar: AppBar(
          title: Text(_isEditMode ? 'Edit Appointment' : 'New Appointment'),
        ),
        body: const Center(child: CircularProgressIndicator()),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: Text(_isEditMode ? 'Edit Appointment' : 'New Appointment'),
        actions: [
          if (_isEditMode)
            IconButton(
              icon: const Icon(Icons.delete, color: Colors.red),
              onPressed: _showDeleteDialog,
            ),
        ],
      ),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            // Quick Input Section (only for new appointments)
            if (!_isEditMode) ...[
              _buildQuickInputSection(),
              const SizedBox(height: 16),
            ],

            // Title Field
            TextFormField(
              controller: _titleController,
              decoration: const InputDecoration(
                labelText: 'Title *',
                hintText: 'Enter meeting title',
                prefixIcon: Icon(Icons.title),
              ),
              validator: (value) {
                if (value == null || value.trim().isEmpty) {
                  return 'Please enter a title';
                }
                return null;
              },
            ),
            const SizedBox(height: 16),

            // Description Field
            TextFormField(
              controller: _descriptionController,
              decoration: const InputDecoration(
                labelText: 'Description',
                hintText: 'Enter meeting description (optional)',
                prefixIcon: Icon(Icons.description),
              ),
              maxLines: 3,
            ),
            const SizedBox(height: 16),

            // Date & Time Picker
            Card(
              child: ListTile(
                leading: const Icon(Icons.calendar_today),
                title: const Text('Date & Time'),
                subtitle: Text(
                  DateFormat('EEEE, MMM d, yyyy - h:mm a').format(_selectedDateTime),
                  style: const TextStyle(fontWeight: FontWeight.w500),
                ),
                trailing: const Icon(Icons.edit),
                onTap: _pickDateTime,
              ),
            ),
            const SizedBox(height: 16),

            // Duration Selection
            DropdownButtonFormField<int>(
              value: _durationMinutes,
              decoration: const InputDecoration(
                labelText: 'Expected Duration',
                prefixIcon: Icon(Icons.timer),
              ),
              items: _durationOptions.map((mins) {
                return DropdownMenuItem(
                  value: mins,
                  child: Text(_formatDuration(mins)),
                );
              }).toList(),
              onChanged: (value) {
                setState(() {
                  _durationMinutes = value!;
                });
              },
            ),
            const SizedBox(height: 16),

            // Template Selection
            Consumer<TemplateProvider>(
              builder: (context, templateProvider, child) {
                return DropdownButtonFormField<String?>(
                  value: _selectedTemplateId,
                  decoration: const InputDecoration(
                    labelText: 'Template (Optional)',
                    prefixIcon: Icon(Icons.dashboard),
                  ),
                  items: [
                    const DropdownMenuItem<String?>(
                      value: null,
                      child: Text('No Template'),
                    ),
                    ...templateProvider.templates.map((template) {
                      return DropdownMenuItem<String?>(
                        value: template.id,
                        child: Text(template.name),
                      );
                    }),
                  ],
                  onChanged: (value) {
                    setState(() {
                      _selectedTemplateId = value;
                    });
                  },
                );
              },
            ),
            const SizedBox(height: 16),

            // Tags Section
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        const Icon(Icons.label, size: 20),
                        const SizedBox(width: 8),
                        const Text(
                          'Tags',
                          style: TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        ..._tags.map((tag) => Chip(
                              label: Text(tag),
                              deleteIcon: const Icon(Icons.close, size: 18),
                              onDeleted: () {
                                setState(() {
                                  _tags.remove(tag);
                                });
                              },
                            )),
                        ActionChip(
                          label: const Text('Add Tag'),
                          avatar: const Icon(Icons.add, size: 18),
                          onPressed: _addTag,
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),

            // Reminder Selection
            DropdownButtonFormField<int>(
              value: _reminderMinutes,
              decoration: const InputDecoration(
                labelText: 'Reminder',
                prefixIcon: Icon(Icons.notifications),
              ),
              items: _reminderOptions.map((mins) {
                return DropdownMenuItem(
                  value: mins,
                  child: Text(_formatReminder(mins)),
                );
              }).toList(),
              onChanged: (value) {
                setState(() {
                  _reminderMinutes = value!;
                });
              },
            ),
            const SizedBox(height: 16),

            // Auto Record Toggle
            Card(
              child: SwitchListTile(
                title: const Text('Auto Record'),
                subtitle: const Text(
                  'Automatically start recording at scheduled time',
                ),
                secondary: const Icon(Icons.mic),
                value: _autoRecord,
                onChanged: (value) {
                  setState(() {
                    _autoRecord = value;
                  });
                },
              ),
            ),
            const SizedBox(height: 24),

            // Save Button
            ElevatedButton.icon(
              onPressed: _saveAppointment,
              icon: Icon(_isEditMode ? Icons.save : Icons.add),
              label: Text(_isEditMode ? 'Save Changes' : 'Create Appointment'),
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 16),
              ),
            ),

            if (_isEditMode) ...[
              const SizedBox(height: 12),
              OutlinedButton(
                onPressed: () => Navigator.pop(context),
                child: const Text('Cancel'),
                style: OutlinedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 16),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Future<void> _pickDateTime() async {
    final date = await showDatePicker(
      context: context,
      initialDate: _selectedDateTime,
      firstDate: DateTime.now(),
      lastDate: DateTime.now().add(const Duration(days: 365)),
    );

    if (date != null && mounted) {
      final time = await showTimePicker(
        context: context,
        initialTime: TimeOfDay.fromDateTime(_selectedDateTime),
      );

      if (time != null && mounted) {
        setState(() {
          _selectedDateTime = DateTime(
            date.year,
            date.month,
            date.day,
            time.hour,
            time.minute,
          );
        });
      }
    }
  }

  void _addTag() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Add Tag'),
        content: TextField(
          controller: _tagController,
          decoration: const InputDecoration(
            labelText: 'Tag name',
            hintText: 'Enter tag',
          ),
          autofocus: true,
          onSubmitted: (value) {
            if (value.trim().isNotEmpty && !_tags.contains(value.trim())) {
              setState(() {
                _tags.add(value.trim());
              });
              _tagController.clear();
              Navigator.pop(context);
            }
          },
        ),
        actions: [
          TextButton(
            onPressed: () {
              _tagController.clear();
              Navigator.pop(context);
            },
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () {
              final tag = _tagController.text.trim();
              if (tag.isNotEmpty && !_tags.contains(tag)) {
                setState(() {
                  _tags.add(tag);
                });
                _tagController.clear();
                Navigator.pop(context);
              }
            },
            child: const Text('Add'),
          ),
        ],
      ),
    );
  }

  Future<void> _saveAppointment() async {
    if (!_formKey.currentState!.validate()) return;

    final appointmentProvider = context.read<AppointmentProvider>();

    try {
      if (_isEditMode && widget.appointmentId != null) {
        // Update existing appointment
        final success = await appointmentProvider.updateAppointment(
          widget.appointmentId!,
          title: _titleController.text.trim(),
          description: _descriptionController.text.trim().isEmpty
              ? null
              : _descriptionController.text.trim(),
          scheduledAt: _selectedDateTime,
          durationMinutes: _durationMinutes,
          reminderMinutes: _reminderMinutes,
          templateId: _selectedTemplateId,
          tags: _tags,
          autoRecord: _autoRecord,
        );

        if (success && mounted) {
          Navigator.pop(context, true);
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Appointment updated successfully'),
              backgroundColor: Colors.green,
            ),
          );
        }
      } else {
        // Create new appointment
        final appointment = await appointmentProvider.createAppointment(
          title: _titleController.text.trim(),
          description: _descriptionController.text.trim().isEmpty
              ? null
              : _descriptionController.text.trim(),
          scheduledAt: _selectedDateTime,
          durationMinutes: _durationMinutes,
          reminderMinutes: _reminderMinutes,
          templateId: _selectedTemplateId,
          tags: _tags,
          autoRecord: _autoRecord,
        );

        if (appointment != null && mounted) {
          Navigator.pop(context, true);
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Appointment created successfully'),
              backgroundColor: Colors.green,
            ),
          );
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error: ${e.toString()}'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
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
              final appointmentProvider = context.read<AppointmentProvider>();
              final success = await appointmentProvider.deleteAppointment(
                widget.appointmentId!,
              );

              if (success && mounted) {
                Navigator.pop(context, true);
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

  String _formatDuration(int minutes) {
    if (minutes < 60) {
      return '$minutes minutes';
    }
    final hours = minutes ~/ 60;
    final mins = minutes % 60;
    if (mins == 0) {
      return '$hours ${hours == 1 ? 'hour' : 'hours'}';
    }
    return '$hours ${hours == 1 ? 'hour' : 'hours'} $mins min';
  }

  String _formatReminder(int minutes) {
    if (minutes < 60) {
      return '$minutes minutes before';
    }
    final hours = minutes ~/ 60;
    return '$hours ${hours == 1 ? 'hour' : 'hours'} before';
  }

  // ─────────────────────────────────────────────────────────────────
  // Quick Input Section
  // ─────────────────────────────────────────────────────────────────

  Widget _buildQuickInputSection() {
    return Card(
      color: Theme.of(context).colorScheme.primaryContainer.withOpacity(0.3),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  Icons.flash_on,
                  color: Theme.of(context).colorScheme.primary,
                  size: 20,
                ),
                const SizedBox(width: 8),
                Text(
                  '빠른 입력',
                  style: TextStyle(
                    fontWeight: FontWeight.bold,
                    color: Theme.of(context).colorScheme.primary,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            TextField(
              controller: _quickInputController,
              decoration: InputDecoration(
                hintText: '예: 2/11 2시 집행부 회의',
                hintStyle: TextStyle(
                  color: Theme.of(context).hintColor.withOpacity(0.6),
                  fontSize: 14,
                ),
                isDense: true,
                contentPadding: const EdgeInsets.symmetric(
                  horizontal: 12,
                  vertical: 12,
                ),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8),
                ),
                suffixIcon: IconButton(
                  icon: const Icon(Icons.auto_fix_high),
                  tooltip: '파싱',
                  onPressed: _parseQuickInput,
                ),
              ),
              onChanged: (_) => _parseQuickInput(),
              onSubmitted: (_) {
                if (_parsePreview != null) {
                  _applyQuickInput();
                }
              },
            ),
            if (_parsePreview != null) ...[
              const SizedBox(height: 12),
              _buildParsePreview(),
            ],
          ],
        ),
      ),
    );
  }

  void _parseQuickInput() {
    final input = _quickInputController.text;
    if (input.isEmpty) {
      setState(() {
        _parsePreview = null;
      });
      return;
    }

    final result = QuickInputParser.parse(input);
    setState(() {
      _parsePreview = result;
    });
  }

  void _applyQuickInput() {
    if (_parsePreview == null) return;

    setState(() {
      _titleController.text = _parsePreview!.title;
      if (_parsePreview!.dateTime != null) {
        _selectedDateTime = _parsePreview!.dateTime!;
      }

      // 빠른 입력 필드 초기화
      _quickInputController.clear();
      _parsePreview = null;
    });

    // 제목 필드로 포커스 이동
    FocusScope.of(context).nextFocus();
  }

  Widget _buildParsePreview() {
    final preview = _parsePreview!;
    final hasAnyInfo = preview.hasDate || preview.hasTime;

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: hasAnyInfo
            ? Colors.green.withOpacity(0.1)
            : Colors.orange.withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: hasAnyInfo
              ? Colors.green.withOpacity(0.3)
              : Colors.orange.withOpacity(0.3),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                hasAnyInfo ? Icons.check_circle : Icons.info,
                size: 16,
                color: hasAnyInfo ? Colors.green : Colors.orange,
              ),
              const SizedBox(width: 6),
              Text(
                '인식 결과',
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  fontSize: 13,
                  color: hasAnyInfo ? Colors.green[700] : Colors.orange[700],
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          if (preview.dateTime != null) ...[
            _buildPreviewRow(
              Icons.event,
              '날짜/시간',
              DateFormat('M월 d일 (E) HH:mm', 'ko').format(preview.dateTime!),
            ),
          ],
          _buildPreviewRow(
            Icons.title,
            '제목',
            preview.title,
          ),
          const SizedBox(height: 10),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              onPressed: _applyQuickInput,
              icon: const Icon(Icons.check, size: 18),
              label: const Text('적용하기'),
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 8),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPreviewRow(IconData icon, String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 14, color: Colors.grey[600]),
          const SizedBox(width: 6),
          Text(
            '$label: ',
            style: TextStyle(
              fontSize: 13,
              color: Colors.grey[600],
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
