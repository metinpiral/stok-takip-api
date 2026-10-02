from datetime import datetime
from typing import Optional

from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Urun(Base):
    __tablename__ = "urunler"

    id: Mapped[int] = mapped_column(primary_key=True)
    ad: Mapped[str] = mapped_column(String(100))
    sku: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    kategori: Mapped[Optional[str]] = mapped_column(String(50))
    fiyat: Mapped[float] = mapped_column(default=0)
    stok: Mapped[int] = mapped_column(default=0)
    min_stok: Mapped[int] = mapped_column(default=5)
    olusturma_tarihi: Mapped[datetime] = mapped_column(default=datetime.now)

    hareketler: Mapped[list["StokHareketi"]] = relationship(
        back_populates="urun", cascade="all, delete-orphan"
    )


class StokHareketi(Base):
    __tablename__ = "stok_hareketleri"

    id: Mapped[int] = mapped_column(primary_key=True)
    urun_id: Mapped[int] = mapped_column(ForeignKey("urunler.id"))
    tur: Mapped[str] = mapped_column(String(10))  # "giris" veya "cikis"
    miktar: Mapped[int]
    aciklama: Mapped[Optional[str]] = mapped_column(String(200))
    tarih: Mapped[datetime] = mapped_column(default=datetime.now)

    urun: Mapped["Urun"] = relationship(back_populates="hareketler")