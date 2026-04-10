from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.community import (
    CommunityComment,
    CommunityPost,
    CommunityPostFlag,
    CommunityReaction,
    CommunitySubscription,
    CommunityTopic,
)
from app.models.user import User
from app.schemas.community import (
    CommunityCommentCreate,
    CommunityCommentOut,
    CommunityFlagCreate,
    CommunityModerateRequest,
    CommunityPostCreate,
    CommunityPostOut,
    CommunityPostUpdate,
    CommunityReactRequest,
    CommunitySubscriptionCreate,
    CommunitySubscriptionOut,
    CommunityTopicCreate,
    CommunityTopicOut,
    CommunityTopicUpdate,
)
from app.services.email import send_simple_email

router = APIRouter(prefix="/community", tags=["Community"])

VALID_POST_TYPES = {"discussion", "announcement"}
VALID_POST_STATUS = {"published", "hidden", "removed"}
VALID_REACTIONS = {"like", "love", "celebrate", "support", "insightful"}
VALID_FLAG_RESOLUTIONS = {"dismissed", "actioned"}


def _to_topic_out(topic: CommunityTopic) -> CommunityTopicOut:
    return CommunityTopicOut.model_validate(topic)


def _to_post_out(post: CommunityPost) -> CommunityPostOut:
    return CommunityPostOut.model_validate(post)


def _to_comment_out(comment: CommunityComment) -> CommunityCommentOut:
    return CommunityCommentOut.model_validate(comment)


def _to_sub_out(sub: CommunitySubscription) -> CommunitySubscriptionOut:
    return CommunitySubscriptionOut.model_validate(sub)


def _ensure_post_visible(post: CommunityPost, current_user: User):
    if post.status == "published":
        return
    if current_user.role in {"admin", "manager"}:
        return
    if str(post.author_id) == str(current_user.id):
        return
    raise HTTPException(status_code=404, detail="Post not found")


@router.get("/topics", response_model=list[CommunityTopicOut], status_code=200)
def list_topics(
    include_inactive: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(CommunityTopic)
    if not include_inactive or current_user.role not in {"admin", "manager"}:
        q = q.filter(CommunityTopic.is_active == True)
    topics = q.order_by(CommunityTopic.name.asc()).all()
    return [_to_topic_out(t) for t in topics]


@router.post("/topics", response_model=CommunityTopicOut, status_code=201)
def create_topic(
    body: CommunityTopicCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    topic = CommunityTopic(
        name=body.name.strip(),
        description=body.description,
        created_by=current_user.id,
        is_active=True,
    )
    db.add(topic)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Topic name already exists")
    db.refresh(topic)
    return _to_topic_out(topic)


@router.patch("/topics/{id}", response_model=CommunityTopicOut, status_code=200)
def update_topic(
    id: UUID,
    body: CommunityTopicUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    topic = db.query(CommunityTopic).filter(CommunityTopic.id == id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    if current_user.role not in {"admin", "manager"} and str(topic.created_by) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    if body.name is not None:
        topic.name = body.name.strip()
    if body.description is not None:
        topic.description = body.description
    if body.is_active is not None:
        topic.is_active = body.is_active

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Topic name already exists")
    db.refresh(topic)
    return _to_topic_out(topic)


@router.get("/posts", response_model=list[CommunityPostOut], status_code=200)
def list_posts(
    topic_id: Optional[UUID] = Query(None),
    author_id: Optional[UUID] = Query(None),
    post_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(CommunityPost)
    if topic_id:
        q = q.filter(CommunityPost.topic_id == topic_id)
    if author_id:
        q = q.filter(CommunityPost.author_id == author_id)
    if post_type:
        if post_type not in VALID_POST_TYPES:
            raise HTTPException(status_code=400, detail="Invalid post_type")
        q = q.filter(CommunityPost.post_type == post_type)

    if current_user.role in {"admin", "manager"}:
        if status:
            if status not in VALID_POST_STATUS:
                raise HTTPException(status_code=400, detail="Invalid status")
            q = q.filter(CommunityPost.status == status)
    else:
        if status and status != "published":
            raise HTTPException(status_code=403, detail="Only admins/managers can filter by hidden/removed status")
        q = q.filter(
            or_(
                CommunityPost.status == "published",
                CommunityPost.author_id == current_user.id,
            )
        )

    posts = (
        q.order_by(CommunityPost.is_pinned.desc(), CommunityPost.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [_to_post_out(p) for p in posts]


@router.post("/posts", response_model=CommunityPostOut, status_code=201)
async def create_post(
    body: CommunityPostCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if body.post_type not in VALID_POST_TYPES:
        raise HTTPException(status_code=400, detail="Invalid post_type")

    if body.topic_id:
        topic = db.query(CommunityTopic).filter(CommunityTopic.id == body.topic_id).first()
        if not topic or not topic.is_active:
            raise HTTPException(status_code=404, detail="Topic not found or inactive")

    post = CommunityPost(
        topic_id=body.topic_id,
        author_id=current_user.id,
        title=body.title.strip(),
        content=body.content.strip(),
        post_type=body.post_type,
        status="published",
        is_pinned=body.is_pinned if current_user.role in {"admin", "manager"} else False,
    )
    db.add(post)
    db.commit()
    db.refresh(post)

    # Option B confirmed: all authenticated users can create announcements.
    if post.post_type == "announcement" and post.topic_id:
        subscribed_users = (
            db.query(User)
            .join(CommunitySubscription, CommunitySubscription.user_id == User.id)
            .filter(
                CommunitySubscription.topic_id == post.topic_id,
                User.is_deleted == False,
                User.email != None,
            )
            .all()
        )
        recipients = sorted({u.email for u in subscribed_users if u.email and str(u.id) != str(current_user.id)})
        if recipients:
            background_tasks.add_task(
                send_simple_email,
                recipients,
                f"New community announcement: {post.title}",
                (
                    f"A new announcement was posted in the community.\n\n"
                    f"Title: {post.title}\n\n"
                    f"{post.content}\n\n"
                    f"Posted at: {post.created_at.isoformat()}"
                ),
            )

    return _to_post_out(post)


@router.get("/posts/{id}", response_model=CommunityPostOut, status_code=200)
def get_post(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    post = db.query(CommunityPost).filter(CommunityPost.id == id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    _ensure_post_visible(post, current_user)
    return _to_post_out(post)


@router.patch("/posts/{id}", response_model=CommunityPostOut, status_code=200)
def update_post(
    id: UUID,
    body: CommunityPostUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    post = db.query(CommunityPost).filter(CommunityPost.id == id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if current_user.role not in {"admin", "manager"} and str(post.author_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    if body.topic_id:
        topic = db.query(CommunityTopic).filter(CommunityTopic.id == body.topic_id).first()
        if not topic or not topic.is_active:
            raise HTTPException(status_code=404, detail="Topic not found or inactive")
        post.topic_id = body.topic_id
    if body.title is not None:
        post.title = body.title.strip()
    if body.content is not None:
        post.content = body.content.strip()
    if body.post_type is not None:
        if body.post_type not in VALID_POST_TYPES:
            raise HTTPException(status_code=400, detail="Invalid post_type")
        post.post_type = body.post_type
    if body.is_pinned is not None:
        if current_user.role not in {"admin", "manager"}:
            raise HTTPException(status_code=403, detail="Only admins/managers can pin posts")
        post.is_pinned = body.is_pinned

    db.commit()
    db.refresh(post)
    return _to_post_out(post)


@router.delete("/posts/{id}", status_code=200)
def delete_post(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    post = db.query(CommunityPost).filter(CommunityPost.id == id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if current_user.role not in {"admin", "manager"} and str(post.author_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    post.status = "removed"
    post.moderated_by = current_user.id
    db.commit()
    return {"message": "Post removed"}


@router.post("/posts/{id}/flag", status_code=200)
def flag_post(
    id: UUID,
    body: CommunityFlagCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    post = db.query(CommunityPost).filter(CommunityPost.id == id).first()
    if not post or post.status == "removed":
        raise HTTPException(status_code=404, detail="Post not found")

    existing = (
        db.query(CommunityPostFlag)
        .filter(CommunityPostFlag.post_id == id, CommunityPostFlag.user_id == current_user.id)
        .first()
    )
    if existing:
        return {"message": "Post already flagged", "flagId": existing.id}

    flag = CommunityPostFlag(
        post_id=id,
        user_id=current_user.id,
        reason=body.reason,
        resolution="pending",
    )
    db.add(flag)
    db.commit()
    db.refresh(flag)
    return {"message": "Post flagged for moderation", "flagId": flag.id}


@router.post("/posts/{id}/moderate", status_code=200)
def moderate_post(
    id: UUID,
    body: CommunityModerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "manager")),
):
    if body.status not in VALID_POST_STATUS:
        raise HTTPException(status_code=400, detail="Invalid status")
    if body.flag_resolution and body.flag_resolution not in VALID_FLAG_RESOLUTIONS:
        raise HTTPException(status_code=400, detail="Invalid flag_resolution")

    post = db.query(CommunityPost).filter(CommunityPost.id == id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    post.status = body.status
    post.moderated_by = current_user.id
    post.moderation_note = body.moderation_note

    if body.flag_resolution:
        flags = db.query(CommunityPostFlag).filter(
            CommunityPostFlag.post_id == id,
            CommunityPostFlag.resolution == "pending",
        ).all()
        now = datetime.now(timezone.utc)
        for flag in flags:
            flag.resolution = body.flag_resolution
            flag.resolved_by = current_user.id
            flag.resolved_at = now

    db.commit()
    return {"message": "Post moderated", "status": post.status}


@router.post("/posts/{id}/react", status_code=200)
def react_to_post(
    id: UUID,
    body: CommunityReactRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if body.reaction not in VALID_REACTIONS:
        raise HTTPException(status_code=400, detail="Invalid reaction")

    post = db.query(CommunityPost).filter(CommunityPost.id == id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    _ensure_post_visible(post, current_user)

    existing = db.query(CommunityReaction).filter(
        CommunityReaction.post_id == id,
        CommunityReaction.user_id == current_user.id,
    ).first()
    if not existing:
        reaction = CommunityReaction(
            post_id=id,
            user_id=current_user.id,
            reaction=body.reaction,
        )
        db.add(reaction)
        db.commit()
        return {"message": "Reaction added", "reaction": body.reaction}

    if existing.reaction == body.reaction:
        db.delete(existing)
        db.commit()
        return {"message": "Reaction removed"}

    existing.reaction = body.reaction
    db.commit()
    return {"message": "Reaction updated", "reaction": body.reaction}


@router.get("/posts/{id}/comments", response_model=list[CommunityCommentOut], status_code=200)
def list_comments(
    id: UUID,
    include_hidden: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    post = db.query(CommunityPost).filter(CommunityPost.id == id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    _ensure_post_visible(post, current_user)

    q = db.query(CommunityComment).filter(CommunityComment.post_id == id)
    if not include_hidden or current_user.role not in {"admin", "manager"}:
        q = q.filter(CommunityComment.status == "published")
    comments = q.order_by(CommunityComment.created_at.asc()).all()
    return [_to_comment_out(c) for c in comments]


@router.post("/posts/{id}/comments", response_model=CommunityCommentOut, status_code=201)
def add_comment(
    id: UUID,
    body: CommunityCommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    post = db.query(CommunityPost).filter(CommunityPost.id == id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    _ensure_post_visible(post, current_user)

    comment = CommunityComment(
        post_id=id,
        author_id=current_user.id,
        content=body.content.strip(),
        status="published",
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return _to_comment_out(comment)


@router.get("/feed", response_model=list[CommunityPostOut], status_code=200)
def browse_feed(
    topic_id: Optional[UUID] = Query(None),
    post_type: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(CommunityPost)
    if topic_id:
        q = q.filter(CommunityPost.topic_id == topic_id)
    if post_type:
        if post_type not in VALID_POST_TYPES:
            raise HTTPException(status_code=400, detail="Invalid post_type")
        q = q.filter(CommunityPost.post_type == post_type)

    if current_user.role in {"admin", "manager"}:
        q = q.filter(CommunityPost.status != "removed")
    else:
        q = q.filter(CommunityPost.status == "published")

    posts = (
        q.order_by(CommunityPost.is_pinned.desc(), CommunityPost.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [_to_post_out(p) for p in posts]


@router.get("/subscriptions", response_model=list[CommunitySubscriptionOut], status_code=200)
def list_subscriptions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    subs = (
        db.query(CommunitySubscription)
        .filter(CommunitySubscription.user_id == current_user.id)
        .order_by(CommunitySubscription.created_at.desc())
        .all()
    )
    return [_to_sub_out(s) for s in subs]


@router.post("/subscriptions", response_model=CommunitySubscriptionOut, status_code=201)
def subscribe(
    body: CommunitySubscriptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if (body.topic_id is None and body.post_id is None) or (body.topic_id is not None and body.post_id is not None):
        raise HTTPException(status_code=400, detail="Provide exactly one target: topic_id or post_id")

    if body.topic_id:
        topic = db.query(CommunityTopic).filter(CommunityTopic.id == body.topic_id, CommunityTopic.is_active == True).first()
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")
    if body.post_id:
        post = db.query(CommunityPost).filter(CommunityPost.id == body.post_id).first()
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        _ensure_post_visible(post, current_user)

    sub = CommunitySubscription(user_id=current_user.id, topic_id=body.topic_id, post_id=body.post_id)
    db.add(sub)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Already subscribed")
    db.refresh(sub)
    return _to_sub_out(sub)


@router.delete("/subscriptions", status_code=200)
def unsubscribe(
    body: CommunitySubscriptionCreate = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if (body.topic_id is None and body.post_id is None) or (body.topic_id is not None and body.post_id is not None):
        raise HTTPException(status_code=400, detail="Provide exactly one target: topic_id or post_id")

    q = db.query(CommunitySubscription).filter(CommunitySubscription.user_id == current_user.id)
    if body.topic_id:
        q = q.filter(CommunitySubscription.topic_id == body.topic_id)
    else:
        q = q.filter(CommunitySubscription.post_id == body.post_id)

    sub = q.first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    db.delete(sub)
    db.commit()
    return {"message": "Unsubscribed successfully"}


@router.post("/digest/send", status_code=200)
async def send_daily_digest(
    hours: int = Query(24, ge=1, le=168),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "manager")),
):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    posts = (
        db.query(CommunityPost)
        .filter(CommunityPost.status == "published", CommunityPost.created_at >= cutoff)
        .order_by(CommunityPost.created_at.desc())
        .all()
    )
    if not posts:
        return {"message": "No new posts for digest", "emailsSent": 0}

    subs = db.query(CommunitySubscription).all()
    subscribers_by_user: dict[UUID, list[CommunitySubscription]] = {}
    for s in subs:
        subscribers_by_user.setdefault(s.user_id, []).append(s)

    post_ids = {p.id for p in posts}
    topic_ids = {p.topic_id for p in posts if p.topic_id is not None}

    target_user_ids: set[UUID] = set()
    for user_id, user_subs in subscribers_by_user.items():
        for s in user_subs:
            if s.post_id and s.post_id in post_ids:
                target_user_ids.add(user_id)
                break
            if s.topic_id and s.topic_id in topic_ids:
                target_user_ids.add(user_id)
                break

    if not target_user_ids:
        return {"message": "No matching subscribers for digest", "emailsSent": 0}

    users = (
        db.query(User)
        .filter(
            User.id.in_(target_user_ids),
            User.is_deleted == False,
            User.email != None,
        )
        .all()
    )
    emails_sent = 0
    for user in users:
        body_lines = ["Here is your community digest:\n"]
        for post in posts[:20]:
            body_lines.append(f"- [{post.post_type}] {post.title}")
            body_lines.append(f"  {post.content[:200]}")
        ok = await send_simple_email(
            [user.email],
            "Your community daily digest",
            "\n".join(body_lines),
        )
        if ok:
            emails_sent += 1

    return {"message": "Digest completed", "emailsSent": emails_sent, "postsIncluded": min(len(posts), 20)}
