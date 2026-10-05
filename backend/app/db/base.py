from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base de los modelos ORM. Alembic genera las migraciones a partir de su metadata."""
