from pydantic import BaseModel, Field


class IngestionConfig(BaseModel):
    dataset: str = Field(default="bhavcopy")
    chunk_days: int = Field(default=30)
    max_parallel_chunks: int = Field(default=4)
