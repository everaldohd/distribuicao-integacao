from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.security import hash_password
from app.models.user import User
from app.models.historical_balance import HistoricalBalance
from app.schemas.user import UserCreate, UserUpdate, UserOut, UserPasswordChange
from app.routers.deps import get_current_user, get_current_manager
from app.services.balance import compute_new_user_initial_balance
import uuid

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/me/password")
def change_password(
    data: UserPasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.core.security import verify_password
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Senha atual incorreta")
    current_user.hashed_password = hash_password(data.new_password)
    db.commit()
    return {"message": "Senha alterada com sucesso"}


# --- Manager endpoints ---

@router.get("/", response_model=List[UserOut], dependencies=[Depends(get_current_manager)])
def list_users(db: Session = Depends(get_db)):
    return db.query(User).order_by(User.name).all()


@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    data: UserCreate,
    db: Session = Depends(get_db),
    manager: User = Depends(get_current_manager),
):
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")

    initial_balance = compute_new_user_initial_balance(db)

    user = User(
        id=str(uuid.uuid4()),
        name=data.name,
        email=data.email,
        hashed_password=hash_password(data.password),
        is_manager=data.is_manager,
        profile_id=data.profile_id,
    )
    db.add(user)
    db.flush()  # get user.id

    # Saldo inicial = média dos usuários ativos
    if initial_balance is not None:
        balance_entry = HistoricalBalance(
            user_id=user.id,
            year=0,
            month=0,
            delta=initial_balance,
            cumulative_balance=initial_balance,
        )
        db.add(balance_entry)

    db.commit()
    db.refresh(user)
    return user


@router.get("/{user_id}", response_model=UserOut, dependencies=[Depends(get_current_manager)])
def get_user(user_id: str, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return user


@router.put("/{user_id}", response_model=UserOut)
def update_user(
    user_id: str,
    data: UserUpdate,
    db: Session = Depends(get_db),
    manager: User = Depends(get_current_manager),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user
