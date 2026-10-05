from sqlalchemy.orm import DeclarativeBase

from app.db.base import Base


def test_base_is_declarative_with_empty_metadata() -> None:
    assert issubclass(Base, DeclarativeBase)
    # Aún no hay modelos: la primera migración llegará con el esquema de modelo-datos.md.
    assert Base.metadata.tables == {}
