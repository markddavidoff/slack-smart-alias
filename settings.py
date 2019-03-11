import os
from enum import unique, Enum

ARN_ID = "arn:aws:lambda:us-west-1:<your lambda id>:function:update-slack-oncall"

#TODO move these to a settings.yml so they can be re-used in the serverless yml
# using https://serverless.com/framework/docs/providers/aws/guide/variables/#reference-variables-in-other-files


@unique
class People(Enum):
    """
    <configure-me>
    person1 = 'email1@email.com'
    person2 = 'email2@email.com'
    """


# order to mathc datetime.weekday()
MON, TUE, WED, THU, FRI, SAT, SUN = range(7)


# The Slack @user-group to update (Default: oncall)
# If set to "oncall" it would be referenced via "@oncall" in slack
ALIAS_NAME = "oncall"


# A mapping of People to be set to the user group for each day
# <configure-me>
WEEKDAY_ROTATION = {
    # Monday
    MON: [],  # [People.person1, People.person2],
    # Tuesday
    TUE: [],
    # Wednesday
    WED: [],
    # Thursday
    THU: [],
    # Friday
    FRI: [],
}

# timezone you want to use for schedule. This will be used to determine what day it is for the WEEKDAY_ROTATION
TIMEZONE = 'US/Pacific'

# sensitive vars loaded from env vars
try:
    SLACK_API_TOKEN = os.environ['SLACK_SMART_ALIAS_SLACK_API_TOKEN']
except KeyError as e:
    raise Exception("Make sure all the required env vars are set! {} was missing".format(e.args[0]))
