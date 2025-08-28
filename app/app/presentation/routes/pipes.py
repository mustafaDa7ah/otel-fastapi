from fastapi import APIRouter, Depends
from app.application.use_cases import PipeUseCases, PipeDTO
from app.infrastructure.di import get_pipe_use_cases

router = APIRouter(prefix="/pipes", tags=["pipes"])

@router.post("", response_model=PipeDTO)
async def create_pipe(uc: PipeUseCases = Depends(get_pipe_use_cases)):
    return await uc.create_pipe()

@router.get("/{id}", response_model=PipeDTO)
async def get_pipe(id: int, uc: PipeUseCases = Depends(get_pipe_use_cases)):
    return await uc.get_pipe(id)

@router.get("", response_model=list[PipeDTO])
async def list_pipes(uc: PipeUseCases = Depends(get_pipe_use_cases)):
    return await uc.list_pipes()
