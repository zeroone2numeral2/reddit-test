import peewee

from ..models import Setting


def jobs_locked():
    return bool(Setting.get_key('locked').value)


def change_lock(new_value: int):
    setting = Setting.get_key('locked')

    if setting.value != new_value:
        # change only if current value is different
        setting.value = new_value
        setting.save()
        return True
    else:
        return False


def unlock_jobs():
    return change_lock(0)


def lock_jobs():
    return change_lock(1)


def get_accounts_usage_mode():
    return Setting.get_key('accounts_usage_mode').value


def change_accounts_usage_mode(value=None):
    if value not in (1, 2, 3, 0, None):
        raise ValueError('invalid usage mode passed')

    setting = Setting.get_key('accounts_usage_mode')
    setting.value = value
    setting.save()
