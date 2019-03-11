import os
from enum import unique, Enum


#TODO move these to a settings.yml so they can be re-used in the serverless yml
# using https://serverless.com/framework/docs/providers/aws/guide/variables/#reference-variables-in-other-files

STAGE = os.environ['stage']

@unique
class People(Enum):
    """
    <configure-me>
    person1 = ('email1@email.com', phonenumber1)
    person2 = ('email2@email.com', phonenumber2)
    """


# order to mathc datetime.weekday()
MON, TUE, WED, THU, FRI, SAT, SUN = range(7)

# A mapping of People to be set to the user group for each day
# <configure-me>
WEEKDAY_ROTATION = {
    # Monday
    MON: [],
    # Tuesday
    TUE: [],
    # Wednesday
    WED: [],
    # Thursday
    THU: [],
    # Friday
    FRI: [],
}

# Rotates the oncall on weekends by pairs in the order of the People enum
ROTATE_WEEKEND_ONCALL = True

# The Slack @user-group to update (Default: oncall)
# If set to "oncall" it would be referenced via "@oncall" in slack
ALIAS_NAME = "oncall"

# timezone you want to use for schedule. This will be used to determine what day it is for the WEEKDAY_ROTATION
TIMEZONE = 'America/Los_Angeles'

# Number of days ahead to schedule calendar events
DAYS_AHEAD = 45

# Google Calendar ID (ex.- 'bloop.com_abcdef123456abc123@group.calendar.google.com'). Set to None to disable.
GOOGLE_CAL_ID = None

# sensitive vars loaded from env vars
try:
    SLACK_API_TOKEN = os.environ['SLACK_SMART_ALIAS_SLACK_API_TOKEN']
    GOOGLE_SERVICE_ACCOUNT_KEYFILE = os.environ['GOOGLE_SERVICE_ACCOUNT_KEYFILE']   # set to None to disable
except KeyError as e:
    raise Exception("Make sure all the required env vars are set! {} was missing".format(e.args[0]))
