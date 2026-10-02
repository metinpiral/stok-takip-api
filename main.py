from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query, status
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

import models
import schemas
from database import Base, engine, get_db

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Stok Takip API")


def urun_getir_veya_404(urun_id: int, db: Session) -> models.Urun:
    urun = db.get(models.Urun, urun_id)
    if urun is None:
        raise HTTPException(status_code=404, detail="Ürün bulunamadı")
    return urun


@app.get("/")
def ana_sayfa():
    return {"mesaj": "Stok Takip API çalışıyor"}


@app.post(
    "/urunler",
    response_model=schemas.UrunCikti,
    status_code=status.HTTP_201_CREATED,
)
def urun_ekle(veri: schemas.UrunOlustur, db: Session = Depends(get_db)):
    mevcut = db.scalar(select(models.Urun).where(models.Urun.sku == veri.sku))
    if mevcut:
        raise HTTPException(
            status_code=409, detail="Bu SKU ile kayıtlı bir ürün zaten var"
        )

    urun = models.Urun(**veri.model_dump())

    # Başlangıç stoğu varsa bunu da hareket olarak kaydet
    if veri.stok > 0:
        urun.hareketler.append(
            models.StokHareketi(
                tur="giris", miktar=veri.stok, aciklama="Açılış stoğu"
            )
        )

    db.add(urun)
    db.commit()
    db.refresh(urun)
    return urun


@app.get("/urunler", response_model=list[schemas.UrunCikti])
def urunleri_listele(
    kategori: Optional[str] = None, db: Session = Depends(get_db)
):
    sorgu = select(models.Urun).order_by(models.Urun.id)
    if kategori:
        sorgu = sorgu.where(models.Urun.kategori == kategori)
    return db.scalars(sorgu).all()


@app.get("/urunler/{urun_id}", response_model=schemas.UrunCikti)
def urun_detay(urun_id: int, db: Session = Depends(get_db)):
    return urun_getir_veya_404(urun_id, db)


@app.patch("/urunler/{urun_id}", response_model=schemas.UrunCikti)
def urun_guncelle(
    urun_id: int, veri: schemas.UrunGuncelle, db: Session = Depends(get_db)
):
    urun = urun_getir_veya_404(urun_id, db)
    for alan, deger in veri.model_dump(exclude_unset=True).items():
        setattr(urun, alan, deger)
    db.commit()
    db.refresh(urun)
    return urun


@app.delete("/urunler/{urun_id}", status_code=status.HTTP_204_NO_CONTENT)
def urun_sil(urun_id: int, db: Session = Depends(get_db)):
    urun = urun_getir_veya_404(urun_id, db)
    db.delete(urun)
    db.commit()
@app.post(
    "/urunler/{urun_id}/hareketler",
    response_model=schemas.HareketCikti,
    status_code=status.HTTP_201_CREATED,
)
def hareket_ekle(
    urun_id: int, veri: schemas.HareketOlustur, db: Session = Depends(get_db)
):
    urun = urun_getir_veya_404(urun_id, db)

    if veri.tur == "cikis":
        if veri.miktar > urun.stok:
            raise HTTPException(
                status_code=400,
                detail=f"Yetersiz stok. Mevcut: {urun.stok}, istenen: {veri.miktar}",
            )
        urun.stok -= veri.miktar
    else:
        urun.stok += veri.miktar

    hareket = models.StokHareketi(urun_id=urun.id, **veri.model_dump())
    db.add(hareket)
    db.commit()
    db.refresh(hareket)
    return hareket


@app.get(
    "/urunler/{urun_id}/hareketler",
    response_model=list[schemas.HareketCikti],
)
def hareketleri_listele(urun_id: int, db: Session = Depends(get_db)):
    urun_getir_veya_404(urun_id, db)
    sorgu = (
        select(models.StokHareketi)
        .where(models.StokHareketi.urun_id == urun_id)
        .order_by(models.StokHareketi.tarih.desc(), models.StokHareketi.id.desc())
    )
    return db.scalars(sorgu).all()


@app.get("/raporlar/dusuk-stok", response_model=list[schemas.UrunCikti])
def dusuk_stoklu_urunler(db: Session = Depends(get_db)):
    sorgu = (
        select(models.Urun)
        .where(models.Urun.stok <= models.Urun.min_stok)
        .order_by(models.Urun.stok)
    )
    return db.scalars(sorgu).all()


@app.get("/raporlar/ozet", response_model=schemas.StokOzeti)
def stok_ozeti(db: Session = Depends(get_db)):
    sonuc = db.execute(
        select(
            func.count(models.Urun.id),
            func.coalesce(func.sum(models.Urun.stok), 0),
            func.coalesce(func.sum(models.Urun.stok * models.Urun.fiyat), 0),
            func.coalesce(
                func.sum(
                    case((models.Urun.stok <= models.Urun.min_stok, 1), else_=0)
                ),
                0,
            ),
        )
    ).one()

    return schemas.StokOzeti(
        toplam_urun=sonuc[0],
        toplam_adet=sonuc[1],
        toplam_stok_degeri=round(sonuc[2], 2),
        dusuk_stoklu_urun=sonuc[3],
    )


@app.get("/raporlar/hareketler", response_model=list[schemas.HareketOzeti])
def hareket_ozeti(
    gun: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    baslangic = datetime.now() - timedelta(days=gun)

    toplam_giris = func.coalesce(
        func.sum(
            case(
                (models.StokHareketi.tur == "giris", models.StokHareketi.miktar),
                else_=0,
            )
        ),
        0,
    )
    toplam_cikis = func.coalesce(
        func.sum(
            case(
                (models.StokHareketi.tur == "cikis", models.StokHareketi.miktar),
                else_=0,
            )
        ),
        0,
    )

    sorgu = (
        select(
            models.Urun.id,
            models.Urun.ad,
            models.Urun.sku,
            toplam_giris.label("toplam_giris"),
            toplam_cikis.label("toplam_cikis"),
        )
        .join(models.StokHareketi, models.StokHareketi.urun_id == models.Urun.id)
        .where(models.StokHareketi.tarih >= baslangic)
        .group_by(models.Urun.id)
        .order_by(toplam_cikis.desc())
    )

    return [
        schemas.HareketOzeti(
            urun_id=s.id,
            ad=s.ad,
            sku=s.sku,
            toplam_giris=s.toplam_giris,
            toplam_cikis=s.toplam_cikis,
        )
        for s in db.execute(sorgu).all()
    ]