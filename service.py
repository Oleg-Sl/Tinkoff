import json

filename_secrets_tinkoff = 'secrets_tinkoff.json'
filename_secrets_bx24 = 'secrets_bx24.json'


def get_secret_tinkoff(key):
    with open(filename_secrets_tinkoff, 'r') as secrets_file:
        secrets = json.load(secrets_file)

    return secrets.get(key, None)


def update_secrets_bx24(auth_token, expires_in, refresh_token):
    """ Обновление токенов доступа к BX24 в файле """
    with open(filename_secrets_bx24) as secrets_file:
        data = json.load(secrets_file)

    data["auth_token"] = auth_token
    data["expires_in"] = expires_in
    data["refresh_token"] = refresh_token

    with open(filename_secrets_bx24, 'w') as secrets_file:
        json.dump(data, secrets_file)


def get_secret_bx24(key):
    """ Получение секрета BX24 по ключу """
    with open(filename_secrets_bx24) as secrets_file:
        data = json.load(secrets_file)

    return data.get(key)


def get_secrets_all_bx24():
    """ Получение секрета BX24 """
    with open(filename_secrets_bx24) as secrets_file:
        data = json.load(secrets_file)

    return data

