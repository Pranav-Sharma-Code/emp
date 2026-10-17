from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db
from models.enums import UserRole


def update_profile(user, form):
    """Edit contact details and (optionally) the password.

    Returns (ok, message). Nothing is changed unless every check passes.
    """
    name = form.get("name", "").strip()
    phone = form.get("phone", "").strip()
    if not name or len(name) > 100:
        return False, "Enter a name (up to 100 characters)"
    if len(phone) > 20:
        return False, "The phone number is too long"

    department = user.department
    if user.role == UserRole.Examiner:
        department = form.get("department", "").strip()
        if not department or len(department) > 100:
            return False, "Enter your department"

    new_password = form.get("new_password", "")
    if new_password:
        if not check_password_hash(user.password, form.get("current_password", "")):
            return False, "Your current password is wrong"
        if len(new_password) < 6:
            return False, "The new password must be at least 6 characters"
        if new_password != form.get("confirm_password", ""):
            return False, "The new passwords do not match"

    user.name = name
    user.phone = phone or None
    if user.role == UserRole.Examiner:
        user.department = department
    if new_password:
        user.password = generate_password_hash(new_password)
    db.session.commit()
    return True, "Profile updated"
