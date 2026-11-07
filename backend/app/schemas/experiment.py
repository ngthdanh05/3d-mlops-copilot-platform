from pydantic import Field

from app.schemas.base import InputSchema, ORMSchema, UTCDateTime


class ExperimentCreate(InputSchema):
    name: str = Field(min_length=1, max_length=255, examples=["MNIST-CNN-v1"])
    description: str | None = Field(default=None, max_length=10_000)


class ExperimentRead(ORMSchema):
    id: int
    name: str
    description: str | None
    created_at: UTCDateTime
