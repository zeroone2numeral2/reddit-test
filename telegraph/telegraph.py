from typing import List

from telegraph import Telegraph


class ListItem:
    def __init__(self, created_on, subreddits, invite_link):
        self.created_on = created_on
        self.subreddits = subreddits
        self.invite_link = invite_link


class Page:
    def __init__(self, url):
        self._url = url
        self._list_items = list()

    def update(self):
        pass

    def set(self, items: List[ListItem]) -> None:
        for item in items:
            if not isinstance(item, ListItem):
                raise ValueError('All the list items must be of type ListItem')

        self._list_items = items

    def append(self, item: ListItem) -> None:
        if not isinstance(item, ListItem):
            raise ValueError('Item must be of type ListItem')

        self._list_items.append(item)

    def extend(self, items: List[ListItem]) -> None:
        for item in items:
            if not isinstance(item, ListItem):
                raise ValueError('All the list items must be of type ListItem')

        self._list_items.extend(items)

    def reset(self):
        self._list_items = list()


class TelegraphAPI(Telegraph):
    @staticmethod
    def get_page(self):
        return Page('')
