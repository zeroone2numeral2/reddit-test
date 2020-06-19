from .reddit import Reddit


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

    def by_name(self, account_name):
        return self._accounts.get(account_name.lower(), self._default)

    def exists(self, account_name):
        return account_name.lower in self._accounts

    @property
    def default(self):
        return self._default
