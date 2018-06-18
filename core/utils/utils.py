def next_month(selected_date):
    year, month = selected_date
    month += 1
    if month > 12:
        month = 1
        year += 1
    date = (year, month)
    return date


def previous_month(selected_date):
    year, month = selected_date
    month -= 1
    if month < 1:
        month = 12
        year -= 1
    date = (year, month)
    return date