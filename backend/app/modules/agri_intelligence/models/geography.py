from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import Base


class Country(Base):
    __tablename__ = "countries"
    __table_args__ = (
        UniqueConstraint("name", name="uq_countries_name"),
        UniqueConstraint("iso2_code", name="uq_countries_iso2_code"),
        UniqueConstraint("iso3_code", name="uq_countries_iso3_code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    iso2_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    iso3_code: Mapped[str | None] = mapped_column(String(3), nullable=True)

    province_states: Mapped[list["ProvinceState"]] = relationship(
        "ProvinceState", back_populates="country", passive_deletes="all"
    )


class ProvinceState(Base):
    __tablename__ = "province_states"
    __table_args__ = (
        UniqueConstraint("country_id", "name", name="uq_province_states_country_name"),
        UniqueConstraint("country_id", "code", name="uq_province_states_country_code"),
        UniqueConstraint("id", "country_id", name="uq_province_states_id_country"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    country_id: Mapped[int] = mapped_column(
        ForeignKey("countries.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    code: Mapped[str | None] = mapped_column(String(40), nullable=True)

    country: Mapped[Country] = relationship("Country", back_populates="province_states")
    districts: Mapped[list["District"]] = relationship(
        "District", back_populates="province_state", passive_deletes="all"
    )


class District(Base):
    __tablename__ = "districts"
    __table_args__ = (
        UniqueConstraint(
            "province_state_id", "name", name="uq_districts_province_state_name"
        ),
        UniqueConstraint(
            "province_state_id", "code", name="uq_districts_province_state_code"
        ),
        UniqueConstraint(
            "id", "province_state_id", name="uq_districts_id_province_state"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    province_state_id: Mapped[int] = mapped_column(
        ForeignKey("province_states.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    code: Mapped[str | None] = mapped_column(String(40), nullable=True)

    province_state: Mapped[ProvinceState] = relationship(
        "ProvinceState", back_populates="districts"
    )
    localities: Mapped[list["Locality"]] = relationship(
        "Locality", back_populates="district", passive_deletes="all"
    )


class Locality(Base):
    __tablename__ = "localities"
    __table_args__ = (
        UniqueConstraint("district_id", "name", name="uq_localities_district_name"),
        UniqueConstraint("district_id", "code", name="uq_localities_district_code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    district_id: Mapped[int] = mapped_column(
        ForeignKey("districts.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    code: Mapped[str | None] = mapped_column(String(40), nullable=True)

    district: Mapped[District] = relationship("District", back_populates="localities")
