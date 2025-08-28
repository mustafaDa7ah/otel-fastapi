from dataclasses import dataclass
from typing import List
from opentelemetry import trace, metrics
from .interfaces import IPipeRepository
from .dto import PipeDTO   # 👈 import DTO here

class PipeUseCases:
    def __init__(self, repo: IPipeRepository):
        self.repo = repo
        self.tracer = trace.get_tracer("application.pipe_use_cases")
        meter = metrics.get_meter("application.pipe_use_cases")
        # Custom business metrics
        self.pipes_created = meter.create_counter(
            name="pipes.created",
            description="Number of pipes created",
        )

        self.pipe_latency = meter.create_histogram(
            name="pipes.create.latency_ms",
            description="Latency of create pipe in ms",
            unit="ms",
        )

    async def create_pipe(self) -> PipeDTO:
        with self.tracer.start_as_current_span("usecase.create_pipe") as span:
            # (fake work) — in a real app you’d validate, call domain, persist, etc.
            from time import perf_counter, sleep
            start = perf_counter()
            sleep(0.02)  # simulate work 20ms

            created = await self.repo.create(PipeDTO(id=self.repo.next_id(), status="created"))
            self.pipes_created.add(1, {"status": "created"})
            elapsed_ms = (perf_counter() - start) * 1000.0
            self.pipe_latency.record(elapsed_ms, {"op": "create"})
            span.set_attribute("pipe.id", created.id)
            return 
            
    async def get_pipe(self, id: int) -> PipeDTO:
        with self.tracer.start_as_current_span("usecase.get_pipe") as span:
            span.set_attribute("pipe.id", id)
            p = await self.repo.get(id)
            if p is None:
                raise ValueError(f"Pipe {id} not found")
            return p

    async def list_pipes(self) -> List[PipeDTO]:
        with self.tracer.start_as_current_span("usecase.list_pipes"):
            return await self.repo.list()        

