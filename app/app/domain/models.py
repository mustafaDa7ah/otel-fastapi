from dataclasses import dataclass
from datetime import datetime

@dataclass
class Pipe:
    id: int
    status: str = "created"
    created_at: datetime = datetime.utcnow()
