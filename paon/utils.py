import datetime

def tmdb_date_to_date(str):
    d = datetime.datetime.strptime(str, '%Y-%m-%d')
    return d.date()

