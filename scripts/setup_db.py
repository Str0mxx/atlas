"""ATLAS veritabani kurulum scripti.

Veritabani baglantisini kontrol eder, tablolari olusturur
ve isteye bagli olarak ornek veri yukler.

Kullanim:
    python -m scripts.setup_db --check     # Sadece baglanti kontrolu
    python -m scripts.setup_db --migrate   # Tablolari olustur
    python -m scripts.setup_db --seed      # Ornek veri yukle
    python -m scripts.setup_db --all       # Hepsini calistir
"""

import argparse
import asyncio
import logging
import sys

from app.core.database import close_db, create_tables, init_db

logger = logging.getLogger("atlas.scripts.setup_db")


async def check_connection() -> bool:
    """Veritabani baglantisini test eder.

    Returns:
        Baglanti basarili ise True.
    """
    try:
        await init_db()
        logger.info("Veritabani baglantisi basarili")
        await close_db()
        return True
    except Exception as exc:
        logger.error("Veritabani baglantisi basarisiz: %s", exc)
        return False


async def run_migrations() -> None:
    """Veritabani tablolarini olusturur.

    Gelistirme ortaminda create_tables kullanir.
    Production'da alembic upgrade head kullanilmali.
    """
    await init_db()
    try:
        await create_tables()
        logger.info("Veritabani tablolari olusturuldu")
    finally:
        await close_db()


async def run_seed() -> None:
    """Ornek veri yukler.

    scripts.seed_data modulundeki seed_all fonksiyonunu calistirir.
    """
    from scripts.seed_data import seed_all

    await seed_all()
    logger.info("Ornek veriler yuklendi")


async def main(args: argparse.Namespace) -> None:
    """Ana calisma fonksiyonu.

    Args:
        args: CLI argumanlari.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    )

    if args.all or args.check:
        success = await check_connection()
        if not success:
            logger.error("Baglanti kontrolu basarisiz, cikiliyor")
            sys.exit(1)

    if args.all or args.migrate:
        await run_migrations()

    if args.all or args.seed:
        await run_seed()

    if not (args.all or args.check or args.migrate or args.seed):
        logger.warning("Hicbir islem secilmedi. --help ile kullanimi gorun.")


def cli() -> None:
    """CLI giris noktasi."""
    parser = argparse.ArgumentParser(
        description="ATLAS veritabani kurulum scripti",
    )
    parser.add_argument(
        "--check", action="store_true",
        help="Veritabani baglantisini kontrol et",
    )
    parser.add_argument(
        "--migrate", action="store_true",
        help="Tablolari olustur",
    )
    parser.add_argument(
        "--seed", action="store_true",
        help="Ornek veri yukle",
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Tum islemleri calistir (check + migrate + seed)",
    )
    args = parser.parse_args()
    asyncio.run(main(args))


if __name__ == "__main__":
    cli()
