# Template API Documentation

## Overview

The Template API provides CRUD operations for managing meeting templates in the PC Worker backend. Templates allow users to organize meetings by context (e.g., team meetings, project reviews, one-on-ones) and automatically tag meetings with template-defined tags during processing.

## Architecture

### Components

1. **Template Model** (`models.py`): Pydantic data class for type-safe template representation
2. **SupabaseClient Methods** (`supabase_client.py`): Async CRUD operations with retry logic
3. **Auto-Tagging Integration** (`main_worker.py`): Template tags automatically applied during meeting processing
4. **Database Schema** (`migrations/001_create_templates_table.sql`): PostgreSQL table with RLS policies

### Security Model

- **Row-Level Security (RLS)**: Each user can only access their own templates
- **Service Role Bypass**: PC Worker uses service role key to bypass RLS for admin operations
- **Idempotent Operations**: All tagging operations are safe to retry

## API Methods

### 1. List Templates

Get all templates for a user.

```python
async def list_templates(self, user_id: str) -> List[Template]
```

#### Parameters
- `user_id` (str): User identifier

#### Returns
- `List[Template]`: Sorted by creation date (newest first)

#### Raises
- `SupabaseQueryError`: If query fails

#### Example
```python
supabase = get_supabase_client()
templates = await supabase.list_templates(user_id="user-123")

for template in templates:
    print(f"{template.name}: {', '.join(template.tags)}")
```

#### Guarantees
- Only returns templates owned by the user
- Results sorted by created_at DESC
- Returns empty list if user has no templates

---

### 2. Get Template by ID

Retrieve a specific template by ID.

```python
async def get_template_by_id(
    self,
    template_id: str,
    user_id: str
) -> Optional[Template]
```

#### Parameters
- `template_id` (str): Template identifier
- `user_id` (str): User identifier (for ownership validation)

#### Returns
- `Template`: If found and owned by user
- `None`: If not found or not owned by user

#### Raises
- `SupabaseQueryError`: If query fails

#### Example
```python
template = await supabase.get_template_by_id(
    template_id="template-456",
    user_id="user-123"
)

if template:
    print(f"Template: {template.name}")
else:
    print("Template not found")
```

#### Guarantees
- Returns None if template not owned by user (no error thrown)
- Safe for permission checking

---

### 3. Create Template

Create a new template for a user.

```python
async def create_template(
    self,
    user_id: str,
    name: str,
    description: Optional[str] = None,
    tags: Optional[List[str]] = None
) -> Optional[Template]
```

#### Parameters
- `user_id` (str): User identifier
- `name` (str, required): Template name (max 255 chars, non-empty)
- `description` (str, optional): Template description
- `tags` (List[str], optional): List of tags for this template
  - Empty strings filtered automatically
  - Whitespace trimmed automatically
  - Default: empty list

#### Returns
- `Template`: Created template with ID and timestamps
- `None`: If creation fails

#### Raises
- `SupabaseQueryError`: If database operation fails

#### Example
```python
template = await supabase.create_template(
    user_id="user-123",
    name="Team Meeting",
    description="Weekly team sync template",
    tags=["team", "sync", "weekly"]
)

if template:
    print(f"Created template: {template.id}")
```

#### Guarantees
- Auto-generated UUID for template ID
- Timestamps automatically set
- Tags sanitized (empty strings removed, whitespace trimmed)

---

### 4. Update Template

Update an existing template (partial updates supported).

```python
async def update_template(
    self,
    template_id: str,
    user_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    tags: Optional[List[str]] = None
) -> bool
```

#### Parameters
- `template_id` (str): Template identifier
- `user_id` (str): User identifier (for ownership validation)
- `name` (str, optional): New template name
- `description` (str, optional): New description
- `tags` (List[str], optional): New tags list

#### Returns
- `True`: If update successful
- `False`: If template not found or not owned by user

#### Raises
- `SupabaseQueryError`: If database operation fails

#### Example
```python
success = await supabase.update_template(
    template_id="template-456",
    user_id="user-123",
    name="Daily Standup",
    tags=["daily", "standup", "team"]
)

if success:
    print("Template updated")
else:
    print("Update failed")
```

#### Guarantees
- Only updates specified fields (partial updates supported)
- Updated_at timestamp automatically updated
- Idempotent: updating with same values is safe
- Returns False instead of raising error for permission denied

---

### 5. Delete Template

Delete a template.

```python
async def delete_template(
    self,
    template_id: str,
    user_id: str
) -> bool
```

#### Parameters
- `template_id` (str): Template identifier
- `user_id` (str): User identifier (for ownership validation)

#### Returns
- `True`: If deletion successful
- `False`: If template not found or not owned by user

#### Raises
- `SupabaseQueryError`: If database operation fails

#### Example
```python
success = await supabase.delete_template(
    template_id="template-456",
    user_id="user-123"
)

if success:
    print("Template deleted")
else:
    print("Deletion failed")
```

#### Guarantees
- Soft-delete NOT used: template is permanently removed
- Returns False for permission denied (no error)
- Idempotent: deleting already-deleted template returns False

---

## Auto-Tagging Integration

Templates are automatically applied during meeting processing through the `_apply_template_tags` method in `main_worker.py`.

### Integration Points

When a meeting enters processing state:

1. **Meeting Fetched**: Meeting record retrieved from database
2. **Template Lookup**: User's templates fetched (if implemented)
3. **Tags Applied**: Selected template's tags added to meeting record
4. **Idempotent**: Operation is safe to retry

### Implementation Example

```python
async def _apply_template_tags(self, meeting_id: str, user_id: str) -> None:
    """
    Apply template tags to a meeting during processing.

    Idempotent: safe to call multiple times.
    """
    try:
        # Fetch templates for user
        templates = await self.supabase.list_templates(user_id)

        # Select template based on meeting context
        # (could be based on meeting title, duration, etc.)
        selected_template = templates[0]  # or custom logic

        # Apply tags to meeting (implementation depends on schema)
        # await self.supabase.apply_tags(meeting_id, selected_template.tags)

        logger.log_meeting_event(meeting_id, "template_tags_applied")

    except Exception as e:
        # Tagging errors don't fail processing
        logger.warning(f"Template tagging failed: {e}")
```

### Current Status

The template auto-tagging mechanism is integrated into the processing pipeline but the actual tag application depends on:
- `meetings` table structure (must have `tags` column)
- Auto-selection strategy (based on meeting title, duration, or manual selection)

---

## Data Model

### Template

```python
class Template(BaseModel):
    id: str                           # UUID
    user_id: str                      # Owner user ID
    name: str                         # Template name (required, non-empty)
    description: Optional[str] = None # Template description
    tags: List[str]                   # Tags (auto-sanitized)
    created_at: Optional[datetime]    # Creation timestamp
    updated_at: Optional[datetime]    # Last update timestamp
```

### Validation Rules

- `name`: Non-empty string, max 255 characters
- `tags`: List of strings, empty strings filtered, whitespace trimmed
- `user_id`: Must match authenticated user (enforced by RLS)

---

## Database Schema

### Templates Table

```sql
CREATE TABLE public.templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    tags TEXT[] DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT template_name_not_empty CHECK (name != '')
);
```

### Indexes

- `idx_templates_user_id`: Fast lookup by user
- `idx_templates_created_at`: Sorting by creation date
- `idx_templates_tags`: GIN index for tag searches

### RLS Policies

1. **SELECT**: Users can read only their own templates
2. **INSERT**: Users can create templates for themselves
3. **UPDATE**: Users can modify their own templates
4. **DELETE**: Users can delete their own templates

---

## Error Handling

All API methods use retry logic with exponential backoff:

- **Max Attempts**: 3
- **Initial Delay**: 1.0 second
- **Backoff Strategy**: Exponential

### Error Types

```python
SupabaseQueryError: Raised for database operation failures
```

Example error handling:

```python
from exceptions import SupabaseQueryError

try:
    template = await supabase.create_template(
        user_id="user-123",
        name="New Template",
        tags=["test"]
    )
except SupabaseQueryError as e:
    logger.error(f"Failed to create template: {e}")
    # Implement retry or fallback logic
```

---

## Testing

Comprehensive test suite in `test_templates.py`:

### Test Coverage

- CRUD operations (Create, Read, Update, Delete)
- User isolation and permission checks
- Idempotency guarantees
- Tag sanitization
- Partial updates
- Edge cases (empty lists, None values, etc.)

### Running Tests

```bash
# Run all template tests
pytest test_templates.py -v

# Run specific test
pytest test_templates.py::TestTemplateAPI::test_create_template -v

# Run with coverage
pytest test_templates.py --cov=supabase_client
```

---

## Deprecations & Roadmap

### Current Limitations

- Auto-tagging strategy not fully implemented (placeholder in place)
- Requires `tags` column in meetings table
- No template-based meeting filtering yet

### Future Enhancements (Phase 4+)

- Smart tag suggestion based on meeting content
- Template-based search filters
- Tag-based analytics and reporting
- Template sharing between users (v2)
- Template versioning

---

## Examples

### Complete Workflow

```python
import asyncio
from supabase_client import get_supabase_client

async def template_workflow():
    supabase = get_supabase_client()
    user_id = "user-123"

    # 1. Create templates
    team_template = await supabase.create_template(
        user_id=user_id,
        name="Team Meeting",
        description="Weekly team sync",
        tags=["team", "sync", "weekly"]
    )
    print(f"Created: {team_template.id}")

    # 2. List all templates
    all_templates = await supabase.list_templates(user_id)
    print(f"Total templates: {len(all_templates)}")

    # 3. Get specific template
    template = await supabase.get_template_by_id(
        team_template.id,
        user_id
    )
    print(f"Retrieved: {template.name}")

    # 4. Update template
    success = await supabase.update_template(
        template_id=team_template.id,
        user_id=user_id,
        tags=["team", "sync", "bi-weekly"]
    )
    print(f"Updated: {success}")

    # 5. Delete template
    success = await supabase.delete_template(
        team_template.id,
        user_id
    )
    print(f"Deleted: {success}")

# Run workflow
asyncio.run(template_workflow())
```

---

## Performance Considerations

### Query Optimization

- Templates indexed by `user_id` for fast lookups
- Results ordered by `created_at DESC` for newest-first retrieval
- GIN index on tags for array operations

### Caching Strategy

Consider caching frequently-accessed templates:

```python
# Cache implementation example (future)
template_cache = {}

async def get_user_templates(user_id: str, use_cache: bool = True):
    if use_cache and user_id in template_cache:
        return template_cache[user_id]

    templates = await supabase.list_templates(user_id)
    template_cache[user_id] = templates
    return templates
```

### Scalability

- No N+1 query problems (single query per operation)
- Batch operations support (future enhancement)
- Connection pooling via Supabase client

---

## Troubleshooting

### Template Not Found

If `get_template_by_id` returns None:
- Verify user_id matches template owner
- Check template exists in database
- Verify RLS policies are enabled

### Query Timeouts

If operations timeout:
- Check network connection to Supabase
- Verify API rate limits not exceeded
- Check database performance in Supabase dashboard

### Permission Denied

All permission checks return False instead of raising errors:

```python
# This returns False, not an error
success = await supabase.update_template(
    template_id="foreign-template",
    user_id="user-456"
)
# success == False (permission denied)
```

---

## Version History

- **v1.0** (Phase 3, 2026-01): Initial implementation
  - Basic CRUD operations
  - RLS policies
  - Auto-tagging integration point
