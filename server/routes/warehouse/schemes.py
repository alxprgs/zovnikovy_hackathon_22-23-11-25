from pydantic import BaseModel, Field

class AddItem(BaseModel):
    type: str = Field(...)
    count: int = Field(...)
    company: str = Field(...)
    warehouse_id: int = Field(...)

class RemoveItem(BaseModel):
    type: str = Field(...)
    count: int = Field(...)
    company: str = Field(...)
    warehouse_id: int = Field(...)

class SetTypeMinimum(BaseModel):
    type: str = Field(...)
    count: int = Field(...)
    company: str = Field(...)
    warehouse_id: int = Field(...)