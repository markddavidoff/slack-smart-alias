#!/usr/bin/env python
# Adapted from https://gist.github.com/devdazed/473ab227c323fb01838f
from __future__ import print_function
import dateutil.tz
import json
import logging
import math
import requests

from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient import discovery

import settings

# todo set this up with serverless
log = logging.getLogger(__name__)


class SlackOnCall(object):

    def __init__(self, slack_token,
                 slack_user_group_handle,
                 arn,
                 log_level='INFO',
                 keyfile=None,
                 gcal_id=None,
                 days_ahead=45):

        self.slack_token = slack_token
        self.slack_user_group_handle = slack_user_group_handle

        self._slack_user_group = None
        self._all_slack_users = None
        self.google_keyfile = json.loads(keyfile) if keyfile else None
        self.google_calendar_id = gcal_id
        self.arn = arn
        self.days_ahead = int(days_ahead)

        log.setLevel(log_level)

    def run(self):
        """
        Gets user group information and on-call information then updates the
        on-call user group in slack to be the on-call users
        """

        today = datetime.now(dateutil.tz.gettz(settings.TIMEZONE)).replace(hour=0, minute=0)

        weekday = today.weekday()
        weeknum = today.isocalendar()[1]

        oncalls = self.get_on_call_engs(weekday, weeknum)
        slack_users = self.slack_users_by_email(oncalls)
        if not slack_users:
            log.warning('No Slack users found for email addresses: {0}'.format(','.join(oncalls)))
            return

        if settings.GOOGLE_CAL_ID:
            # set on-call calendar event for the future
            the_future = today + timedelta(days=self.days_ahead)
            weekday = the_future.weekday()
            oncalls = self.get_on_call_engs(weekday, weeknum)
            if weekday < 6:
                self.set_calendar_event(oncalls, the_future)

        # update slack oncall
        slack_user_ids = [u['id'] for u in slack_users]
        if set(slack_user_ids) == set(self.slack_user_group['users']):
            log.info(f'User group {self.slack_user_group_handle} already set to {slack_user_ids}')
            return
        self.update_on_call(slack_users)

        log.info('Job Complete')

    def _make_request(self, url):
        response = requests.get(url, headers={'Authorization': f'Bearer {self.slack_token}'})
        return response.json()

    def backfill_calendar_events(self, start_date, num_days):
        """
        Do not run unless you are prepared for calendar spam. Do not start on a sunday since this assumes Saturday
        would have made Sunday's.  You will also need to increase the timeout to over a minute if num_days>=45.
        :param start_date:
        :param num_days:
        :return:
        """
        for x in range(num_days):
            the_day = start_date + timedelta(days=x)
            weekday = the_day.weekday()
            weeknum = the_day.isocalendar()[1]

            oncalls = self.get_on_call_engs(weekday, weeknum)
            if weekday < 6:
                self.set_calendar_event(oncalls, the_day)

    def set_calendar_event(self, users, start_date):
        credentials = service_account.Credentials.from_service_account_info(
            self.google_keyfile, scopes=['https://www.googleapis.com/auth/calendar'])

        service = discovery.build('calendar', 'v3', credentials=credentials)

        users_str = '/'.join([x.name for x in users])
        desc_str = ""

        weekday = start_date.weekday()

        if weekday == 5:
            end_date = start_date + timedelta(days=2)
        else:
            end_date = start_date + timedelta(days=1)

        attendees = []
        for user in users:
            attendees.append({'email': user.value.email})
            desc_str += f'{user.name} ({user.value.email}, {user.value.phone})\n'

        event = {
            "summary": f"On-Call {users_str}",
            "location": "Earth",
            "description": desc_str,
            "start": {
                "dateTime": start_date.strftime("%Y-%m-%dT00:00:00%z"),
                "timeZone": settings.TIMEZONE
            },
            "end": {
                "dateTime": end_date.strftime("%Y-%m-%dT00:00:00%z"),
                "timeZone": settings.TIMEZONE
            },
            "attendees": attendees
        }

        service.events().insert(calendarId=self.google_calendar_id, body=event).execute()

    @property
    def slack_user_group(self):
        """
        :return: the Slack user group matching the slack_user_group_handle
        specified in the configuration
        """
        if self._slack_user_group is not None:
            return self._slack_user_group

        url = 'https://slack.com/api/usergroups.list?include_users=1'
        groups = self._make_request(url)['usergroups']
        for group in groups:
            if group['handle'] == self.slack_user_group_handle:
                self._slack_user_group = group
                return group

        raise ValueError(f'No user groups found that match {self.slack_user_group_handle}')

    def get_on_call_engs(self, weekday, weeknum):
        """
        Uses WEEKDAY_ROTATION on weekdays, otherwise rotates the on-call in pairs
        based on the index stored in the last_oncall_index tag
        :return: All on-call email addresses
        """
        users = set()

        if not settings.ROTATE_WEEKEND_ONCALL or weekday < 5:
            oncalls = settings.WEEKDAY_ROTATION[weekday]
        else:   # set a param that stores the index of the last on-call
            eng_list = list(settings.People)
            oncall_index = weeknum % math.ceil(len(eng_list) / 2)
            oncalls = eng_list[oncall_index * 2:oncall_index * 2 + 2]

        for oncall in oncalls:
            users.add(oncall)

        log.info(f'Found {len(users)} users on-call')

        return users

    @property
    def all_slack_users(self):
        if self._all_slack_users is not None:
            return self._all_slack_users

        url = 'https://slack.com/api/users.list'
        users = self._make_request(url)['members']
        log.info(f'Found {len(users)} total Slack users')
        self._all_slack_users = users
        return users

    def slack_users_by_email(self, engs):
        """
        Finds all slack users by their email address
        :param emails: List of email address to find users
        :return: List of Slack user objects found in :emails:
        """
        users = []
        emails = set([x.value.email for x in engs])
        for user in self.all_slack_users:
            if user['profile'].get('email') in emails:
                users.append(user)

        return users

    def update_on_call(self, slack_users):
        """
        Updates the specified user-group
        :param slack_users: Slack users to modify the group with
        """
        user_ids = [u['id'] for u in slack_users]
        url = 'https://slack.com/api/usergroups.users.update?usergroup={0}&users={1}'.format(
            self.slack_user_group['id'], ','.join(user_ids))

        log.info(
            'Updating user group {0} from {1} to {2}'.format(self.slack_user_group_handle,
                                                             self.slack_user_group['users'],
                                                             user_ids))
        self._make_request(url)


def handler(_event, context):
    """
    Main entry point for AWS Lambda.
    """
    return SlackOnCall(slack_token=settings.SLACK_API_TOKEN,
                       slack_user_group_handle=settings.ALIAS_NAME,
                       arn=context.invoked_function_arn,
                       keyfile=settings.GOOGLE_SERVICE_ACCOUNT_KEYFILE,
                       gcal_id=settings.GOOGLE_CAL_ID,
                       days_ahead=settings.DAYS_AHEAD).run()

