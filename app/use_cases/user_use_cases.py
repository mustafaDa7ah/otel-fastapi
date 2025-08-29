from uuid import UUID
from typing import List, Optional
from app.domain.models import User
from app.domain.repositories import UserRepository


class UserUseCases:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    def create_user(self, name: str, email: str) -> User:
        user = User(name=name, email=email)
        return self.user_repository.add(user)

    def get_user(self, user_id: UUID) -> Optional[User]:
        return self.user_repository.get_by_id(user_id)

    def get_all_users(self) -> List[User]:
        return self.user_repository.get_all()