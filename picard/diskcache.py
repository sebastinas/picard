# -*- coding: utf-8 -*-
#
# Picard, the next-generation MusicBrainz tagger
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
import os
import hashlib
import time
from picard.util import LockableObject
from PyQt4.QtGui import QDesktopServices

class DiskCache(LockableObject):
    """
    Disk caching
    """
    _last_cleanup = 0
    def __init__(self, ttl=60, topdir=None, file_prefix='',
                 file_suffix='.cache', salt='A', hashlevel=2,
                 cleanup_delay=None, cleanup_testonly=False,
                 debug=False):
        LockableObject.__init__(self)
        self.debug=debug
        self.ttl=int(ttl)
        self.topdir=topdir
        self.file_prefix=file_prefix
        self.file_suffix=file_suffix
        self.salt=str(salt)
        self.hashlevel=hashlevel
        self.cleanup_delay=cleanup_delay
        self.cleanup_testonly=cleanup_testonly
        self._last_cleanup = time.time()
        if self.topdir is None:
            self.topdir = str(QDesktopServices.storageLocation(QDesktopServices.CacheLocation))
        d = []
        d.append('Picard')
        d.append(self.__class__.__name__)
        d.append(self.salt)
        d.append(str(self.hashlevel))
        self.cache_folder = os.path.join(self.topdir, '.'.join(d))

        if self.cleanup_delay is None and self.ttl > 0:
            self.cleanup_delay = self.ttl
        if self.debug:
            print self

    def __str__(self):
        t = []
        t.append('ttl: ' + str(self.ttl))
        t.append('cache folder:' + self.cache_folder)
        t.append('cleanup delay:' + str(self.cleanup_delay))
        return "\n".join(t)

    def _mk_hash(self, key):
        """Returns a hash as hex string from given cache key, mixed with salt"""
        return hashlib.sha1(self.salt+str(key)).hexdigest()

    def _mk_path(self, key, write=False):
        """
        Returns full filepath for given cache key. If write is True it will
        create missing directories if needed
        """
        hash_ = self._mk_hash(key)
        #following with return /tmp/picard/a/b/c for cache_folder=/tmp/picard,
        #hash_='abcde', hashlevel=3
        path = os.path.join(self.cache_folder, *[(subdir) for subdir in
                                                 list(hash_[:self.hashlevel])])
        if write and not os.path.exists(path):
            os.makedirs(path)
        return os.path.join(path, self.file_prefix + hash_ + self.file_suffix)

    def read(self, key):
        self.lock_for_read()
        try:
            filepath = self._mk_path(key)
            if os.path.exists(filepath):
                if self.debug:
                    print 'cache read hit: ' + filepath
                modified = os.path.getmtime(filepath)
                age_seconds = time.time() - modified
                if age_seconds < self.ttl:
                    f = open(filepath, "rb")
                    data = f.read()
                    f.close()
                    return data
            if self.debug:
                print 'cache miss: ' + filepath
            return None
        finally:
            self.unlock()

    def write(self, key, data=''):
        self.cleanup()
        self.lock_for_write()
        try:
            filepath = self._mk_path(key, write=True)
            if self.debug:
                print 'cache write: ' + filepath
            f = open(filepath, "wb")
            f.write(data)
            f.close()
        finally:
            self.unlock()

    def _filematch(self, name):
        start_match = True
        end_match = True
        if self.file_prefix != '' and not name.startswith(self.file_prefix):
            start_match = False
        if self.file_suffix != '' and not name.endswith(self.file_suffix):
            end_match = False
        return start_match and end_match

    def _cleanup(self, top_level_dir, older_than=0, filematch=None, testonly=False):
        for root, dirs, files in os.walk(self.cache_folder, topdown=False):
            for name in files:
                if filematch is None or filematch(name):
                    filepath = os.path.join(root, name)
                    if older_than > 0 or os.stat(filepath).st_mtime < older_than:
                        if not testonly:
                            self.lock_for_write()
                            try:
                                os.remove(filepath)
                            finally:
                                self.unlock()
                        if self.debug:
                            print "cache remove file: " + filepath

    def cleanup(self):
        if self.cleanup_delay <= 0:
            return
        now = time.time()
        if self._last_cleanup > now - self.cleanup_delay:
            return
        self._last_cleanup = now
        older_than = self._last_cleanup - self.ttl
        self._cleanup(self.cache_folder, older_than,
                      filematch=self._filematch,
                      testonly=self.cleanup_testonly)
