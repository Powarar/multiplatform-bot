from sqlalchemy import Integer, String, Text, DateTime, ForeignKey, BigInteger, Enum as SQLEnum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship, DeclarativeBase
from datetime import datetime, timezone
from typing import List, Optional
import enum


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    posts: Mapped[List["Post"]] = relationship(back_populates="user")
    communities: Mapped[List["Community"]] = relationship(back_populates="owner")


class PlatformType(enum.Enum):
    TELEGRAM = "telegram"
    VK = "vk"
    MAX = "MAX"


class Community(Base):
    __tablename__ = "communities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    platform: Mapped[PlatformType] = mapped_column(SQLEnum(PlatformType), nullable=False)
    community_id: Mapped[str] = mapped_column(String(255), nullable=False)
    community_name: Mapped[str] = mapped_column(String(255), nullable=False)
    access_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    owner: Mapped["User"] = relationship(back_populates="communities")
    posts: Mapped[List["PostToCommunity"]] = relationship(back_populates="community")


class Post(Base):
    __tablename__ = "posts"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    
    message_id: Mapped[int] = mapped_column(Integer, nullable=False)
    from_chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # ✅ ДОБАВЛЕНО: relationships для двусторонних связей
    user: Mapped["User"] = relationship(back_populates="posts")
    communities: Mapped[List["PostToCommunity"]] = relationship(back_populates="post")


class PostStatus(enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class PostToCommunity(Base):
    __tablename__ = "post_to_community"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    post_id: Mapped[int] = mapped_column(Integer, ForeignKey("posts.id"), nullable=False)
    community_id: Mapped[int] = mapped_column(Integer, ForeignKey("communities.id"), nullable=False)
    status: Mapped[PostStatus] = mapped_column(SQLEnum(PostStatus), default=PostStatus.PENDING)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    post: Mapped["Post"] = relationship(back_populates="communities")
    community: Mapped["Community"] = relationship(back_populates="posts")
