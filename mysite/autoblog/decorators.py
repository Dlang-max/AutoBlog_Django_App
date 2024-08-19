def member_required(user):
    if user:
        return user.is_member
    return False

