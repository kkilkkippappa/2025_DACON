from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.DB.config import get_db
from app.DB.table_sensor import Sensor, SensorDTO

router = APIRouter(prefix="/db", tags=["database"])


@router.get("/")
def read_root():
    """Simple health endpoint for the DB router."""
    return {"message": "Welcome to the db!"}


@router.get("/sensors")
def list_sensors(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Fetch sensor rows ordered by timestamp with pagination."""
    try:
        sensors = (
            db.query(Sensor).order_by(Sensor.date_time.desc()).offset(offset).limit(limit).all()
        )
        return jsonable_encoder([SensorDTO.model_validate(s) for s in sensors])
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error while listing sensors: {exc.__class__.__name__}",
        ) from exc


@router.get("/sensors/{sensor_id}")
def get_sensor(sensor_id: int, db: Session = Depends(get_db)):
    """Retrieve a single sensor record by primary key."""
    sensor = db.query(Sensor).filter(Sensor.id == sensor_id).first()
    if not sensor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sensor not found")
    return jsonable_encoder(SensorDTO.model_validate(sensor))


@router.post("/sensors", status_code=status.HTTP_201_CREATED)
def create_sensor(payload: SensorDTO, db: Session = Depends(get_db)):
    """Insert a new sensor record with validation and error handling."""
    sensor_data = payload.model_dump(exclude_unset=True, exclude={"id"})
    if "date_time" not in sensor_data:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="date_time is required")

    sensor = Sensor(**sensor_data)
    try:
        db.add(sensor)
        db.commit()
        db.refresh(sensor)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to insert sensor due to constraint violation",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error while inserting sensor: {exc.__class__.__name__}",
        ) from exc

    return jsonable_encoder(SensorDTO.model_validate(sensor))
