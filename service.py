# -*- coding: UTF-8 -*-
import os
import sys
import xbmc
import xbmcaddon
import xbmcplugin

from urlparse import parse_qs  # Only python 2

__addon__ = xbmcaddon.Addon()
__author__ = __addon__.getAddonInfo('author')
__scriptid__ = __addon__.getAddonInfo('id')
__scriptname__ = __addon__.getAddonInfo('name')
__version__ = __addon__.getAddonInfo('version')
__language__ = __addon__.getLocalizedString

__cwd__ = xbmc.translatePath(__addon__.getAddonInfo('path')).decode("utf-8")
__profile__ = xbmc.translatePath(__addon__.getAddonInfo('profile')).decode("utf-8")
__resource__ = xbmc.translatePath(os.path.join(__cwd__, 'resources', 'lib')).decode("utf-8")
__temp__ = xbmc.translatePath(os.path.join(__profile__, 'temp', '')).decode("utf-8")

if not os.path.exists(__temp__):
    os.makedirs(__temp__)

cache_file = os.path.join(__temp__, 'cachefile.dbm')
log_file = os.path.join(__temp__, 'subliminal.log')

sys.path.insert(0, __resource__)

from plugin import SubliminalPlugin


def execute(url, handle, query):
    try:
        xbmc.log(r'Executing <%s?%s> (%d)' % (url, query, handle), level=xbmc.LOGNOTICE)
        params = parse_qs(query)
        xbmc.log('Params params: %s' % params, level=xbmc.LOGDEBUG)
        video_path = xbmc.Player().getPlayingFile().decode('utf-8')
        plugin = SubliminalPlugin(url, handle)
        plugin.configure(cache_file, log_file)

        action = params.get('action')[0] if 'action' in params else None
        if action == 'download':
            xbmc.log('Download with params: %s' % params, level=xbmc.LOGDEBUG)
            plugin.download(video_path, params['subtitle_id'][0], __temp__)
        elif action == 'search':
            plugin.search(video_path, params['languages'][0].split(','))
    finally:
        xbmcplugin.endOfDirectory(handle)


url = sys.argv[0]  # e.g.: plugin://service.subtitles.subliminal/
handle = int(sys.argv[1])  # e.g.: 11
query = sys.argv[2][1:]  # e.g.: ?action=search&languages=Portuguese%20(Brazil)&preferredlanguage=Portuguese%20(Brazil)

# Executes this addon
execute(url, handle, query)
