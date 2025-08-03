# backend/schemas/position.py
from pydantic import BaseModel

class PositionResponse(BaseModel):
    position_id: int
    position_name: str