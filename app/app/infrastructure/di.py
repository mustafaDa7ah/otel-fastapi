from fastapi import Depends
from app.application.use_cases import PipeUseCases
from app.infrastructure.repositories import InMemoryPipeRepository

# Simple "container"
_repo = InMemoryPipeRepository()
_use_cases = PipeUseCases(_repo)

def get_pipe_use_cases() -> PipeUseCases:
    return _use_cases
