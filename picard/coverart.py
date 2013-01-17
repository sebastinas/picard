# -*- coding: utf-8 -*-
#
# Picard, the next-generation MusicBrainz tagger
# Copyright (C) 2007 Oliver Charles
# Copyright (C) 2007-2011 Philipp Wolfer
# Copyright (C) 2007, 2010, 2011 Lukáš Lalinský
# Copyright (C) 2011 Michael Wiencek
# Copyright (C) 2011-2012 Wieland Hoffmann
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
import json
import re
import traceback
import picard.webservice

from picard.util import partial, mimetype
from PyQt4 import QtCore
from PyQt4.QtCore import QUrl, QObject


class CoverArtDownloader(QtCore.QObject):
    # data transliterated from the perl stuff used to find cover art for the
    # musicbrainz server.
    # See mb_server/cgi-bin/MusicBrainz/Server/CoverArt.pm
    # hartzell --- Tue Apr 15 15:25:58 PDT 2008
    COVERART_SITES = (
        # CD-Baby
        # tested with http://musicbrainz.org/release/1243cc17-b9f7-48bd-a536-b10d2013c938.html
        {
        'name': 'cdbaby',
        'regexp': 'http://(www\.)?cdbaby.com/cd/(\w)(\w)(\w*)',
        'imguri': 'http://cdbaby.name/$2/$3/$2$3$4.jpg',
        },
    )

    # amazon image file names are unique on all servers and constructed like
    # <ASIN>.<ServerNumber>.[SML]ZZZZZZZ.jpg
    # A release sold on amazon.de has always <ServerNumber> = 03, for example.
    # Releases not sold on amazon.com, don't have a "01"-version of the image,
    # so we need to make sure we grab an existing image.
    AMAZON_SERVER = {
        "amazon.jp": {
            "server": "ec1.images-amazon.com",
            "id"    : "09",
        },
        "amazon.co.jp": {
            "server": "ec1.images-amazon.com",
            "id"    : "09",
        },
        "amazon.co.uk": {
            "server": "ec1.images-amazon.com",
            "id"    : "02",
        },
        "amazon.de": {
            "server": "ec2.images-amazon.com",
            "id"    : "03",
        },
        "amazon.com": {
            "server": "ec1.images-amazon.com",
            "id"    : "01",
        },
        "amazon.ca": {
            "server": "ec1.images-amazon.com",
            "id"    : "01",                   # .com and .ca are identical
        },
        "amazon.fr": {
            "server": "ec1.images-amazon.com",
            "id"    : "08"
        },
    }

    AMAZON_IMAGE_PATH = '/images/P/%s.%s.%sZZZZZZZ.jpg'
    AMAZON_ASIN_URL_REGEX = re.compile(r'^http://(?:www.)?(.*?)(?:\:[0-9]+)?/.*/([0-9B][0-9A-Z]{9})(?:[^0-9A-Z]|$)')

    _CAA_THUMBNAIL_SIZE_MAP = {
        0: "small",
        1: "large",
    }

    def __init__(self, album, metadata, release):
        QtCore.QObject.__init__(self)
        self.try_list = []
        self.settings = QObject.config.setting
        self.album = album
        self.metadata = metadata
        self.release = release

    def run(self):
        """ Gets all cover art URLs from the metadata and then attempts to
        download the album art. """
        album = self.album
        metadata = self.metadata
        if self.settings['ca_provider_use_caa']:
            album._requests += 1
            album.tagger.xmlws.download(
                    "coverartarchive.org", 80, "/release/%s/" %
                    metadata["musicbrainz_albumid"],
                    partial(self._caa_json_downloaded),
                    priority=True, important=True)
        else:
            self._fill_try_list()
            self._walk_try_list()

    def _extract_host_port_path(self, url):
        parsedUrl = QUrl(url)
        path = str(parsedUrl.encodedPath())
        if parsedUrl.hasQuery():
            path += '?' + parsedUrl.encodedQuery()
        host = str(parsedUrl.host())
        port = parsedUrl.port(80)
        return (host, port, path)


    def _try_list_append_image(self, url, imagetype="front", description=""):
        self.log.debug("Adding %s image %s", imagetype, url)
        self.try_list.append({
            'url': url,
            'type': imagetype.lower(),
            'description': description,
        })

    def _process_asin_relation(self, relation):
        match = self.AMAZON_ASIN_URL_REGEX.match(relation.target[0].text)
        if match is not None:
            asinHost = match.group(1)
            asin = match.group(2)
            if asinHost in self.AMAZON_SERVER:
                serverInfo = self.AMAZON_SERVER[asinHost]
            else:
                serverInfo = self.AMAZON_SERVER['amazon.com']
            host = serverInfo['server']
            path_l = self.AMAZON_IMAGE_PATH % (asin, serverInfo['id'], 'L')
            path_m = self.AMAZON_IMAGE_PATH % (asin, serverInfo['id'], 'M')
            self._try_list_append_image("http://%s:%s" % (host, path_l))
            self._try_list_append_image("http://%s:%s" % (host, path_m))

    def _process_url_relation(self, relation):
        # Search for cover art on special sites
        for site in self.COVERART_SITES:
            # this loop transliterated from the perl stuff used to find cover art for the
            # musicbrainz server.
            # See mb_server/cgi-bin/MusicBrainz/Server/CoverArt.pm
            # hartzell --- Tue Apr 15 15:25:58 PDT 2008
            if not self.settings['ca_provider_use_%s' % site['name']]:
                continue
            match = re.match(site['regexp'], relation.target[0].text)
            if match is not None:
                imgURI = site['imguri']
                for i in range(1, len(match.groups())+1):
                    if match.group(i) is not None:
                        imgURI = imgURI.replace('$' + str(i), match.group(i))
                self._try_list_append_image(imgURI)

    def _caa_append_image_to_trylist(self, imagedata):
        """Adds URLs to `try_list` depending on the users CAA image size settings."""
        imagesize = self.settings["caa_image_size"]
        thumbsize = self._CAA_THUMBNAIL_SIZE_MAP.get(imagesize, None)
        if thumbsize is None:
            url = imagedata["image"]
        else:
            url = imagedata["thumbnails"][thumbsize]
        self._try_list_append_image(url, imagedata["types"][0], imagedata["comment"])

    def _walk_try_list(self):
        """Downloads each item in ``try_list``. If there are none left, loading of
        ``album`` will be finalized."""
        album = self.album
        metadata = self.metadata
        release = self.release
        if not self.try_list:
            album._finalize_loading(None)
        elif album.id not in album.tagger.albums:
            return
        else:
            # We still have some items to try!
            album._requests += 1
            imagedata = self.try_list.pop(0)
            host, port, path = self._extract_host_port_path(imagedata['url'])
            self.tagger.window.set_statusbar_message(N_("Downloading http://%s:%i%s"),
                    host, port, path)
            album.tagger.xmlws.download(
                    host, port, path,
                    partial(self._coverart_downloaded, imagedata),
                    priority=True, important=True)


    def _coverart_downloaded(self, imagedata, data, http, error):
        album = self.album
        metadata = self.metadata
        release = self.release

        album._requests -= 1
        imagetype = imagedata["type"]

        if error or len(data) < 1000:
            if error:
                album.log.error(str(http.errorString()))
        else:
            self.tagger.window.set_statusbar_message(N_("Coverart %s downloaded"),
                    http.url().toString())
            mime = mimetype.get_from_data(data, default="image/jpeg")
            filename = None
            if imagetype != 'front' and self.settings["caa_image_type_as_filename"]:
                    filename = imagetype
            metadata.add_image(mime, data, filename, imagedata["description"],
                               imagetype)
            for track in album._new_tracks:
                track.metadata.add_image(mime, data, filename,
                                         imagedata["description"], imagetype)

        # If the image already was a front image, there might still be some
        # other front images in the try_list - remove them.
        if imagetype == 'front':
            for item in self.try_list[:]:
                if item['type'] == 'front' and 'archive.org' not in item['url']: # FIXME: match
                    # Hosts other than archive.org only provide front images
                    self.try_list.remove(item)
        self._walk_try_list()

    def _fill_try_list(self):
        """Fills ``try_list`` by looking at the relationships in ``release``."""
        try:
            release = self.release
            if 'relation_list' in release.children:
                for relation_list in release.relation_list:
                    if relation_list.target_type == 'url':
                        for relation in relation_list.relation:
                            self._process_url_relation(relation)

                            # Use the URL of a cover art link directly
                            if self.settings['ca_provider_use_whitelist']\
                                and (relation.type == 'cover art link' or
                                        relation.type == 'has_cover_art_at'):
                                self._try_list_append_image(relation.target[0].text)
                            elif self.settings['ca_provider_use_amazon']\
                                and (relation.type == 'amazon asin' or
                                        relation.type == 'has_Amazon_ASIN'):
                                self._process_asin_relation(relation)
        except AttributeError, e:
            self.album.log.error(traceback.format_exc())

    def _caa_json_downloaded(self, data, http, error):
        album = self.album
        metadata = self.metadata
        release = self.release

        album._requests -= 1
        caa_front_found = False
        if error:
            album.log.error(str(http.errorString()))
        else:
            try:
                caa_data = json.loads(data)
            except ValueError:
                self.log.debug("Invalid JSON: %s", http.url().toString())
            else:
                caa_types = self.settings["caa_image_types"].split()
                caa_types = map(unicode.lower, caa_types)
                for image in caa_data["images"]:
                    if self.settings["caa_approved_only"] and not image["approved"]:
                        continue
                    if not image["types"] and 'unknown' in caa_types:
                        self._caa_append_image_to_trylist(image)
                    imagetypes = map(unicode.lower, image["types"])
                    for imagetype in imagetypes:
                        if imagetype == "front":
                            caa_front_found = True
                        if imagetype in caa_types:
                            self._caa_append_image_to_trylist(image)
                            break

        if error or not caa_front_found:
            self._fill_try_list()
        self._walk_try_list()


def coverart(album, metadata, release):
    CoverArtDownloader(album, metadata, release).run()
