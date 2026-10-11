"""Domain and business logic exceptions for CineBook."""


class BookingError(Exception):
    """Base exception for all booking-related errors."""
    pass


class SeatUnavailableError(BookingError):
    """Raised when one or more selected seats are already booked."""
    pass


class ShowInPastError(BookingError):
    """Raised when an action is attempted on a show that has already started."""
    pass


class InvalidSeatSelectionError(BookingError):
    """Raised when selected seats are invalid (e.g. wrong screen, > 6 seats, or empty)."""
    pass


class CancelWindowClosedError(BookingError):
    """Raised when cancellation is attempted within 1 hour of the showtime."""
    pass


class UnauthorizedBookingActionError(BookingError):
    """Raised when a user attempts to view or modify another user's booking."""
    pass
