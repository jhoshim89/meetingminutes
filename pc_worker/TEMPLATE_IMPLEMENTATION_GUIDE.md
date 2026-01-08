# Template Implementation Guide

## Overview

This guide explains how to implement and integrate the Template feature into the Meeting Minutes MVP. The implementation is split into setup and integration phases.

## Phase 3.1: Database & Backend Setup (Completed)

### What Has Been Implemented

1. **Template Model** (in `models.py`)
   - Pydantic data validation
   - Tag sanitization (whitespace trim, empty string filtering)
   - Required fields: id, user_id, name
   - Optional fields: description, tags, created_at, updated_at

2. **Supabase Client Methods** (in `supabase_client.py`)
   - `list_templates(user_id)` - Get all user templates
   - `get_template_by_id(template_id, user_id)` - Get specific template
   - `create_template(user_id, name, description, tags)` - Create new template
   - `update_template(template_id, user_id, name, description, tags)` - Update template
   - `delete_template(template_id, user_id)` - Delete template
   - Retry logic with exponential backoff (3 attempts, 1s initial delay)

3. **Auto-Tagging Integration** (in `main_worker.py`)
   - `_apply_template_tags(meeting_id, user_id)` - Placeholder for tag application
   - Called during meeting processing (after status update to PROCESSING)
   - Idempotent: safe to retry

4. **Database Migration** (in `migrations/001_create_templates_table.sql`)
   - PostgreSQL table with RLS policies
   - Indexes for performance
   - Service role access for PC Worker

5. **Comprehensive Tests** (in `test_templates.py`)
   - Mock Supabase client for testing
   - 20+ test cases covering CRUD, permissions, validation
   - pytest compatible

### Setup Instructions

#### Step 1: Apply Database Migration

Navigate to Supabase dashboard and run the migration SQL:

```bash
# Option A: Using Supabase Dashboard
1. Go to SQL Editor
2. Create new query
3. Copy entire content of migrations/001_create_templates_table.sql
4. Execute

# Option B: Using Supabase CLI (if set up)
supabase db push
```

Expected output:
```
CREATE TABLE
CREATE INDEX
ALTER TABLE
CREATE POLICY [4 times]
GRANT
CREATE TRIGGER
COMMENT ON TABLE
COMMENT ON COLUMN [2 times]
```

#### Step 2: Verify Database Setup

Check that RLS policies are enabled:

```sql
-- Check RLS status
SELECT tablename, rowsecurity
FROM pg_tables
WHERE tablename = 'templates';

-- Expected output: rowsecurity = true
```

#### Step 3: Install Dependencies (if needed)

All required dependencies should already be in `requirements.txt`:

```bash
pip install -r requirements.txt
```

If updating locally:
```bash
pip install --upgrade supabase postgrest
```

---

## Phase 3.2: Auto-Tagging Implementation (Next Steps)

### Option A: Manual Template Selection

Users select a template when creating meetings (Flutter app):

```python
# In main_worker.py, modify _apply_template_tags method

async def _apply_template_tags(self, meeting_id: str, user_id: str) -> None:
    """
    Apply template tags to meeting (template_id must be stored in meetings table).

    This implementation assumes meetings table has:
    - template_id: UUID (foreign key to templates)
    - tags: TEXT[] (array of tags from template)
    """
    try:
        # Fetch meeting to get selected template_id
        meeting = await self.supabase.get_meeting_by_id(meeting_id)

        if not meeting or not hasattr(meeting, 'template_id') or not meeting.template_id:
            logger.debug(f"No template selected for meeting {meeting_id}")
            return

        # Get template details
        template = await self.supabase.get_template_by_id(
            meeting.template_id,
            user_id
        )

        if not template:
            logger.warning(f"Template {meeting.template_id} not found")
            return

        # Apply tags to meeting (if meetings table has tags column)
        # This would require a new method: update_meeting_tags
        # await self.supabase.update_meeting_tags(meeting_id, template.tags)

        logger.log_meeting_event(
            meeting_id,
            "template_tags_applied",
            template_name=template.name,
            tags_count=len(template.tags)
        )

    except Exception as e:
        logger.warning(f"Failed to apply template tags: {e}")
```

### Option B: Smart Auto-Selection (Future Enhancement)

AI-based tag suggestion based on meeting content:

```python
async def _apply_template_tags(self, meeting_id: str, user_id: str) -> None:
    """
    Smart auto-selection: suggest template based on meeting title/context
    """
    try:
        meeting = await self.supabase.get_meeting_by_id(meeting_id)
        templates = await self.supabase.list_templates(user_id)

        if not templates:
            return

        # Score templates based on meeting title matching
        best_template = None
        best_score = 0

        for template in templates:
            score = calculate_relevance_score(meeting.title, template)
            if score > best_score:
                best_score = score
                best_template = template

        if best_template and best_score > 0.5:
            # Apply tags from best_template
            logger.log_meeting_event(
                meeting_id,
                "template_auto_selected",
                template_name=best_template.name,
                confidence=f"{best_score:.2f}"
            )

    except Exception as e:
        logger.warning(f"Auto-selection failed: {e}")
```

---

## Phase 3.2: Frontend Integration (Flutter App)

### Update MeetingModel

Add template support to `flutter_app/lib/models/meeting_model.dart`:

```dart
class MeetingModel {
  // ... existing fields ...

  final String? templateId;  // NEW: Selected template ID
  final List<String>? tags;   // NEW: Tags from template

  MeetingModel({
    // ... existing parameters ...
    this.templateId,
    this.tags,
  });

  factory MeetingModel.fromJson(Map<String, dynamic> json) {
    return MeetingModel(
      // ... existing fields ...
      templateId: json['template_id'] as String?,
      tags: List<String>.from(json['tags'] as List? ?? []),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      // ... existing fields ...
      'template_id': templateId,
      'tags': tags,
    };
  }
}
```

### Create TemplateModel

New file: `flutter_app/lib/models/template_model.dart`

```dart
class TemplateModel {
  final String id;
  final String userId;
  final String name;
  final String? description;
  final List<String> tags;
  final DateTime createdAt;
  final DateTime? updatedAt;

  TemplateModel({
    required this.id,
    required this.userId,
    required this.name,
    this.description,
    required this.tags,
    required this.createdAt,
    this.updatedAt,
  });

  factory TemplateModel.fromJson(Map<String, dynamic> json) {
    return TemplateModel(
      id: json['id'] as String,
      userId: json['user_id'] as String,
      name: json['name'] as String,
      description: json['description'] as String?,
      tags: List<String>.from(json['tags'] as List? ?? []),
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: json['updated_at'] != null
          ? DateTime.parse(json['updated_at'] as String)
          : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'user_id': userId,
      'name': name,
      'description': description,
      'tags': tags,
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt?.toIso8601String(),
    };
  }
}
```

### Create TemplateProvider

New file: `flutter_app/lib/providers/template_provider.dart`

```dart
import 'package:flutter/foundation.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import '../models/template_model.dart';

class TemplateProvider extends ChangeNotifier {
  final _supabase = Supabase.instance.client;

  List<TemplateModel> templates = [];
  bool isLoading = false;
  String? error;

  // Load templates for current user
  Future<void> loadTemplates() async {
    isLoading = true;
    error = null;
    notifyListeners();

    try {
      final userId = _supabase.auth.currentUser?.id;
      if (userId == null) throw Exception('Not authenticated');

      final response = await _supabase
          .from('templates')
          .select()
          .eq('user_id', userId)
          .order('created_at', ascending: false);

      templates = (response as List)
          .map((e) => TemplateModel.fromJson(e))
          .toList();

      isLoading = false;
      notifyListeners();
    } catch (e) {
      error = e.toString();
      isLoading = false;
      notifyListeners();
    }
  }

  // Create new template
  Future<TemplateModel?> createTemplate({
    required String name,
    String? description,
    List<String>? tags,
  }) async {
    try {
      final userId = _supabase.auth.currentUser?.id;
      if (userId == null) throw Exception('Not authenticated');

      final response = await _supabase
          .from('templates')
          .insert({
            'user_id': userId,
            'name': name,
            'description': description,
            'tags': tags ?? [],
          })
          .select()
          .single();

      final template = TemplateModel.fromJson(response);
      templates.add(template);
      notifyListeners();
      return template;
    } catch (e) {
      error = e.toString();
      notifyListeners();
      return null;
    }
  }

  // Update template
  Future<bool> updateTemplate({
    required String templateId,
    String? name,
    String? description,
    List<String>? tags,
  }) async {
    try {
      await _supabase
          .from('templates')
          .update({
            if (name != null) 'name': name,
            if (description != null) 'description': description,
            if (tags != null) 'tags': tags,
          })
          .eq('id', templateId);

      // Update local list
      final index = templates.indexWhere((t) => t.id == templateId);
      if (index >= 0) {
        templates[index] = templates[index].copyWith(
          name: name,
          description: description,
          tags: tags,
        );
        notifyListeners();
      }
      return true;
    } catch (e) {
      error = e.toString();
      notifyListeners();
      return false;
    }
  }

  // Delete template
  Future<bool> deleteTemplate(String templateId) async {
    try {
      await _supabase
          .from('templates')
          .delete()
          .eq('id', templateId);

      templates.removeWhere((t) => t.id == templateId);
      notifyListeners();
      return true;
    } catch (e) {
      error = e.toString();
      notifyListeners();
      return false;
    }
  }
}
```

### Update MeetingRecorderScreen

In `flutter_app/lib/screens/meeting_recorder_screen.dart`, add template selection:

```dart
// Add to state
TemplateModel? selectedTemplate;

// In build method, add dropdown before record button
DropdownButton<TemplateModel>(
  hint: const Text('Select Template (Optional)'),
  value: selectedTemplate,
  items: templateProvider.templates
      .map((t) => DropdownMenuItem(
            value: t,
            child: Text(t.name),
          ))
      .toList(),
  onChanged: (template) {
    setState(() {
      selectedTemplate = template;
    });
  },
)

// When creating meeting, pass template_id
await meetingProvider.createMeeting(
  title: titleController.text,
  templateId: selectedTemplate?.id,
);
```

---

## Testing & Validation

### 1. Run Unit Tests

```bash
cd pc_worker
python -m pytest test_templates.py -v
```

Expected output:
```
test_templates.py::TestTemplateAPI::test_create_template PASSED
test_templates.py::TestTemplateAPI::test_list_templates PASSED
test_templates.py::TestTemplateAPI::test_update_template PASSED
test_templates.py::TestTemplateAPI::test_delete_template PASSED
... (20+ tests total)
```

### 2. Test Database Setup

```bash
# In Supabase SQL Editor
SELECT COUNT(*) FROM templates;
-- Should return 0 (empty table)

-- Test RLS by inserting as service role
INSERT INTO templates (user_id, name, tags)
VALUES ('user-123', 'Test Template', ARRAY['test']);

-- Verify
SELECT * FROM templates WHERE user_id = 'user-123';
-- Should return 1 row
```

### 3. Manual Integration Test

```python
import asyncio
from supabase_client import get_supabase_client

async def test_integration():
    supabase = get_supabase_client()

    # Create template
    template = await supabase.create_template(
        user_id="test-user-123",
        name="Test Template",
        tags=["test"]
    )
    assert template is not None
    print(f"✓ Created template: {template.id}")

    # List templates
    templates = await supabase.list_templates("test-user-123")
    assert len(templates) > 0
    print(f"✓ Listed {len(templates)} template(s)")

    # Update template
    success = await supabase.update_template(
        template.id, "test-user-123",
        name="Updated Template",
        tags=["updated"]
    )
    assert success
    print("✓ Updated template")

    # Delete template
    success = await supabase.delete_template(template.id, "test-user-123")
    assert success
    print("✓ Deleted template")

asyncio.run(test_integration())
```

---

## Data Model Updates Needed

### Meetings Table Enhancement

To fully enable auto-tagging, add these columns to `meetings` table:

```sql
ALTER TABLE public.meetings ADD COLUMN IF NOT EXISTS template_id UUID;
ALTER TABLE public.meetings ADD COLUMN IF NOT EXISTS tags TEXT[] DEFAULT '{}';

-- Add foreign key constraint
ALTER TABLE public.meetings
ADD CONSTRAINT fk_meetings_template
FOREIGN KEY (template_id) REFERENCES public.templates(id) ON DELETE SET NULL;

-- Add index
CREATE INDEX idx_meetings_template_id ON public.meetings(template_id);
```

### Implementation in supabase_client.py

Add method to update meeting tags:

```python
@retry_with_backoff(max_attempts=3, initial_delay=1.0)
async def apply_meeting_tags(
    self,
    meeting_id: str,
    tags: List[str]
) -> bool:
    """Apply tags to a meeting"""
    try:
        await asyncio.to_thread(
            lambda: self.client.table('meetings')
            .update({'tags': tags})
            .eq('id', meeting_id)
            .execute()
        )
        logger.info(f"Applied {len(tags)} tags to meeting {meeting_id}")
        return True
    except APIError as e:
        logger.error(f"Failed to apply tags: {e}")
        raise SupabaseQueryError(f"Failed to apply tags: {e}")
```

---

## Troubleshooting

### Issue: "Templates table does not exist"

**Solution**: Run the migration SQL in Supabase dashboard:
1. Go to SQL Editor
2. Run `migrations/001_create_templates_table.sql`

### Issue: "Permission denied" when accessing templates

**Solution**: Verify RLS policies are enabled:
```sql
-- In Supabase SQL Editor
SELECT * FROM pg_policies WHERE tablename = 'templates';
-- Should return 4 policies (SELECT, INSERT, UPDATE, DELETE)
```

### Issue: pytest not finding tests

**Solution**: Ensure pytest is installed:
```bash
pip install pytest pytest-asyncio
pytest test_templates.py -v
```

---

## Next Steps

1. **Immediate (Phase 3.2)**: Complete auto-tagging implementation
2. **Short-term (Phase 3.3)**: Implement template selection in Flutter UI
3. **Medium-term (Phase 4)**: Integrate with RAG search for template-based filtering
4. **Long-term (Phase 5)**: Template sharing and team collaboration

---

## References

- Template API Documentation: `TEMPLATE_API.md`
- Database Migration: `migrations/001_create_templates_table.sql`
- Test Suite: `test_templates.py`
- Main Worker Integration: `main_worker.py` (search for `_apply_template_tags`)
