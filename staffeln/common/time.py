import re
from datetime import datetime
from dateutil.relativedelta import relativedelta

regex = re.compile(
    r'((?P<years>\d+?)y)?((?P<months>\d+?)m)?((?P<weeks>\d+?)w)?((?P<days>\d+?)d)?'
)


# parse_time parses timedelta string to time dict
# input: <string> 1y2m3w5d - all values should be integer
# output: <dict> {year: 1, month: 2, week: 3, day: 5}
def parse_timedelta_string(time_str):
    empty_flag = True
    try:
        parts = regex.match(time_str)
        if not parts:
            return None
        parts = parts.groupdict()
        time_params = {}
        for key in parts:
            if parts[key]:
                time_params[key] = int(parts[key])
                empty_flag = False
            else:
                time_params[key] = 0
        if empty_flag: return None
        return time_params
    except:
        return None


def timeago(years, months, weeks, days, from_date=None):
    if from_date is None:
        from_date = datetime.now()
    return from_date - relativedelta(years=years, months=months, weeks=weeks, days=days)

## yearsago using Standard library
# def yearsago(years, from_date=None):
#     if from_date is None:
#         from_date = datetime.now()
#     try:
#         return from_date.replace(year=from_date.year - years)
#     except ValueError:
#         # Must be 2/29!
#         assert from_date.month == 2 and from_date.day == 29 # can be removed
#         return from_date.replace(month=2, day=28,
#                                  year=from_date.year-years)
