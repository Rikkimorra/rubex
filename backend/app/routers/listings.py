from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import Listing, ListingDirection, ListingStatus, TAB_RANGES, User, amount_to_tab
from app.schemas import ListingCreate, ListingOut

router = APIRouter(prefix="/api/listings", tags=["listings"])


def _to_out(listing: Listing, viewer_subscribed: bool) -> ListingOut:
    locked = not viewer_subscribed
    return ListingOut(
        id=listing.id,
        direction=listing.direction,
        amount_rub=listing.amount_rub,
        tab=listing.tab,
        details=listing.details,
        created_at=listing.created_at,
        author_username=(None if locked else listing.user.username),
        author_first_name=(None if locked else listing.user.first_name),
        contact_locked=locked,
    )


@router.get("", response_model=list[ListingOut])
def list_listings(
    tab: str = Query(..., description=f"Одно из: {', '.join(TAB_RANGES)}"),
    direction: ListingDirection | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if tab not in TAB_RANGES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"tab must be one of {TAB_RANGES}")

    q = db.query(Listing).filter(Listing.tab == tab, Listing.status == ListingStatus.ACTIVE)
    if direction is not None:
        q = q.filter(Listing.direction == direction)
    q = q.order_by(desc(Listing.created_at)).limit(200)

    return [_to_out(l, user.is_subscribed) for l in q.all()]


@router.post("", response_model=ListingOut, status_code=status.HTTP_201_CREATED)
def create_listing(
    payload: ListingCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not user.is_subscribed:
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            "Для размещения объявления нужна активная подписка",
        )

    listing = Listing(
        user_id=user.id,
        direction=payload.direction,
        amount_rub=payload.amount_rub,
        tab=amount_to_tab(payload.amount_rub),
        details=payload.details,
    )
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return _to_out(listing, viewer_subscribed=True)


@router.get("/mine", response_model=list[ListingOut])
def my_listings(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = (
        db.query(Listing)
        .filter(Listing.user_id == user.id, Listing.status == ListingStatus.ACTIVE)
        .order_by(desc(Listing.created_at))
    )
    return [_to_out(l, viewer_subscribed=True) for l in q.all()]


@router.delete("/{listing_id}", status_code=status.HTTP_204_NO_CONTENT)
def close_listing(listing_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    listing = db.get(Listing, listing_id)
    if listing is None or listing.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Listing not found")
    listing.status = ListingStatus.CLOSED
    db.commit()
    return None
