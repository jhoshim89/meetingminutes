# Template Implementation - Quick Reference Guide

## What Was Built

Meeting template backend API for organizing meetings by context with automatic tagging.

## Quick Start

### 1. Apply Database Migration
```bash
# Go to Supabase Dashboard > SQL Editor
# Copy and execute: pc_worker/migrations/001_create_templates_table.sql
```

### 2. Run Tests
```bash
cd D:\Productions\meetingminutes\pc_worker
python -m pytest test_templates.py -v
```

### 3. Use Template API
```python
from supabase_client import get_supabase_client

supabase = get_supabase_client()

# Create template
template = await supabase.create_template(
    user_id="user-123",
    name="Team Meeting",
    tags=["team", "sync"]
)

# List templates
templates = await supabase.list_templates("user-123")

# Get template
template = await supabase.get_template_by_id("template-id", "user-123")

# Update template
await supabase.update_template("template-id", "user-123", name="Updated")

# Delete template
await supabase.delete_template("template-id", "user-123")
```

## File Overview

| File | Purpose | Lines |
|------|---------|-------|
| models.py (lines 191-215) | Template data model | 35 |
| supabase_client.py (lines 452-670) | Template API methods | 215 |
| main_worker.py (lines 176-179, 249-278) | Auto-tagging integration | 30 |
| test_templates.py | Test suite (20+ tests) | 450+ |
| migrations/001_create_templates_table.sql | Database schema | 75 |
| TEMPLATE_API.md | API documentation | 500+ |
| TEMPLATE_IMPLEMENTATION_GUIDE.md | Implementation guide | 400+ |

## API Methods

### list_templates(user_id)
Get all user templates
```python
templates: List[Template] = await supabase.list_templates(user_id)
```

### get_template_by_id(template_id, user_id)
Get specific template
```python
template: Optional[Template] = await supabase.get_template_by_id(template_id, user_id)
```

### create_template(user_id, name, description, tags)
Create new template
```python
template: Template = await supabase.create_template(
    user_id=user_id,
    name="Template Name",
    description="Optional description",
    tags=["tag1", "tag2"]
)
```

### update_template(template_id, user_id, name, description, tags)
Update template (partial updates supported)
```python
success: bool = await supabase.update_template(
    template_id=template_id,
    user_id=user_id,
    name="New Name",
    tags=["new", "tags"]
)
```

### delete_template(template_id, user_id)
Delete template
```python
success: bool = await supabase.delete_template(template_id, user_id)
```

## Key Features

- ✓ 5 CRUD API methods
- ✓ Row-level security (RLS) at database
- ✓ Automatic timestamp management
- ✓ Tag sanitization (whitespace trim, empty string filter)
- ✓ Retry logic (3 attempts, 1s delay)
- ✓ User isolation enforced
- ✓ Idempotent operations
- ✓ Async/await throughout
- ✓ Comprehensive error handling
- ✓ 20+ unit tests

## Database

### Table: templates
```
id          UUID PRIMARY KEY
user_id     UUID (FOREIGN KEY to auth.users)
name        VARCHAR 255 (NOT NULL, NOT EMPTY)
description TEXT (OPTIONAL)
tags        TEXT[] (DEFAULT '{}')
created_at  TIMESTAMP (DEFAULT NOW)
updated_at  TIMESTAMP (AUTO-UPDATE)
```

### RLS Policies
- Users can only access their own templates
- Service role (PC Worker) bypasses RLS

### Indexes
- idx_templates_user_id (fast user lookups)
- idx_templates_created_at (efficient ordering)
- idx_templates_tags (GIN for array operations)

## Error Handling

All methods use @retry_with_backoff:
```python
@retry_with_backoff(max_attempts=3, initial_delay=1.0)
async def operation():
    # Automatically retried 3 times with exponential backoff
```

Errors:
```python
try:
    template = await supabase.create_template(...)
except SupabaseQueryError as e:
    # Handle database errors
    logger.error(f"Failed: {e}")
```

Permission checks return False instead of exceptions:
```python
success = await supabase.update_template(...)
if not success:
    # Permission denied or not found
```

## Testing

### Run all tests
```bash
pytest test_templates.py -v
```

### Run specific test
```bash
pytest test_templates.py::TestTemplateAPI::test_create_template -v
```

### Test coverage
```bash
pytest test_templates.py --cov=supabase_client
```

## Auto-Tagging

Integration point in main_worker.py:

```python
# Called during meeting processing (Step 2)
await self._apply_template_tags(meeting_id, user_id)
```

Currently a placeholder for Phase 3.2 implementation.

## Next Steps (Phase 3.2)

1. Implement full auto-tagging logic
2. Add Flutter UI for template selection
3. Implement tag-based meeting filtering
4. Add smart tag suggestions

## Verification

Before deploying:
1. ✓ Run test suite: `pytest test_templates.py -v`
2. ✓ Apply migration to Supabase
3. ✓ Verify RLS policies in dashboard
4. ✓ Test with real credentials

## Documentation

For more details, see:
- **API Reference**: TEMPLATE_API.md
- **Implementation Guide**: TEMPLATE_IMPLEMENTATION_GUIDE.md
- **Verification**: TEMPLATE_VERIFICATION_CHECKLIST.md
- **Task Summary**: TASK_3_1_COMPLETION_SUMMARY.md
- **Changes Log**: CHANGES_SUMMARY.md

## Support

For issues or questions:
1. Check TROUBLESHOOTING section in TEMPLATE_API.md
2. Run test suite to verify installation
3. Review example code in documentation
4. Check error logs for detailed messages

## Version

- **Version**: 1.0
- **Status**: COMPLETED
- **Phase**: 3.1
- **Ready for**: Phase 3.2 (Flutter Integration)
