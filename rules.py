def is_available(worker, show_datetime):
    for entry in worker.unavailable_dates:

        # időintervallum (start, end)
        if isinstance(entry, tuple):
            start, end = entry
            if start <= show_datetime <= end:
                return False

        # csak dátum
        else:
            if entry == show_datetime.date():
                return False

    return True


def ek_allowed(worker, role, ek_in_role):
    if worker.is_ek and role.name == "Jolly joker":
        return False
    if worker.is_ek and ek_in_role:
        return False
    return True
