"""
artist_hub/models.py
Expose tous les modèles des sous-modules pour la découverte automatique Django et les migrations.
"""
from artist_hub.payments.models import (
    Payment,
    PaymentStatus,
    PaymentMethod,
)
from artist_hub.casting.models import (
    CastingSession,
    Candidate,
    CandidatePhoto,
    CandidateStatus,
    CandidateGender,
    PhotoType,
)
from artist_hub.ticketing.models import (
    EventTicketCategory,
    TicketPurchase,
)
from artist_hub.booking.models import (
    BookingService,
    BookingRequest,
)

__all__ = [
    "Payment",
    "PaymentStatus",
    "PaymentMethod",
    "CastingSession",
    "Candidate",
    "CandidatePhoto",
    "CandidateStatus",
    "CandidateGender",
    "PhotoType",
    "EventTicketCategory",
    "TicketPurchase",
    "BookingService",
    "BookingRequest",
]
