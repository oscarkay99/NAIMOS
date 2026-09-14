from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class Page(BaseModel):
    total: int
    limit: int
    offset: int
