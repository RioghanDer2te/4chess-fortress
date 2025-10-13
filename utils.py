from typing import Union, Iterable


def list_in_list(list1: Union[str, list, tuple, iter], list2: Union[str, list, tuple, iter], require_all=False) -> bool:
    for i in list1:
        if i in list2 and not require_all:
            return True
        elif i not in list2 and require_all:
            return False
    return require_all


def str_range(start: str, stop: str, step=1) -> list:  # this range is stop inclusive
    return [chr(a) for a in range(ord(start), ord(stop) + (1 if step > 0 else -1), step)]


def make_iter(_o) -> Union[None, list]:
    if _o is None:
        return None
    if isinstance(_o, list):
        return _o.copy()
    if isinstance(_o, str):
        return [_o]
    if isinstance(_o, dict):
        return list(_o)  # made this difference to be able to use dict.items() here
    if isinstance(_o, Iterable):
        return list(_o)
    return [_o]

def chunk_list(lst: Union[Iterable, str], n: int) -> list:
    _lst = list(lst)
    return [_lst[i:i+n] for i in range(0, len(_lst), n)]
