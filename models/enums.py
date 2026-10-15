import enum

class UserRole(enum.Enum):
    Admin = "admin"
    Student = "Student"
    Examiner = "Examiner"


class UserStatus(enum.Enum):
    Active = "active"
    Pending = "pending"
    Rejected = "rejected"
    Inactive = "inactive"


class Examtype(enum.Enum):
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


class SlotsStatus(enum.Enum):
    Available = "available"
    Full = "full"
    Cancelled = "cancelled"
    Completed = "completed"


class BookingStatus(enum.Enum):
    Booked = "booked"
    Cancelled = "cancelled"
    Completed = "completed"
