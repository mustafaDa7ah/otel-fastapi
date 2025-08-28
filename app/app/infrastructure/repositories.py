from typing import Dict, List, Optional
from app.application.use_cases import PipeDTO
from app.application.interfaces import IPipeRepository

class InMemoryPipeRepository(IPipeRepository):
    def __init__(self):
        self._db: Dict[int, PipeDTO] = {}
        self._id = 0

    def next_id(self) -> int:
        self._id += 1
        return self._id

    async def create(self, pipe: PipeDTO) -> PipeDTO:
        self._db[pipe.id] = pipe
        return pipe

    async def get(self, id: int) -> Optional[PipeDTO]:
        return self._db.get(id)

    async def list(self) -> List[PipeDTO]:
        return list(self._db.values())
