"""
Travel & Logistics Planner modelleri.

Uçuş, otel, transfer, vize, gezi planı,
fiyat uyarı, belge, harcama modelleri.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class TransportType(str, Enum):
    """Ulaşım türleri."""

    flight = "flight"
    train = "train"
    bus = "bus"
    car_rental = "car_rental"
    taxi = "taxi"
    shuttle = "shuttle"


class BookingStatus(str, Enum):
    """Rezervasyon durumları."""

    pending = "pending"
    confirmed = "confirmed"
    cancelled = "cancelled"
    completed = "completed"
    refunded = "refunded"
    waitlisted = "waitlisted"


class VisaStatus(str, Enum):
    """Vize durumları."""

    not_required = "not_required"
    required = "required"
    applied = "applied"
    approved = "approved"
    denied = "denied"


class ExpenseCategory(str, Enum):
    """Harcama kategorileri."""

    flight = "flight"
    hotel = "hotel"
    transport = "transport"
    food = "food"
    activity = "activity"
    shopping = "shopping"
    insurance = "insurance"
    other = "other"


class DocumentType(str, Enum):
    """Belge türleri."""

    passport = "passport"
    visa = "visa"
    insurance = "insurance"
    booking = "booking"
    ticket = "ticket"
    receipt = "receipt"


class HotelRating(str, Enum):
    """Otel derecelendirme."""

    budget = "budget"
    standard = "standard"
    comfort = "comfort"
    premium = "premium"
    luxury = "luxury"


class FlightRecord(BaseModel):
    """Uçuş kaydı."""

    flight_id: str = Field(
        default_factory=lambda: str(uuid4())[:8]
    )
    origin: str = ""
    destination: str = ""
    price: float = 0.0
    status: str = "pending"
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )


class HotelRecord(BaseModel):
    """Otel kaydı."""

    hotel_id: str = Field(
        default_factory=lambda: str(uuid4())[:8]
    )
    name: str = ""
    city: str = ""
    price_per_night: float = 0.0
    rating: float = 0.0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )


class ItineraryRecord(BaseModel):
    """Gezi planı kaydı."""

    itinerary_id: str = Field(
        default_factory=lambda: str(uuid4())[:8]
    )
    destination: str = ""
    days: int = 1
    status: str = "draft"
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )


class TravelExpenseRecord(BaseModel):
    """Seyahat harcama kaydı."""

    expense_id: str = Field(
        default_factory=lambda: str(uuid4())[:8]
    )
    category: str = "other"
    amount: float = 0.0
    currency: str = "USD"
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )
