import json
from uuid import UUID
from typing import List, Optional
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Float, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from opentelemetry import trace

from app.domain.models import User, Product, Order
from app.domain.repositories import UserRepository, ProductRepository, OrderRepository

Base = declarative_base()
tracer = trace.get_tracer(__name__)

class UserModel(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True)
    name = Column(String)
    email = Column(String)
    created_at = Column(DateTime)


class ClickHouseUserRepository(UserRepository):
    def __init__(self, session):
        self.session = session

    def add(self, user: User) -> User:
        with tracer.start_as_current_span("user_repository_add") as span:
            span.set_attribute("user.id", str(user.id))
            span.set_attribute("user.name", user.name)
            
            user_model = UserModel(
                id=str(user.id),
                name=user.name,
                email=user.email,
                created_at=user.created_at
            )
            self.session.add(user_model)
            self.session.commit()
            return user

    def get_by_id(self, user_id: UUID) -> Optional[User]:
        with tracer.start_as_current_span("user_repository_get_by_id") as span:
            span.set_attribute("user.id", str(user_id))
            
            result = self.session.query(UserModel).filter(UserModel.id == str(user_id)).first()
            if result:
                return User(
                    id=UUID(result.id),
                    name=result.name,
                    email=result.email,
                    created_at=result.created_at
                )
            return None

    def get_all(self) -> List[User]:
        with tracer.start_as_current_span("user_repository_get_all"):
            results = self.session.query(UserModel).all()
            return [
                User(
                    id=UUID(result.id),
                    name=result.name,
                    email=result.email,
                    created_at=result.created_at
                )
                for result in results
            ]