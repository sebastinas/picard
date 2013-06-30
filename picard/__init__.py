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

import re
version_info = (1, 2, 0, 'final', 0)


def version_to_string(version_info):
    assert len(version_info) == 5
    assert version_info[3] in ('final', 'dev')
    return '%d.%d.%d%s%d' % version_info

def version_from_string(version_string):
    g = re.match(r"^(\d+).(\d+).(\d+)(dev|final)(\d+)$", version_string).groups()
    return (int(g[0]), int(g[1]), int(g[2]), g[3], int(g[4]))

__version__ = version_string = version_to_string(version_info)

api_versions = ["0.15.0", "0.15.1", "0.16.0", "1.0.0", "1.1.0", "1.2.0"]
