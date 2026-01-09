import 'package:flutter/foundation.dart';
import '../models/template_model.dart';
import '../services/supabase_service.dart';

class TemplateProvider with ChangeNotifier {
  final SupabaseService _supabaseService = SupabaseService();

  List<TemplateModel> _templates = [];
  TemplateModel? _selectedTemplate;
  bool _isLoading = false;
  String? _error;

  // Getters
  List<TemplateModel> get templates => _templates;
  TemplateModel? get selectedTemplate => _selectedTemplate;
  bool get isLoading => _isLoading;
  String? get error => _error;
  bool get hasSelectedTemplate => _selectedTemplate != null;

  Future<void> fetchTemplates() async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      _templates = await _supabaseService.getTemplates();
      _error = null;
    } catch (e) {
      _error = e.toString();
      debugPrint('Fetch templates error: $e');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<TemplateModel?> createTemplate({
    required String name,
    String? description,
    List<String>? tags,
  }) async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      final template = await _supabaseService.createTemplate(
        name: name,
        description: description,
        tags: tags,
      );

      _templates.insert(0, template);
      _error = null;
      notifyListeners();
      return template;
    } catch (e) {
      _error = e.toString();
      debugPrint('Create template error: $e');
      notifyListeners();
      return null;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<bool> updateTemplate(
    String templateId, {
    String? name,
    String? description,
    List<String>? tags,
  }) async {
    try {
      final updatedTemplate = await _supabaseService.updateTemplate(
        templateId,
        name: name,
        description: description,
        tags: tags,
      );

      final index = _templates.indexWhere((t) => t.id == templateId);
      if (index != -1) {
        _templates[index] = updatedTemplate;
      }

      if (_selectedTemplate?.id == templateId) {
        _selectedTemplate = updatedTemplate;
      }

      notifyListeners();
      return true;
    } catch (e) {
      _error = e.toString();
      debugPrint('Update template error: $e');
      notifyListeners();
      return false;
    }
  }

  Future<bool> deleteTemplate(String templateId) async {
    try {
      await _supabaseService.deleteTemplate(templateId);
      _templates.removeWhere((t) => t.id == templateId);

      if (_selectedTemplate?.id == templateId) {
        _selectedTemplate = null;
      }

      notifyListeners();
      return true;
    } catch (e) {
      _error = e.toString();
      debugPrint('Delete template error: $e');
      notifyListeners();
      return false;
    }
  }

  void selectTemplate(TemplateModel? template) {
    _selectedTemplate = template;
    notifyListeners();
  }

  void clearSelection() {
    _selectedTemplate = null;
    notifyListeners();
  }

  void clearError() {
    _error = null;
    notifyListeners();
  }

  void reset() {
    _templates = [];
    _selectedTemplate = null;
    _error = null;
    notifyListeners();
  }
}
