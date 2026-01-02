from collections import defaultdict
from rules import is_available, ek_allowed

def generate_schedule(workers, shows):
    daily_assigned = defaultdict(set)
    fulfilled_wants = set()
    schedule_result = {}

    for show in shows:
        show_date = show.start.date()
        assigned_today = daily_assigned[show_date]
        schedule = {}

        for role in show.roles:
            schedule[role.name] = []
            ek_in_role = False

            # Először előadás kívánságos dolgozók
            if role.name == "Nézőtér beülős":
                for worker in sorted(workers, key=lambda w: (w.assigned_count, w.previous_roles.count(role.name))):
                    if len(schedule[role.name]) >= role.max_count:
                        break
                    if worker.name in assigned_today:
                        continue
                    if worker.wants_to_see != show.title:
                        continue
                    if worker.name in fulfilled_wants:
                        continue
                    if not is_available(worker, show.start):
                        continue
                    if not ek_allowed(worker, role, ek_in_role):
                        continue

                    schedule[role.name].append(worker.name)
                    assigned_today.add(worker.name)
                    worker.assigned_count += 1
                    fulfilled_wants.add(worker.name)
                    worker.previous_roles.append(role.name)
                    if worker.is_ek:
                        ek_in_role = True

            # Normál beosztás – rotáció és ÉK szabályok
            for worker in sorted(workers, key=lambda w: (w.assigned_count, w.previous_roles.count(role.name))):
                if len(schedule[role.name]) >= role.max_count:
                    break
                if worker.name in assigned_today:
                    continue
                if not is_available(worker, show.start):
                    continue
                if not ek_allowed(worker, role, ek_in_role):
                    continue
                schedule[role.name].append(worker.name)
                assigned_today.add(worker.name)
                worker.assigned_count += 1
                worker.previous_roles.append(role.name)
                if worker.is_ek:
                    ek_in_role = True

        schedule_result[f"{show.title} ({show.start.strftime('%Y-%m-%d %H:%M')})"] = schedule

    return schedule_result
