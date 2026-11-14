from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import Base


class AgroecologicalZone(Base):
    __tablename__ = "agroecological_zones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False, unique=True)
    code: Mapped[str | None] = mapped_column(String(60), nullable=True, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    geographic_associations: Mapped[list["AgroecologicalZoneGeography"]] = relationship(
        "AgroecologicalZoneGeography",
        back_populates="agroecological_zone",
        cascade="all, delete-orphan",
    )
