# -*- coding: utf-8 -*-
#
# Picard, the next-generation MusicBrainz tagger
# Copyright (C) 2006 Lukáš Lalinský
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

from PyQt4 import QtCore
from picard import config_version, log
from picard.util import LockableObject, rot13


class ConfigUpgradeError(Exception):
    pass


class ConfigSection(LockableObject):
    """Configuration section."""

    def __init__(self, config, name):
        LockableObject.__init__(self)
        self.__config = config
        self.__name = name

    def __getitem__(self, name):
        self.lock_for_read()
        key = "%s/%s" % (self.__name, name)
        try:
            opt = Option.get(self.__name, name)
            if self.__config.contains(key):
                return opt.convert(self.__config.value(key))
            return opt.default
        except KeyError:
            if self.__config.contains(key):
                return self.__config.value(key)
        finally:
            self.unlock()

    def __setitem__(self, name, value):
        self.lock_for_write()
        try:
            self.__config.setValue("%s/%s" % (self.__name, name),
                                  QtCore.QVariant(value))
        finally:
            self.unlock()

    def __contains__(self, key):
        key = "%s/%s" % (self.__name, key)
        return self.__config.contains(key)

    def remove(self, key):
        key = "%s/%s" % (self.__name, key)
        if self.__config.contains(key):
            self.__config.remove(key)


class Config(QtCore.QSettings):
    """Configuration."""

    def __init__(self):
        """Initializes the configuration."""
        QtCore.QSettings.__init__(self, "MusicBrainz", "Picard")
        self.application = ConfigSection(self, "application")
        self.setting = ConfigSection(self, "setting")
        self.persist = ConfigSection(self, "persist")
        self.profile = ConfigSection(self, "profile/default")
        self.current_preset = "default"

        IntOption("application", "config_version", 0)
        self.version = self._from_version = self.application["config_version"]
        self._upgrade_hooks = []

    def switchProfile(self, profilename):
        """Sets the current profile."""
        key = u"profile/%s" % (profilename,)
        if self.contains(key):
            self.profile.name = key
        else:
            raise KeyError, "Unknown profile '%s'" % (profilename,)

    def register_upgrade_hook(self, from_version, to_version, func, *args):
        """Register a function to upgrade from one config version to another"""
        assert(to_version <= config_version)
        assert(from_version >= 0)
        assert(from_version < to_version)
        hook = {
            'from': from_version,
            'to': to_version,
            'func': func,
            'args': args,
            'done': False
        }
        self._upgrade_hooks.append(hook)

    def run_upgrade_hooks(self):
        """Executes registered functions to upgrade config version to the latest"""
        if not self._upgrade_hooks:
            return
        if self._from_version >= config_version:
            return
        #remove executed hooks if any, and sort
        self._upgrade_hooks = sorted([ item for item in self._upgrade_hooks if
                                     not item['done']], key=lambda k:
                                     (k['from'], k['to']))
        for hook in self._upgrade_hooks:
            if self._from_version < hook['to']:
                try:
                    hook['func'](*hook['args'])
                except Exception as e:
                    raise ConfigUpgradeError, "Error during config upgrade from version %d to %d using %s(): %s" \
                           % (self._from_version, hook['to'],
                              hook['func'].__name__, e)
                else:
                    hook['done'] = True
                    self._from_version = hook['to']
                    self.write_version(self._from_version)

        # remove executed hooks
        self._upgrade_hooks = [item for item in self._upgrade_hooks if not item['done']]
        if not self._upgrade_hooks:
            # all hooks were executed, ensure config is marked with latest version
            self._from_version = config_version
            self.write_version(config_version)

    def write_version(self, version):
        self.application["config_version"] = version
        self.sync()


class Option(QtCore.QObject):
    """Generic option."""

    registry = {}

    def __init__(self, section, name, default, convert=None):
        self.section = section
        self.name = name
        self.default = default
        self.convert = convert
        if not self.convert:
            self.convert = type(self.default)
        self.registry[(self.section, self.name)] = self

    @classmethod
    def get(cls, section, name):
        try:
            return cls.registry[(section, name)]
        except KeyError:
            raise KeyError, "Option %s.%s not found." % (section, name)


class TextOption(Option):
    """Option with a text value."""

    def __init__(self, section, name, default):
        def convert(value):
            return unicode(value.toString())
        Option.__init__(self, section, name, default, convert)


class BoolOption(Option):
    """Option with a boolean value."""

    def __init__(self, section, name, default):
        Option.__init__(self, section, name, default, QtCore.QVariant.toBool)


class IntOption(Option):
    """Option with an integer value."""

    def __init__(self, section, name, default):
        def convert(value):
            return value.toInt()[0]
        Option.__init__(self, section, name, default, convert)


class FloatOption(Option):
    """Option with a float value."""

    def __init__(self, section, name, default):
        def convert(value):
            return value.toDouble()[0]
        Option.__init__(self, section, name, default, convert)


class PasswordOption(Option):
    """Super l33t h3ckery!"""

    def __init__(self, section, name, default):
        def convert(value):
            return rot13(unicode(value.toString()))
        Option.__init__(self, section, name, default, convert)


_config = Config()

setting = _config.setting
persist = _config.persist
