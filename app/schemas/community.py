from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CommunityTopicCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    description: Optional[str] = None


class CommunityTopicUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=200)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class CommunityTopicOut(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    created_by: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CommunityPostCreate(BaseModel):
    topic_id: Optional[UUID] = None
    title: str = Field(min_length=2, max_length=300)
    content: str = Field(min_length=1)
    post_type: str = Field(default="discussion")
    is_pinned: bool = False


class CommunityPostUpdate(BaseModel):
    topic_id: Optional[UUID] = None
    title: Optional[str] = Field(default=None, min_length=2, max_length=300)
    content: Optional[str] = Field(default=None, min_length=1)
    post_type: Optional[str] = None
    is_pinned: Optional[bool] = None


class CommunityPostOut(BaseModel):
    id: UUID
    topic_id: Optional[UUID] = None
    author_id: Optional[UUID] = None
    title: str
    content: str
    post_type: str
    status: str
    is_pinned: bool
    moderated_by: Optional[UUID] = None
    moderation_note: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CommunityFlagCreate(BaseModel):
    reason: Optional[str] = Field(default=None, max_length=500)


class CommunityModerateRequest(BaseModel):
    status: str = Field(description="published | hidden | removed")
    moderation_note: Optional[str] = Field(default=None, max_length=1000)
    flag_resolution: Optional[str] = Field(default=None, description="dismissed | actioned")


class CommunityReactRequest(BaseModel):
    reaction: str = Field(description="like | love | celebrate | support | insightful")


class CommunityCommentCreate(BaseModel):
    content: str = Field(min_length=1)


class CommunityCommentOut(BaseModel):
    id: UUID
    post_id: UUID
    author_id: UUID
    content: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CommunitySubscriptionCreate(BaseModel):
    topic_id: Optional[UUID] = None
    post_id: Optional[UUID] = None


class CommunitySubscriptionOut(BaseModel):
    id: UUID
    user_id: UUID
    topic_id: Optional[UUID] = None
    post_id: Optional[UUID] = None
    created_at: datetime

    model_config = {"from_attributes": True}
