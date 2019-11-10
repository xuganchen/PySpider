from collections import OrderedDict


class LimitedOrderedDict(OrderedDict):
    @property
    def maxlen(self):
        return self._maxLen

    def __init__(self, maxLen, *args, **kwargs):
        if type(maxLen) != int:
            raise TypeError("The parameter 'maxLen' must be int!")
        else:
            self._maxLen = maxLen
            super(LimitedOrderedDict, self).__init__(*args, **kwargs)

    def __setitem__(self, key, value):
        if (key not in self) and (len(self) >= self._maxLen):
            last = self.popitem(last=False)
        OrderedDict.__setitem__(self, key, value)






