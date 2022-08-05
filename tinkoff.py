#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests
import json
import time


requests.adapters.DEFAULT_RETRIES = 10


class TinkoffApi:
    api_url = 'https://business.tinkoff.ru/openapi{method}'
    timeout = 60

    def __init__(self, account_number, auth_token):
        self.account_number = account_number
        self.auth_token = auth_token

    def execute_get_request(self, method, params, count_repeat_req=5):
        status_code = None
        try:
            url = self.api_url.format(method=method)
            headers = {
                'Authorization': f'Bearer {self.auth_token}',
                'Content-Type': 'application/json',
            }
            r = requests.get(url, headers=headers, params=params, timeout=self.timeout)
            status_code = r.status_code
            result = json.loads(r.text)
        except TypeError:
            result = dict(errorMessage=f'Error while deserializing API response [{str(r.text)}]')
        except ValueError:
            result = dict(errorMessage=f'Error on decode API response [{r.text}]')
        except requests.exceptions.ReadTimeout:
            result = dict(errorMessage=f'Timeout waiting expired [{str(self.timeout)} sec]')
        except requests.exceptions.ConnectionError:
            result = dict(errorMessage=f'Max retries exceeded [{str(requests.adapters.DEFAULT_RETRIES)}]')

        if status_code == 429 and count_repeat_req > 0:
            time.sleep(5)
            return self.execute_get_request(method, params, count_repeat_req - 1)

        return result

    def get_statements(self, date_start, data_end):
        params = dict(accountNumber=self.account_number)
        if date_start:
            params['from'] = date_start.strftime("%Y-%m-%d")
        if data_end:
            params['till'] = data_end.strftime("%Y-%m-%d")

        result = self.execute_get_request('/api/v1/bank-statement', params)

        return result

