import json

from .reddit import Reddit

from config import reddit


class AccountManager:
    def __init__(self, accounts: list):
        self._accounts = {}
        self._default = None
        for i, account in enumerate(accounts):
            initialized_account = Reddit(**account)
            self._accounts[account.username.lower()] = initialized_account
            if i == 0:
                self._default = initialized_account
            elif account.get('default', False):
                self._default = initialized_account

    def by_name(self, account_name, return_default_on_missing=False):
        return self._accounts.get(account_name.lower(), self._default if return_default_on_missing else None)

    def exists(self, account_name):
        return account_name.lower() in self._accounts

    @property
    def default(self):
        return self._default


class CredentialsManager:
    def __init__(self, credentials_type):
        if credentials_type not in ('accounts', 'clients'):
            raise ValueError("'credentials_type' must be either 'accounts' or 'clients'")

        self._credentials = {}
        self._default_name = None

        # ensure there's only one client/account marked as default
        defaults_count = 0
        for item in reddit['reddit'][credentials_type]:
            if item.get('default', False):
                defaults_count += 1

            if defaults_count > 1:
                raise ValueError('reddit.toml must contain only one {} flagged as default'.format(credentials_type))

        if defaults_count < 1:
            raise ValueError('reddit.toml must contain one {} flagged as default'.format(credentials_type))

        # load the dict with the data
        for item in reddit['reddit'][credentials_type]:
            # print(item)
            name = item.get('name', item.get('username', None))

            self._credentials[name] = item
            if item['default']:
                self._default_name = name

    def by_name(self, name, return_default_on_missing=False):
        return self._credentials.get(name, self.default if return_default_on_missing else None)

    def exists(self, name):
        return name in self._credentials

    def __str__(self):
        return json.dumps(self._credentials, indent=2)

    @property
    def default(self):
        return self._credentials[self._default_name]
