from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.security import validate_init_data, InitDataError


def get_current_user(
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
) -> User:
    """
    Ожидает заголовок:  Authorization: tma <initData>
    где <initData> — строка window.Telegram.WebApp.initData из фронтенда.
    """
    if not authorization:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing Authorization header")

    parts = authorization.split(" ", 1)
    init_data = parts[1] if len(parts) == 2 else parts[0]

    try:
        data = validate_init_data(init_data)
    except InitDataError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Invalid Telegram auth: {e}")

    tg_user = data.get("user")
    if not tg_user or "id" not in tg_user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "No user in initData")

    user = db.get(User, tg_user["id"])
    if user is None:
        user = User(
            id=tg_user["id"],
            username=tg_user.get("username"),
            first_name=tg_user.get("first_name"),
            last_name=tg_user.get("last_name"),
        )
        db.add(user)
    else:
        user.username = tg_user.get("username")
        user.first_name = tg_user.get("first_name")
        user.last_name = tg_user.get("last_name")

    db.commit()
    db.refresh(user)
    return user
