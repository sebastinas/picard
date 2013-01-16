# -*- coding: utf-8 -*-
#
# Copyright (C) 2013 Laurent Monin
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

# hack to make doctest and gettext work together... :(
try:
    _("")
except NameError:
    def _(a_string):
        return a_string
except TypeError:
    # during doctesting, _ might mean something else
    pass

class BytesToHuman(object):
    """
    Helper class to convert bytes to human-readable form
    It supports i18n through gettext and both decimal and binary units

    >>> b = BytesToHuman()
    >>> n = 1572864
    >>> [b.binary(n), b.decimal(n), b.binary_long(n), b.decimal_long(n)]
    ['1.5 MiB', '1.6 MB', '1.5 mebibytes', '1.6 megabytes']
    """
    def __init__(self, number=0, multiple=1000):
        """
        Inits BytesToHuman

        >>> '1000 bytes = ' + str(BytesToHuman(1000))
        '1000 bytes = 1 kB'
        >>> str(BytesToHuman(0))
        '0 B'
        >>> b = BytesToHuman()
        >>> [b.binary(4568979874), b.decimal(10**18)]
        ['4.3 GiB', '1000 PB']
        """
        self.number = number
        self.multiple = multiple
        self.__bytes_strings_i18n()

    def __str__(self):
        return self.short_string(self.number, self.multiple)

    def decimal(self, number):
        """
        Convert bytes to short human-readable string, decimal mode

        >>> [BytesToHuman().decimal(n) for n in [1000, 1024, 15500]]
        ['1 kB', '1 kB', '15.5 kB']
        """
        return self.short_string(number, 1000)

    def binary(self, number):
        """
        Convert bytes to short human-readable string, binary mode
        >>> [BytesToHuman().binary(n) for n in [1000, 1024, 15500]]
        ['1000 B', '1 KiB', '15.1 KiB']
        """
        return self.short_string(number, 1024)

    def decimal_long(self, number):
        """
        Convert bytes to long human-readable string, decimal mode
        >>> [BytesToHuman().decimal_long(n) for n in [1000, 1024, 15500]]
        ['1 kilobyte', '1 kilobyte', '15.5 kilobytes']
        """
        return self.long_string(number, 1000)

    def binary_long(self, number):
        """
        Convert bytes to long human-readable string, binary mode
        >>> [BytesToHuman().binary_long(n) for n in [1000, 1024, 15500]]
        ['1000 bytes', '1 kibibyte', '15.1 kibibytes']
        """
        return self.long_string(number, 1024)

    def __bytes_strings_i18n(self):
        """
        Inits BYTES_STRINGS dict, and force gettextization
        """
        #dummy methods to force gettextization
        def ungettext(s, p, n):
            return [s, p]
        def N_(s):
            return s
        self.BYTES_STRINGS = {
            N_('%d B'): ungettext('%d byte', '%d bytes', 0),
            N_('%d kB'): ungettext('%d kilobyte', '%d kilobytes', 0),
            N_('%d KiB'): ungettext('%d kibibyte', '%d kibibytes', 0),
            N_('%d MB'): ungettext('%d megabyte', '%d megabytes', 0),
            N_('%d MiB'): ungettext('%d mebibyte', '%d mebibytes', 0),
            N_('%d GB'): ungettext('%d gigabyte', '%d gigabytes', 0),
            N_('%d GiB'): ungettext('%d gibibyte', '%d gibibytes', 0),
            N_('%d TB'): ungettext('%d terabyte', '%d terabytes', 0),
            N_('%d TiB'): ungettext('%d tebibyte', '%d tebibytes', 0),
            N_('%d PB'): ungettext('%d petabyte', '%d petabytes', 0),
            N_('%d PiB'): ungettext('%d pebibyte', '%d pebibytes', 0),

            N_('%0.1f B'): ungettext('%d byte', '%d bytes', 0), # no 0.1 byte ;)
            N_('%0.1f kB'): ungettext('%0.1f kilobyte', '%0.1f kilobytes', 0),
            N_('%0.1f KiB'): ungettext('%0.1f kibibyte', '%0.1f kibibytes', 0),
            N_('%0.1f MB'): ungettext('%0.1f megabyte', '%0.1f megabytes', 0),
            N_('%0.1f MiB'): ungettext('%0.1f mebibyte', '%0.1f mebibytes', 0),
            N_('%0.1f GB'): ungettext('%0.1f gigabyte', '%0.1f gigabytes', 0),
            N_('%0.1f GiB'): ungettext('%0.1f gibibyte', '%0.1f gibibytes', 0),
            N_('%0.1f TB'): ungettext('%0.1f terabyte', '%0.1f terabytes', 0),
            N_('%0.1f TiB'): ungettext('%0.1f tebibyte', '%0.1f tebibytes', 0),
            N_('%0.1f PB'): ungettext('%0.1f petabyte', '%0.1f petabytes', 0),
            N_('%0.1f PiB'): ungettext('%0.1f pebibyte', '%0.1f pebibytes', 0),
        }
        del ungettext
        del N_

    def textual(self, number, unit, short=True):
        """
        Convert `number` and `unit` to translated string, long or short
        depending on `short` boolean value
        """
        n = int(number)
        key = '%d' if number == n else '%0.1f'
        key += ' ' + unit
        if short:
            return _(key) % number
        else:
            return ungettext(self.BYTES_STRINGS[key][0],
                             self.BYTES_STRINGS[key][1], number) % number

    @staticmethod
    def calc_unit(number, multiple=1000):
        """
        >>> BytesToHuman.calc_unit(12456, 1024)
        (12.2, 'KiB')
        >>> BytesToHuman.calc_unit(-12456, 1000)
        (-12.5, 'kB')
        >>> BytesToHuman.calc_unit(0, 1001)
        Traceback (most recent call last):
            ...
        ValueError: multiple parameter has to be 1000 or 1024
        """
        if number < 0:
            sign = -1
            number = -number
        else:
            sign = 1
        n = float(number)
        if multiple == 1000:
            k, b = 'k', 'B'
        elif multiple == 1024:
            k, b = 'K', 'iB'
        else:
            raise ValueError('multiple parameter has to be 1000 or 1024')

        suffixes = ["B"] + [i + b for i in k + "MGTP"]
        for suffix in suffixes:
            if n < multiple or suffix == suffixes[-1]:
                if suffix == suffixes[0]:
                    return (sign*int(n), suffix)
                else:
                    return (sign*round(n, 1), suffix)
            else:
                n /= multiple

    def short_string(self, number, multiple=1000):
        """
        Returns short human-readable string for `number` bytes

        >>> [BytesToHuman().short_string(15000), BytesToHuman().short_string(15000, 1024)]
        ['15 kB', '14.6 KiB']
        """
        return self.textual(*self.calc_unit(number, multiple), short=True)

    def long_string(self, number, multiple=1000):
        """
        Returns long human-readable string for `number` bytes

        >>> [BytesToHuman().long_string(15000), BytesToHuman().long_string(15000, 1024)]
        ['15 kilobytes', '14.6 kibibytes']
        """
        return self.textual(*self.calc_unit(number, multiple), short=False)


if __name__ == "__main__":
    try:
        import __builtin__
    except ImportError:
        import builtins as __builtin__ #Python 3.0

    try:
        a = _('')
    except NameError:
        __builtin__.__dict__['_'] = lambda a: a

    try:
        a = ungettext('', '', 0)
    except NameError:
        def ungettext(a, b, c):
            if c == 1: return a
            return b
        __builtin__.__dict__['ungettext'] = ungettext

    import doctest
    doctest.testmod()
