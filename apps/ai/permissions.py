def user_in_ai_group(user) -> bool:
    if not getattr(user, "is_authenticated", False):
        return False
    return user.groups.filter(name="ai").exists()
