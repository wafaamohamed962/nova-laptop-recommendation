from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class PriceListing(BaseModel):
    """One normalized SerpApi Google Shopping result for a laptop."""

    title: Optional[str] = None
    seller: str
    price: Optional[float] = None
    currency: str = "USD"
    rating: Optional[float] = None
    reviews_count: Optional[int] = None
    product_link: Optional[str] = None


class LivePriceResult(BaseModel):
    """Live pricing lookup outcome for one of Phase 4's top-matched laptops."""

    laptop_id: Optional[int]
    brand: str
    model_name: str
    query: str
    listings: list[PriceListing] = Field(default_factory=list)
    fetched_at: datetime
    from_cache: bool = False
    error: Optional[str] = None
