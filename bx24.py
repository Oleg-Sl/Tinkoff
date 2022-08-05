#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import time
from requests import adapters, post, exceptions

from service import get_secrets_all_bx24, update_secrets_bx24


adapters.DEFAULT_RETRIES = 10


class Bitrix24:
    api_url = 'https://{domain}/rest/{method}.json'
    oauth_url = 'https://oauth.bitrix.info/oauth/token/'
    timeout = 60

    def __init__(self):
        tokens = get_secrets_all_bx24()
        self.domain = tokens.get("domain", None)
        self.auth_token = tokens.get("auth_token", None)
        self.refresh_token = tokens.get("refresh_token", None)
        self.client_id = tokens.get("client_id")
        self.client_secret = tokens.get("client_secret")

    def refresh_tokens(self):
        r = {}
        try:
            r = post(
                self.oauth_url,
                params={'grant_type': 'refresh_token', 'client_id': self.client_id, 'client_secret': self.client_secret,
                        'refresh_token': self.refresh_token})
            result = json.loads(r.text)

            self.auth_token = result['access_token']
            self.refresh_token = result['refresh_token']
            self.expires_in = result['expires_in']
            update_secrets_bx24(self.auth_token, self.expires_in, self.refresh_token)
            return True
        except (ValueError, KeyError):
            result = dict(error='Error on decode oauth response [%s]' % r.text)
            return result

    def call(self, method, data):
        try:
            url = self.api_url.format(domain=self.domain, method=method)
            # url += '?auth=' + self.auth_token
            params = dict(auth=self.auth_token)
            headers = {
                'Content-Type': 'application/json',
            }
            r = post(url, data=json.dumps(data), params=params, headers=headers, timeout=self.timeout)
            result = json.loads(r.text)
        except ValueError:
            result = dict(error=f'Error on decode api response [{r.text}]')
        except exceptions.ReadTimeout:
            result = dict(error=f'Timeout waiting expired [{str(self.timeout)} sec]')
        except exceptions.ConnectionError:
            result = dict(error=f'Max retries exceeded [{str(adapters.DEFAULT_RETRIES)}]')

        if 'error' in result and result['error'] in ('NO_AUTH_FOUND', 'expired_token'):
            result_update_token = self.refresh_tokens()
            if result_update_token is not True:
                return result
            result = self.call(method, data)
        elif 'error' in result and result['error'] in ['QUERY_LIMIT_EXCEEDED', ]:
            time.sleep(2)
            return self.call(method, data)

        return result

    def batch(self, params):
        if 'halt' not in params or 'cmd' not in params:
            return dict(error='Invalid batch structure')

        return self.call(params)



