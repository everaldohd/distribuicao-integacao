from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.models.schedule_type import ScheduleType
from app.schemas.schedule_type import ScheduleTypeCreate, ScheduleTypeUpdate, ScheduleTypeOut
from app.routers.deps import get_current_manager
import uuid

router = APIRouter(prefix="/schedule-types", tags=["schedule-types"])


@router.get("/", response_model=List[ScheduleTypeOut])
def list_types(db: Session = Depends(get_db)):
    return db.query(ScheduleType).order_by(ScheduleType.display_order, ScheduleType.name).all()


@router.post("/", response_model=ScheduleTypeOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(get_current_manager)])
def create_type(data: ScheduleTypeCreate, db: Session = Depends(get_db)):
    if db.query(ScheduleType).filter(ScheduleType.name == data.name).first():
        raise HTTPException(status_code=400, detail="Tipo de escala já existe")
    st = ScheduleType(id=str(uuid.uuid4()), **data.model_dump())
    db.add(st)
    db.commit()
    db.refresh(st)
    return st


@router.put("/{type_id}", response_model=ScheduleTypeOut, dependencies=[Depends(get_current_manager)])
def update_type(type_id: str, data: ScheduleTypeUpdate, db: Session = Depends(get_db)):
    st = db.get(ScheduleType, type_id)
    if not st:
        raise HTTPException(status_code=404, detail="Tipo não encontrado")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(st, field, value)
    db.commit()
    db.refresh(st)
    return st
