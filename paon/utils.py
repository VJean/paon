import datetime


def tmdb_date_to_date(datestr):
    d = datetime.datetime.strptime(datestr, '%Y-%m-%d')
    return d.date()
