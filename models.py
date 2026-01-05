class Worker:
    def __init__(self, name, wants_to_see=None, is_ek=False):
        self.name = name
        self.wants_to_see = wants_to_see
        self.is_ek = is_ek
        self.assigned_count = 0
        self.previous_roles = []
        self.unavailable_dates = []

class Role:
    def __init__(self, name, max_count, ek_allowed=True):
        self.name = name
        self.max_count = max_count
        self.ek_allowed = ek_allowed

class Show:
    def __init__(self, title, start, roles):
        self.title = title
        self.start = start
        self.roles = roles
