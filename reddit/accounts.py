import json
from typing import List


class BaseEntity:
    __slots__ = []
    CREDS = []  # list of attributes that will be passed to the praw instance

    def properties_dict(self):
        result = {}
        for attribute in self.__slots__:
            result[attribute] = getattr(self, attribute)

        return result

    def __repr__(self):
        properties_dict = self.properties_dict()
        return json.dumps(properties_dict, indent=2)

    def creds_dict(self):
        result = {}
        for cred_key in self.CREDS:
            result[cred_key] = getattr(self, cred_key)

        return result


class Client(BaseEntity):
    __slots__ = ['name', 'client_id', 'client_secret', 'parent', 'user_agent', 'default', 'id', 'secret']
    DEFAULT_USER_AGENT = 'test script by -'
    CREDS = ['client_id', 'client_secret', 'user_agent']

    def __init__(self, name, client_id, client_secret, parent, user_agent=None, default=False):
        self.name = name
        self.client_id = client_id
        self.id = client_id
        self.client_secret = client_secret
        self.secret = client_secret
        self.user_agent = user_agent if user_agent else self.DEFAULT_USER_AGENT
        self.default = default
        self.parent = parent

    @classmethod
    def from_config(cls, config_dict, parent=None):
        client = cls(
            parent=parent,
            name=config_dict['name'],
            client_id=config_dict['client_id'],
            client_secret=config_dict['client_secret'],
            user_agent=config_dict.get('user_agent', None),
            default=config_dict.get('default', False)
        )

        return client


class Account(BaseEntity):
    __slots__ = ['username', 'password', 'default', 'clients']
    CREDS = ['username', 'password']

    def __init__(self, username, password, default=False):
        self.username = username
        self.password = password
        self.default = default
        self.clients = {}

    @classmethod
    def from_config(cls, config_dict):
        account = cls(
            username=config_dict['username'],
            password=config_dict['password'],
            default=config_dict.get('default', False)
        )

        return account

    def add_client(self, client: Client):
        self.clients[client.name] = client

    @property
    def client_names_list(self) -> List[str]:
        return list(self.clients.keys())

    @property
    def clients_list(self) -> List[Client]:
        return list(self.clients.values())

    @property
    def default_client(self) -> Client:
        for client in self.clients_list:
            if client.default:
                return client

    def client_exists(self, client_name) -> bool:
        return client_name in self.clients

    def get_client_by_name(self, client_name) -> Client:
        return self.clients[client_name]


def serialize(obj):
    return obj.properties_dict()


class Credentials:
    def __init__(self, reddit_config):
        self.accounts = {}

        for account_dict in reddit_config['accounts']:
            if not account_dict.get('enabled', True) or account_dict.get('disabled', False):
                # do not load disabled accounts
                continue

            account = Account.from_config(account_dict)

            for client_dict in account_dict['clients']:
                if not client_dict.get('enabled', True) or client_dict.get('disabled', False):
                    # do not load disabled clients
                    continue

                client = Client.from_config(client_dict)
                client.parent = account.username
                account.add_client(client)

            default_clients_count = len([c for c in account.clients_list if c.default])
            if default_clients_count == 0:
                raise ValueError('reddit.toml: account "{}" must have one client flagged as default'.format(account.username))
            elif default_clients_count > 1:
                raise ValueError('reddit.toml: account "{}" must have only one client flagged as default'.format(account.username))

            # reference the account in every client
            for client in account.clients_list:
                client.parent = account.username

            self.accounts[account.username] = account

        default_accounts_count = len([a for a in self.accounts_list if a.default])
        if default_accounts_count == 0:
            raise ValueError('reddit.toml: there must be one account flagged as default')
        elif default_accounts_count > 1:
            raise ValueError('reddit.toml: there must be only one account flagged as default')

    @property
    def account_names_list(self) -> List[str]:
        return list(self.accounts.keys())

    @property
    def client_names_list(self) -> List[str]:
        clients_list = []
        for account in self.accounts_list:
            for client in account.clients_list:
                if client.name not in clients_list:
                    clients_list.append(client.name)

        return clients_list

    @property
    def accounts_list(self) -> List[Account]:
        return list(self.accounts.values())

    @property
    def default_account(self) -> Account:
        for account in self.accounts_list:
            if account.default:
                return account

    def account_exists(self, account_name) -> bool:
        return account_name in self.accounts

    def client_exists(self, client_name) -> bool:
        for account in self.accounts_list:
            if account.client_exists(client_name):
                return True

        return False

    def get_account_by_name(self, account_name) -> Account:
        return self.accounts[account_name]

    def get_client_by_name(self, client_name) -> Client:
        for account in self.accounts_list:
            if client_name not in account.client_names_list:
                continue

            return account.get_client_by_name(client_name)

    def get_client_parent_account(self, client_name) -> Account:
        for account in self.accounts_list:
            if client_name not in account.client_names_list:
                continue

            return account
