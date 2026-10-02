from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, computed_field


class UrunOlustur(BaseModel):
    ad: str = Field(min_length=1, max_length=100)
    sku: str = Field(min_length=1, max_length=50)
    kategori: Optional[str] = None
    fiyat: float = Field(default=0, ge=0)
    stok: int = Field(default=0, ge=0)
    min_stok: int = Field(default=5, ge=0)


class UrunGuncelle(BaseModel):
    ad: Optional[str] = Field(default=None, min_length=1, max_length=100)
    kategori: Optional[str] = None
    fiyat: Optional[float] = Field(default=None, ge=0)
    min_stok: Optional[int] = Field(default=None, ge=0)


class UrunCikti(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ad: str
    sku: str
    kategori: Optional[str]
    fiyat: float
    stok: int
    min_stok: int
    olusturma_tarihi: datetime

    @computed_field
    @property
    def dusuk_stok(self) -> bool:
        return self.stok <= self.min_stok


class HareketOlustur(BaseModel):
    tur: Literal["giris", "cikis"]
    miktar: int = Field(gt=0)
    aciklama: Optional[str] = Field(default=None, max_length=200)


class HareketCikti(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    urun_id: int
    tur: str
    miktar: int
    aciklama: Optional[str]
    tarih: datetime
    
class StokOzeti(BaseModel):
    toplam_urun: int
    toplam_adet: int
    toplam_stok_degeri: float
    dusuk_stoklu_urun: int


class HareketOzeti(BaseModel):
    urun_id: int
    ad: str
    sku: str
    toplam_giris: int
    toplam_cikis: int