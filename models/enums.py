import enum

from sqlalchemy import Enum


def sa_enum(enum_class):
    return Enum(enum_class, values_callable=lambda e: [m.value for m in e])


class UserRole(enum.Enum):
    Admin = "admin"
    Student = "student"
    Examiner = "examiner"


class UserStatus(enum.Enum):
    Active = "active"
    Pending = "pending"
    Rejected = "rejected"
    Inactive = "inactive"


class ExamType(enum.Enum):
    Viva = "viva"
    Practical = "practical"
    Project = "project"
    Assessment = "assessment"


class ExamState(enum.Enum):
    Draft = "draft"
    SlotCreation = "slotcreation"
    BookingOpen = "bookingopen"
    Closed = "closed"
    Completed = "completed"


class SlotStatus(enum.Enum):
    Available = "available"
    Full = "full"
    Cancelled = "cancelled"
    Completed = "completed"


class BookingStatus(enum.Enum):
    Booked = "booked"
    Cancelled = "cancelled"
    Completed = "completed"


class EvaluationStatus(enum.Enum):
    Draft = "draft"
    Submitted = "submitted"
