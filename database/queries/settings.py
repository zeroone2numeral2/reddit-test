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
