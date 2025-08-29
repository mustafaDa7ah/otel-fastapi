from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from uuid import UUID, uuid4


class User(BaseModel):
    id: UUID
    name: str
    email: str
    created_at: datetime = datetime.now()

    def __init__(self, **kwargs):
        if 'id' not in kwargs:
            kwargs['id'] = uuid4()
        if 'created_at' not in kwargs:
            kwargs['created_at'] = datetime.now()
        super().__init__(**kwargs)


class Product(BaseModel):
    id: UUID
    name: str
    price: float
    description: Optional[str] = None


class Order(BaseModel):
    id: UUID
    user_id: UUID
    product_ids: List[UUID]
    total_amount: float
    status: str = "pending"
    created_at: datetime = datetime.now()