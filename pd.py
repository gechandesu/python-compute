from pydantic import BaseModel, Extra


class EntityModel(BaseModel):
    """Basic entity model."""

    aaa: int
    bbb: int

    class Config:
        extra = Extra.forbid


class Some(EntityModel):
    ooo: str
    www: str

a = Some(ooo='dsda', www='wcd', sds=1)

print(a)
