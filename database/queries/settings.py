import peewee

from ..models import Setting


def jobs_locked():
    return bool(Setting.get_key('locked'))


def change_lock(new_value: bool):
    setting = Setting.get_key('locked')

    if bool(setting.value) != new_value:
        # change only if current value is different
        setting.value = int(not new_value)
        setting.save()
        return True
    else:
        return False


def unlock_jobs():
    change_lock(False)


def lock_jobs():
    change_lock(True)
