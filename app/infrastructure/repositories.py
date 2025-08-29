import json
import logging
from uuid import UUID
from typing import List, Optional
from datetime import datetime
from sqlalchemy import Column, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from opentelemetry import trace

from app.domain.models import User
from app.domain.repositories import UserRepository

Base = declarative_base()
tracer = trace.get_tracer(__name__)

# ✅ Add this
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class UserModel(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True)
    name = Column(String)
    email = Column(String)
    created_at = Column(DateTime)

class MockUserRepository(UserRepository):
    _users = []  # class-level storage

    def __init__(self):
        self.users = MockUserRepository._users

    def add(self, user: User) -> User:
        with tracer.start_as_current_span("mock_repository_add") as span:
            span.set_attribute("user.id", str(user.id))
            span.set_attribute("user.name", user.name)
            self.users.append(user)

            logger.info(f"Mock: Added user {user.name} with ID {user.id}. Total users: {len(self.users)}")
            return user

    def get_by_id(self, user_id: UUID) -> Optional[User]:
        with tracer.start_as_current_span("mock_repository_get_by_id") as span:
            span.set_attribute("user.id", str(user_id))
            for user in self.users:
                if user.id == user_id:
                    logger.info(f"Mock: Found user {user.name} with ID {user_id}")
                    return user
            logger.warning(f"Mock: User not found with ID {user_id}")
            return None

    def get_all(self) -> List[User]:
        with tracer.start_as_current_span("mock_repository_get_all"):
            logger.info(f"Mock: Returning {len(self.users)} users")
            return self.users.copy()
