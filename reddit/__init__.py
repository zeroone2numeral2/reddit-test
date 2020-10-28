from .sender import Sender
from .sortings import Sorting
from .reddit import Reddit
from .accounts import AccountManager, CredentialsManager
from config import config


# accounts = AccountManager(config.reddit)  # will be deprecated

_accounts = CredentialsManager('accounts')
_clients = CredentialsManager('clients')

# reddit = Reddit(**config.praw)
# reddit = accounts.default
