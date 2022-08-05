#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import re
import json
import logging
from logging import handlers, Formatter

from service import get_secret_tinkoff
from tinkoff import TinkoffApi
from bx24 import Bitrix24

DELTA_DAYS = 11

TINKOFF_PATTERN_INVOICE = r'(?:[Сс]ч[её]ту|[Сс]ч.|[Оо]плату) ?[N№]? ?(\d+) '
TINKOFF_KEY_STATEMENT = 'operation'
TINKOFF_KEY_ERROR = 'errorMessage'
TINKOFF_KEY_RECIPIENT_ACCOUNT = 'recipientAccount'
TINKOFF_KEY_PAYMENT_PURPOSE = 'paymentPurpose'


BX24_KEY_RESULT = 'result'
BX24_KEY_ERROR = 'error'
BX24_INVOICE_ENTITY_ID = '31'
BX24_INVOICE_ENTITY_TYPE = f'dynamic_{BX24_INVOICE_ENTITY_ID}'
BX24_INVOICE_SUMMA_OPLAT = 'ufCrmSmartInvoice1656422348947'
BX24_INVOICE_STAGE = 'stageId'
BX24_INVOICE_STAGE_SUCCESS = 'DT31_3:P'


logger_err = logging.getLogger(__name__)
logger_err.setLevel(logging.INFO)
fh_err = handlers.TimedRotatingFileHandler('./logs/error.log', when='W6', interval=1, backupCount=12)
formatter_err = Formatter('[%(asctime)s] %(levelname).1s %(message)s')
fh_err.setFormatter(formatter_err)
logger_err.addHandler(fh_err)


def get_statements_from_tinkoff(account_number, auth_token):
    date_start = datetime.datetime.now() - datetime.timedelta(days=DELTA_DAYS)
    api_tinkoff = TinkoffApi(account_number, auth_token)
    response = api_tinkoff.get_statements(date_start, None)

    if not isinstance(response, dict):
        logger_err.error(f"Не допустимый тип ответа от API Tinkoff при получении списка счетов: {str(response)}")
        return

    if TINKOFF_KEY_ERROR in response:
        logger_err.error(f"API Tinkoff при получении списка счетов вернуло ошибку: {str(response)}")
        return

    if TINKOFF_KEY_STATEMENT not in response:
        logger_err.error(f"В ответе от API Tinkoff при получении списка счетов отсутствует ключ: {str(response)}")
        return

    return response.get(TINKOFF_KEY_STATEMENT)


def get_invoices_from_bx():
    bx24 = Bitrix24()
    response = bx24.call("crm.deal.list", {})

    if not isinstance(response, dict):
        logger_err.error(f"Не допустимый тип ответа от API BX24 при получении списка счетов: {str(response)}")
        return

    if BX24_KEY_ERROR in response:
        logger_err.error(f"API BX24 при получении списка счетов вернуло ошибку: {str(response)}")
        return

    if BX24_KEY_RESULT not in response:
        logger_err.error(f"В ответе от API BX24 при получении списка счетов отсутствует ключ: {str(response)}")
        return

    return response.get(BX24_KEY_RESULT)


def get_number_invoice(comment):
    match = re.search(TINKOFF_PATTERN_INVOICE, comment)
    if match:
        return match[1]


def get_invoice_from_bx(number_invoice):
    bx24 = Bitrix24()
    response = bx24.call("crm.item.list", {
        'entityTypeId': BX24_INVOICE_ENTITY_ID,
        'filter': {
            'accountNumber': number_invoice
        }
    })

    if not isinstance(response, dict):
        logger_err.error(f"Не допустимый тип ответа от API BX24 при получении списка счетов: {str(response)}")
        return

    if BX24_KEY_ERROR in response:
        logger_err.error(f"API BX24 при получении списка счетов вернуло ошибку: {str(response)}")
        return

    if BX24_KEY_RESULT not in response:
        logger_err.error(f"В ответе от API BX24 при получении списка счетов отсутствует ключ: {str(response)}")
        return

    return response.get(BX24_KEY_RESULT)


def update_invoice_from_bx(items_id, summa_oplat):
    bx24 = Bitrix24()
    response = bx24.call("crm.item.update", {
        'entityTypeId': BX24_INVOICE_ENTITY_ID,
        'id': items_id,
        'fields': {
            BX24_INVOICE_STAGE: BX24_INVOICE_STAGE_SUCCESS,
            BX24_INVOICE_SUMMA_OPLAT: summa_oplat
        }
    })

    if not isinstance(response, dict):
        logger_err.error(f"Не допустимый тип ответа от API BX24 при получении списка счетов: {str(response)}")
        return

    if BX24_KEY_ERROR in response:
        logger_err.error(f"API BX24 при получении списка счетов вернуло ошибку: {str(response)}")
        return

    if BX24_KEY_RESULT not in response:
        logger_err.error(f"В ответе от API BX24 при получении списка счетов отсутствует ключ: {str(response)}")
        return

    return response.get(BX24_KEY_RESULT)


def add_comment_invoice_from_bx(entity_id, entity_type, res):
    bx24 = Bitrix24()
    response = bx24.call('crm.timeline.comment.add', {
        'fields': {
            'ENTITY_ID': entity_id,
            'ENTITY_TYPE': entity_type,
            'COMMENT': res
        }
    })
    return response


def updating_list_of_statements_in_bx24(statements):
    for statement in statements:
        if statement.get(TINKOFF_KEY_RECIPIENT_ACCOUNT) != acc_number:
            continue

        # получение счетов из Битрикс по номеру счета из Tinkoff
        number_invoice = get_number_invoice(statement.get(TINKOFF_KEY_PAYMENT_PURPOSE))
        if not number_invoice:
            logger_err.error(f"Отсутствует номер счета: {str(statement)}")
            continue

        invoice = get_invoice_from_bx(number_invoice)

        if 'items' not in invoice or not invoice['items']:
            continue

        if invoice['items'][0].get(BX24_INVOICE_SUMMA_OPLAT):
            continue

        items_id = invoice['items'][0].get('id')
        summa_oplat = statement.get('amount')

        # Добавление комментария в карточку счета
        update_invoice_from_bx(items_id, summa_oplat)

        # Добавление комментария в карточку счета
        add_comment_invoice_from_bx(
            items_id,
            BX24_INVOICE_ENTITY_TYPE,
            json.dumps(statement, indent=4, ensure_ascii=False)
        )


def main(account_number, auth_token):
    if not account_number or not auth_token:
        logger_err.error("Отсутствует номер счета или токен доступа к API Tinkoff")
        return

    # получение всех счетов из Tinkoff
    statements = get_statements_from_tinkoff(account_number, auth_token)
    if statements:
        updating_list_of_statements_in_bx24(statements)


if __name__ == '__main__':
    logger_err.error("Start!")
    acc_number = get_secret_tinkoff("account_number")
    token = get_secret_tinkoff("auth_token")
    main(acc_number, token)

