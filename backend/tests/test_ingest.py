from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import Laptop
from ingest import run_ingestion

CSV_HEADER = (
    "unnamed:_0,brand,name,processor_name,processor_brand,ram_expandable,ram,ram_type,ghz,"
    "display_type,display,gpu,gpu_brand,ssd,hdd,adapter,battery_life,ram_gb,storage_gb,"
    "screen_size_inches,has_dedicated_gpu,os\n"
)

SAMPLE_ROWS = [
    # normal row
    '0,HP,"HP Chromebook 11A::585119::computer::laptops",MediaTek Octa-core,MediaTek,Not Expandable,'
    '"4 GB ", DDR4 RAM, 2.0 Ghz Processor,LED,11.6 ,Integrated Graphics,MediaTek,64 GB SSD Storage,'
    'No HDD,45, Upto 12 Hrs Battery Life,4,64,11.6,False,ChromeOS',
    # exact duplicate of the row above (same `name`) -> should be dropped
    '0,HP,"HP Chromebook 11A::585119::computer::laptops",MediaTek Octa-core,MediaTek,Not Expandable,'
    '"4 GB ", DDR4 RAM, 2.0 Ghz Processor,LED,11.6 ,Integrated Graphics,MediaTek,64 GB SSD Storage,'
    'No HDD,45, Upto 12 Hrs Battery Life,4,64,11.6,False,ChromeOS',
    # corrupted processor_brand (real-world bug: brand holds the ghz value)
    '1,Apple,"Apple MacBook Pro M1 Pro::597798::computer::laptops",Apple M1 Pro,2.3,32 GB Expandable,'
    '"16 GB ", LPDDR5 RAM, 0,LED,14.2 ,Integrated Graphics,Apple,1024 GB SSD Storage,'
    'No HDD,96, Upto 17 Hrs Battery Life,16,1024,14.2,False,macOS',
    # battery_life field polluted with adapter wattage text
    '2,Dell,"Dell G15::595299::computer::laptops",Intel Core i5 (12th Gen),Intel, 32 GB Expandable,'
    '"16 GB ", DDR5 RAM, 3.3 Ghz Processor,LCD,15.6 ,"GeForce RTX 3050 GPU, 4 GB",NVIDIA,'
    '512 GB SSD Storage,No HDD,56,45W Adapter,16,512,15.6,True,Windows',
]


def write_sample_csv(path: Path) -> Path:
    csv_path = path / "sample.csv"
    csv_path.write_text(CSV_HEADER + "\n".join(SAMPLE_ROWS) + "\n")
    return csv_path


def test_run_ingestion_dedupes_cleans_and_loads(tmp_path):
    csv_path = write_sample_csv(tmp_path)
    db_url = f"sqlite:///{tmp_path / 'test.db'}"

    run_ingestion(csv_path=csv_path, db_url=db_url, append=False)

    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        rows = session.query(Laptop).order_by(Laptop.id).all()
    finally:
        session.close()

    # 4 source rows, 1 exact duplicate dropped -> 3 laptops
    assert len(rows) == 3

    chromebook = next(r for r in rows if r.brand == "HP")
    assert chromebook.model_name == "HP Chromebook 11A"
    assert chromebook.battery_life_hours == 12.0

    macbook = next(r for r in rows if r.brand == "Apple")
    assert macbook.processor_brand == "Apple"
    assert macbook.cpu_ghz == 2.3  # recovered from the corrupted processor_brand field

    dell = next(r for r in rows if r.brand == "Dell")
    assert dell.gpu_name == "GeForce RTX 3050"
    assert dell.gpu_vram_gb == 4.0
    assert dell.battery_life_hours is None  # "45W Adapter" is not a valid hours value
    assert dell.baseline_price is None


def test_run_ingestion_skips_rows_that_fail_validation(tmp_path):
    bad_row = (
        # ram_gb=0 violates LaptopIngestRecord's ge=1 constraint
        '3,Acer,"Acer Bad Laptop::600000::computer::laptops",Intel Core i3 (11th Gen),Intel, Not Expandable,'
        '"0 GB ", DDR4 RAM, 2.0 Ghz Processor,LED,15.6 ,Integrated Graphics,Intel,256 GB SSD Storage,'
        'No HDD,45, Upto 8 Hrs Battery Life,0,256,15.6,False,Windows'
    )
    csv_path = tmp_path / "sample_with_bad_row.csv"
    csv_path.write_text(CSV_HEADER + "\n".join([*SAMPLE_ROWS, bad_row]) + "\n")
    db_url = f"sqlite:///{tmp_path / 'test.db'}"

    run_ingestion(csv_path=csv_path, db_url=db_url, append=False)

    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        count = session.query(Laptop).count()
        acer = session.query(Laptop).filter_by(brand="Acer").first()
    finally:
        session.close()

    assert count == 3  # bad row excluded, valid 3 still loaded
    assert acer is None


def test_run_ingestion_append_mode_skips_existing_and_adds_new(tmp_path):
    db_url = f"sqlite:///{tmp_path / 'test.db'}"

    first_csv = write_sample_csv(tmp_path)
    run_ingestion(csv_path=first_csv, db_url=db_url, append=False)

    new_row = (
        '9,Asus,"Asus Zenbook New::611111::computer::laptops",Intel Core i7 (13th Gen),Intel, 16 GB Expandable,'
        '"16 GB ", LPDDR5 RAM, 2.8 Ghz Processor,OLED,14 ,Iris Xe,Intel,1024 GB SSD Storage,'
        'No HDD,65, Upto 14 Hrs Battery Life,16,1024,14.0,False,Windows'
    )
    second_csv = tmp_path / "second.csv"
    second_csv.write_text(CSV_HEADER + "\n".join([*SAMPLE_ROWS, new_row]) + "\n")

    run_ingestion(csv_path=second_csv, db_url=db_url, append=True)

    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        count = session.query(Laptop).count()
        asus = session.query(Laptop).filter_by(brand="Asus").first()
    finally:
        session.close()

    # 3 original laptops (untouched, not duplicated) + 1 genuinely new one
    assert count == 4
    assert asus is not None
    assert asus.model_name == "Asus Zenbook New"


def test_run_ingestion_is_idempotent_on_rerun(tmp_path):
    csv_path = write_sample_csv(tmp_path)
    db_url = f"sqlite:///{tmp_path / 'test.db'}"

    run_ingestion(csv_path=csv_path, db_url=db_url, append=False)
    run_ingestion(csv_path=csv_path, db_url=db_url, append=False)  # drop + reload again

    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        count = session.query(Laptop).count()
    finally:
        session.close()

    assert count == 3
