#!/usr/bin/env python3
"""
Template API Tests
Comprehensive test suite for template CRUD operations
"""

import asyncio
import pytest
from datetime import datetime
from typing import List, Optional

from models import Template
from exceptions import SupabaseQueryError


class MockSupabaseClient:
    """Mock Supabase client for testing templates"""

    def __init__(self):
        self.templates = {}  # In-memory storage for testing
        self.next_id = 1

    async def list_templates(self, user_id: str) -> List[Template]:
        """Mock list_templates"""
        return [
            t for t in self.templates.values()
            if t.user_id == user_id
        ]

    async def get_template_by_id(
        self,
        template_id: str,
        user_id: str
    ) -> Optional[Template]:
        """Mock get_template_by_id"""
        template = self.templates.get(template_id)
        if template and template.user_id == user_id:
            return template
        return None

    async def create_template(
        self,
        user_id: str,
        name: str,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Optional[Template]:
        """Mock create_template"""
        template_id = f"template-{self.next_id}"
        self.next_id += 1

        template = Template(
            id=template_id,
            user_id=user_id,
            name=name,
            description=description,
            tags=tags or [],
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        self.templates[template_id] = template
        return template

    async def update_template(
        self,
        template_id: str,
        user_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> bool:
        """Mock update_template"""
        template = self.templates.get(template_id)
        if not template or template.user_id != user_id:
            return False

        if name is not None:
            template.name = name
        if description is not None:
            template.description = description
        if tags is not None:
            template.tags = tags

        template.updated_at = datetime.now()
        return True

    async def delete_template(self, template_id: str, user_id: str) -> bool:
        """Mock delete_template"""
        template = self.templates.get(template_id)
        if not template or template.user_id != user_id:
            return False

        del self.templates[template_id]
        return True


# Test suite
class TestTemplateAPI:
    """Test suite for template API operations"""

    @pytest.fixture
    async def client(self):
        """Create a mock Supabase client for testing"""
        return MockSupabaseClient()

    @pytest.mark.asyncio
    async def test_create_template(self):
        """Test creating a template"""
        client = MockSupabaseClient()
        user_id = "user-1"

        template = await client.create_template(
            user_id=user_id,
            name="Team Meeting",
            description="Regular team sync",
            tags=["team", "sync"]
        )

        assert template is not None
        assert template.name == "Team Meeting"
        assert template.user_id == user_id
        assert template.description == "Regular team sync"
        assert template.tags == ["team", "sync"]
        assert template.created_at is not None

    @pytest.mark.asyncio
    async def test_create_template_with_empty_name_fails(self):
        """Test that creating template with empty name fails"""
        client = MockSupabaseClient()

        with pytest.raises(ValueError):
            Template(
                id="test",
                user_id="user-1",
                name="",  # Empty name
                tags=[]
            )

    @pytest.mark.asyncio
    async def test_list_templates(self):
        """Test listing templates for a user"""
        client = MockSupabaseClient()
        user_id = "user-1"
        other_user_id = "user-2"

        # Create templates for different users
        await client.create_template(
            user_id=user_id,
            name="Template 1",
            tags=["tag1"]
        )
        await client.create_template(
            user_id=user_id,
            name="Template 2",
            tags=["tag2"]
        )
        await client.create_template(
            user_id=other_user_id,
            name="Template 3",
            tags=["tag3"]
        )

        # List templates for user-1
        templates = await client.list_templates(user_id)

        assert len(templates) == 2
        assert all(t.user_id == user_id for t in templates)
        assert templates[0].name in ["Template 1", "Template 2"]

    @pytest.mark.asyncio
    async def test_list_empty_templates(self):
        """Test listing templates when user has none"""
        client = MockSupabaseClient()

        templates = await client.list_templates("user-empty")

        assert len(templates) == 0

    @pytest.mark.asyncio
    async def test_get_template_by_id(self):
        """Test getting a specific template"""
        client = MockSupabaseClient()
        user_id = "user-1"

        created = await client.create_template(
            user_id=user_id,
            name="Test Template",
            description="Test description",
            tags=["test"]
        )

        retrieved = await client.get_template_by_id(created.id, user_id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.name == "Test Template"

    @pytest.mark.asyncio
    async def test_get_template_wrong_user(self):
        """Test that user cannot access another user's template"""
        client = MockSupabaseClient()
        user_id = "user-1"
        other_user_id = "user-2"

        created = await client.create_template(
            user_id=user_id,
            name="Private Template",
            tags=[]
        )

        # Try to access with different user
        retrieved = await client.get_template_by_id(created.id, other_user_id)

        assert retrieved is None

    @pytest.mark.asyncio
    async def test_update_template(self):
        """Test updating a template"""
        client = MockSupabaseClient()
        user_id = "user-1"

        created = await client.create_template(
            user_id=user_id,
            name="Original Name",
            description="Original description",
            tags=["original"]
        )

        # Update template
        success = await client.update_template(
            template_id=created.id,
            user_id=user_id,
            name="Updated Name",
            tags=["updated", "new"]
        )

        assert success is True

        # Verify update
        updated = await client.get_template_by_id(created.id, user_id)
        assert updated.name == "Updated Name"
        assert updated.tags == ["updated", "new"]
        assert updated.description == "Original description"  # Unchanged

    @pytest.mark.asyncio
    async def test_update_template_partial(self):
        """Test partial update of template"""
        client = MockSupabaseClient()
        user_id = "user-1"

        created = await client.create_template(
            user_id=user_id,
            name="Original",
            description="Original desc",
            tags=["tag1"]
        )

        # Update only name
        success = await client.update_template(
            template_id=created.id,
            user_id=user_id,
            name="New Name"
        )

        assert success is True

        updated = await client.get_template_by_id(created.id, user_id)
        assert updated.name == "New Name"
        assert updated.description == "Original desc"  # Unchanged
        assert updated.tags == ["tag1"]  # Unchanged

    @pytest.mark.asyncio
    async def test_update_template_wrong_user(self):
        """Test that user cannot update another user's template"""
        client = MockSupabaseClient()
        user_id = "user-1"
        other_user_id = "user-2"

        created = await client.create_template(
            user_id=user_id,
            name="Template",
            tags=[]
        )

        # Try to update with different user
        success = await client.update_template(
            template_id=created.id,
            user_id=other_user_id,
            name="Hacked Name"
        )

        assert success is False

        # Verify original is unchanged
        original = await client.get_template_by_id(created.id, user_id)
        assert original.name == "Template"

    @pytest.mark.asyncio
    async def test_delete_template(self):
        """Test deleting a template"""
        client = MockSupabaseClient()
        user_id = "user-1"

        created = await client.create_template(
            user_id=user_id,
            name="To Delete",
            tags=[]
        )

        # Verify it exists
        assert await client.get_template_by_id(created.id, user_id) is not None

        # Delete it
        success = await client.delete_template(created.id, user_id)
        assert success is True

        # Verify it's gone
        assert await client.get_template_by_id(created.id, user_id) is None

    @pytest.mark.asyncio
    async def test_delete_template_wrong_user(self):
        """Test that user cannot delete another user's template"""
        client = MockSupabaseClient()
        user_id = "user-1"
        other_user_id = "user-2"

        created = await client.create_template(
            user_id=user_id,
            name="Protected",
            tags=[]
        )

        # Try to delete with different user
        success = await client.delete_template(created.id, other_user_id)
        assert success is False

        # Verify it still exists
        assert await client.get_template_by_id(created.id, user_id) is not None

    @pytest.mark.asyncio
    async def test_template_idempotency(self):
        """Test idempotent template operations"""
        client = MockSupabaseClient()
        user_id = "user-1"

        # Create template
        t1 = await client.create_template(
            user_id=user_id,
            name="Test",
            tags=["tag1", "tag2"]
        )

        # Update with same values (should be idempotent)
        success = await client.update_template(
            template_id=t1.id,
            user_id=user_id,
            name="Test",
            tags=["tag1", "tag2"]
        )

        assert success is True

        # Verify no errors
        t2 = await client.get_template_by_id(t1.id, user_id)
        assert t2.name == t1.name
        assert t2.tags == t1.tags

    @pytest.mark.asyncio
    async def test_template_tags_sanitization(self):
        """Test that template tags are sanitized"""
        from models import Template

        # Test with empty string tags
        template = Template(
            id="test",
            user_id="user-1",
            name="Test",
            tags=["", "  ", "valid", ""]
        )

        # Should filter out empty strings
        assert len(template.tags) == 1
        assert template.tags[0] == "valid"

    @pytest.mark.asyncio
    async def test_template_tags_stripped(self):
        """Test that template tags are trimmed"""
        from models import Template

        template = Template(
            id="test",
            user_id="user-1",
            name="Test",
            tags=["  tag1  ", "tag2 ", " tag3"]
        )

        # Should trim whitespace
        assert template.tags == ["tag1", "tag2", "tag3"]

    def test_template_validation(self):
        """Test Template model validation"""
        from models import Template

        # Valid template
        template = Template(
            id="test",
            user_id="user-1",
            name="Valid Template",
            tags=["tag1", "tag2"]
        )
        assert template is not None

        # Invalid: empty name
        with pytest.raises(ValueError):
            Template(
                id="test",
                user_id="user-1",
                name="",
                tags=[]
            )

        # Invalid: None name
        with pytest.raises(ValueError):
            Template(
                id="test",
                user_id="user-1",
                name=None,
                tags=[]
            )

    def test_template_defaults(self):
        """Test Template model defaults"""
        from models import Template

        template = Template(
            id="test",
            user_id="user-1",
            name="Test"
        )

        assert template.description is None
        assert template.tags == []
        assert template.created_at is None
        assert template.updated_at is None

    @pytest.mark.asyncio
    async def test_multiple_users_isolation(self):
        """Test that templates are properly isolated between users"""
        client = MockSupabaseClient()

        users = [f"user-{i}" for i in range(1, 4)]

        # Create templates for each user
        for i, user_id in enumerate(users):
            for j in range(3):
                await client.create_template(
                    user_id=user_id,
                    name=f"Template-{i}-{j}",
                    tags=[user_id]
                )

        # Verify isolation
        for user_id in users:
            templates = await client.list_templates(user_id)
            assert len(templates) == 3
            assert all(t.user_id == user_id for t in templates)

    @pytest.mark.asyncio
    async def test_template_crud_complete_flow(self):
        """Test complete CRUD flow for templates"""
        client = MockSupabaseClient()
        user_id = "user-1"

        # CREATE
        created = await client.create_template(
            user_id=user_id,
            name="Project Template",
            description="For project meetings",
            tags=["project", "team"]
        )
        assert created.id is not None

        # READ
        retrieved = await client.get_template_by_id(created.id, user_id)
        assert retrieved == created

        # LIST
        all_templates = await client.list_templates(user_id)
        assert created in all_templates

        # UPDATE
        update_success = await client.update_template(
            template_id=created.id,
            user_id=user_id,
            name="Updated Project Template",
            tags=["project", "team", "updated"]
        )
        assert update_success is True

        # VERIFY UPDATE
        updated = await client.get_template_by_id(created.id, user_id)
        assert updated.name == "Updated Project Template"
        assert "updated" in updated.tags

        # DELETE
        delete_success = await client.delete_template(created.id, user_id)
        assert delete_success is True

        # VERIFY DELETE
        deleted = await client.get_template_by_id(created.id, user_id)
        assert deleted is None

        all_templates = await client.list_templates(user_id)
        assert created not in all_templates


async def run_tests():
    """Run all tests with pytest"""
    import sys

    # Run pytest programmatically
    exit_code = pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-s"
    ])

    return exit_code


if __name__ == "__main__":
    print("Running Template API Tests...")
    print("=" * 60)

    exit_code = asyncio.run(run_tests())

    print("=" * 60)
    if exit_code == 0:
        print("All tests passed!")
    else:
        print("Some tests failed. See details above.")

    exit(exit_code)
