from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

class UserRepository(ABC):
    @abstractmethod
    def add(self, user) -> object:
        pass
    
    @abstractmethod
    def get_by_id(self, user_id: UUID) -> Optional[object]:
        pass
    
    @abstractmethod
    def get_all(self) -> List[object]:
        pass


class ProductRepository(ABC):
    @abstractmethod
    def add(self, product) -> object:
        pass
    
    @abstractmethod
    def get_by_id(self, product_id: UUID) -> Optional[object]:
        pass
    
    @abstractmethod
    def get_all(self) -> List[object]:
        pass


class OrderRepository(ABC):
    @abstractmethod
    def add(self, order) -> object:
        pass
    
    @abstractmethod
    def get_by_id(self, order_id: UUID) -> Optional[object]:
        pass
    
    @abstractmethod
    def get_all(self) -> List[object]:
        pass
    
    @abstractmethod
    def get_by_user_id(self, user_id: UUID) -> List[object]:
        pass