#!/usr/bin/env python
# Adapted from https://gist.github.com/devdazed/473ab227c323fb01838f
import json
import logging
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
import dateutil.tz

import boto3


import settings

# todo set this up with serverless
log = logging.getLogger(__name__)


class SlackOnCall(object):

    def __init__(self,
                 slack_token,
                 slack_user_group_handle,
                 log_level='INFO'):
       
        self.slack_token = slack_token
        self.slack_user_group_handle = slack_user_group_handle

        self._slack_user_group = None
        self._on_call_email_addresses = None
        self._all_slack_users = None

        log.setLevel(log_level)

    def run(self):
        """
        Gets user group information and on-call information then updates the
        on-call user group in slack to be the on-call users
        """

        slack_users = self.slack_users_by_email(self.on_call_email_addresses)
        if not slack_users:
            log.warning('No Slack users found for email addresses: %s', ','.join(self.on_call_email_addresses))
            return

        slack_user_ids = [u['id'] for u in slack_users]

        if set(slack_user_ids) == set(self.slack_user_group['users']):
            log.info('User group %s already set to %s', self.slack_user_group_handle, slack_user_ids)
            return

        self.update_on_call(slack_users)
        log.info('Job Complete')

    def _make_request(self, url, body=None, headers={}):
        #  TODO: now that we have serverless we can re-write this archaic dodo with requests
        headers['Authorization'] = f'Bearer {self.slack_token}'
        req = Request(url, body, headers)
        log.info('Making request to %s', url)

        try:
            response = urlopen(req)
            body = response.read()
            try:
                return json.loads(body)
            except ValueError:
                return body

        except HTTPError as e:
            log.error("Request failed: %d %s", e.code, e.reason)
        except URLError as e:
            log.error("Server connection failed: %s", e.reason)

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

        raise ValueError('No user groups found that match {}'.format(self.slack_user_group_handle))

    @property
    def on_call_email_addresses(self):
        # todo rename oncall to in_rotation
        """
        Uses WEEKDAY_ROTATION on weekdays, otherwise uses the week number
        based on the index stored in the last_oncall_index tag
        :return: All on-call email addresses
        """
        if self._on_call_email_addresses is not None:
            return self._on_call_email_addresses

        users = set()  # users can be in multiple schedule, this will de-dupe

        today = datetime.now(dateutil.tz.gettz(settings.TIMEZONE))
        weekday = today.weekday()  # Monday is 0 and Sunday is 6

        if weekday < 5:
            people_in_rotation = settings.WEEKDAY_ROTATION[weekday]
        else:
            week_num = today.isocalendar()[1]
            people_in_rotation = settings.WEEKDAY_ROTATION[week_num % len(settings.WEEKDAY_ROTATION)]

            # todo what does this do again? this is some fancy stuff for weekends? turning it off for now...
            # day_of_month = today.day
            # eng_list = list(Engineers)
            # client = boto3.client('lambda')
            # tags = client.list_tags(
            #     Resource=ARN_ID
            # )
            # oncall_index = int(tags['Tags']['last_oncall_index']) # int((day_of_month-1)/7)
            # oncall_index = oncall_index % math.ceil(len(eng_list)/2)
            # client.tag_resource(Resource=ARN_ID,
            #             Tags={'last_oncall_index': str(oncall_index + 1)}
            # )
            #
            # oncalls = eng_list[oncall_index*2:oncall_index*2+2]
            
        for peep in people_in_rotation:
            users.add(peep.value)

        log.info('Found %d users on-call', len(users))
        self._on_call_email_addresses = users
        return users

    @property
    def all_slack_users(self):
        # todo: make this a model we can use so we don't have to check the slack docs all the time
        if self._all_slack_users is not None:
            return self._all_slack_users

        url = 'https://slack.com/api/users.list'
        users = self._make_request(url)['members']
        log.info('Found %d total Slack users', len(users))
        self._all_slack_users = users
        return users

    def slack_users_by_email(self, emails):
        """
        Finds all slack users by their email address
        :param emails: List of email address to find users
        :return: List of Slack user objects found in :emails:
        """
        users = []
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
            self.slack_user_group['id'],
            ','.join(user_ids)
        )

        log.info('Updating user group %s from %s to %s',
                 self.slack_user_group_handle, self.slack_user_group['users'], user_ids)
        self._make_request(url)


def handler(event, context):

    return SlackOnCall(
        slack_token=settings.SLACK_API_TOKEN,
        slack_user_group_handle=settings.ALIAS_NAME
    ).run()
