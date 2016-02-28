import datetime
import logging
import operator
import os
import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import traceback

from language import LanguageConverter
from subprocess import check_output, CalledProcessError, STDOUT
from subliminal import region, scan_video, save_subtitles, download_subtitles, compute_score
from subliminal.core import get_subtitle_path, provider_manager, AsyncProviderPool
from subliminal.score import episode_scores, movie_scores
from subliminal.video import Episode

language_converter = LanguageConverter()

addon = xbmcaddon.Addon()


class SubliminalPlugin(object):

    def __init__(self, base_url, handle):
        self.base_url = base_url
        self.handle = handle

    def configure(self, cache_file, log_file):
        region.configure('dogpile.cache.dbm', arguments={'filename': cache_file})
        if addon.getSetting('subliminal.debug') == 'true':
            logger = logging.getLogger('subliminal')
            logger.setLevel(level=logging.DEBUG)
            logger.addHandler(logging.FileHandler(log_file, 'a'))

    def get_video(self, path):
        return scan_video(path, subtitles=False, embedded_subtitles=False)

    def get_providers(self):
        return [p for p in provider_manager.names() if addon.getSetting(p) == 'true']

    def get_provider_configs(self):
        return {p: {'username': addon.getSetting('%s.username' % p), 'password': addon.getSetting('%s.password' % p)}
                for p in provider_manager.names() if addon.getSetting('%s.username' % p)}

    def get_max_workers(self):
        return int(addon.getSetting('subliminal.max_workers'))

    def get_release_name(self, subtitle):
        if hasattr(subtitle, 'filename') and subtitle.filename:
            return subtitle.filename
        if hasattr(subtitle, 'name') and subtitle.name:
            return subtitle.name
        if hasattr(subtitle, 'release') and subtitle.release:
            return subtitle.release
        if hasattr(subtitle, 'releases') and subtitle.releases:
            return str(subtitle.releases)

        return subtitle.id

    def search(self, path, languages):
        languages = {language_converter.from_english(l): l for l in languages}
        xbmc.log('Languages: %s' % languages, level=xbmc.LOGDEBUG)
        video = self.get_video(path)

        providers = self.get_providers()
        provider_configs = self.get_provider_configs()
        max_workers = self.get_max_workers()
        xbmc.log('Providers: %s' % providers, level=xbmc.LOGDEBUG)
        xbmc.log('Provider Configs: %s' % provider_configs, level=xbmc.LOGDEBUG)
        with AsyncProviderPool(max_workers=max_workers, providers=providers, provider_configs=provider_configs) as p:
            subtitles = p.list_subtitles(video, languages=set(languages.keys()))
            max_score = episode_scores['hash'] if isinstance(video, Episode) else movie_scores['hash']

            scored_subtitles = sorted([(s, compute_score(s, video))
                                       for s in subtitles], key=operator.itemgetter(1), reverse=True)
            for subtitle, score in scored_subtitles:
                option = SubtitleOption(subtitle)
                option.get_subtitle(subtitle.id)
                l = languages[subtitle.language]
                release_name = '[%s] %s' % (subtitle.provider_name, self.get_release_name(subtitle))
                rating = int(round(float(5 * (score+2)/max_score)))
                sync = score + 2 >= max_score
                option.add_directory_item(self.base_url, self.handle, release_name, l, rating, sync)
            xbmc.log('%s' % subtitles, level=xbmc.LOGDEBUG)

        return True

    def download(self, path, subtitle_id, temp_folder):
        encoding = addon.getSetting('subliminal.encoding')
        option = SubtitleOption()
        subtitle = option.get_subtitle(subtitle_id)
        xbmc.log('Cached: %s' % subtitle, level=xbmc.LOGDEBUG)
        video = self.get_video(path)
        download_subtitles([subtitle])
        save_subtitles(video, [subtitle], directory=temp_folder, encoding=encoding if encoding else None)
        subtitle_path = xbmc.translatePath(get_subtitle_path(video.name, subtitle.language)).decode('utf-8')
        xbmc.log('subtitle_path: %s' % subtitle_path, level=xbmc.LOGDEBUG)
        temp_path = os.path.join(temp_folder, os.path.basename(subtitle_path))
        xbmc.log('temp_path: %s' % temp_path, level=xbmc.LOGDEBUG)
        self.post_process(temp_path, subtitle.language, encoding)
        listitem = xbmcgui.ListItem(label2=os.path.basename(temp_path))
        xbmcplugin.addDirectoryItem(handle=self.handle, url=temp_path, listitem=listitem, isFolder=False)

    def post_process(self, subtitle_path, language, encoding):
        scripts = addon.getSetting('subliminal.post_processing_script')
        commands = [c.strip() for c in scripts.split('|') if scripts]

        for command in commands:
            cmd = [command, subtitle_path, str(language), encoding]
            try:
                xbmc.log('Executing: %s' % cmd, level=xbmc.LOGNOTICE)
                output = check_output(cmd, stderr=STDOUT)
                xbmc.log('Output: %s' % output, level=xbmc.LOGDEBUG)
                return True
            except CalledProcessError as cpe:
                xbmc.log('Failed to execute post_process script: %s' % cpe.output, level=xbmc.LOGERROR)
            except:
                xbmc.log('Failed to execute post_process script: %s' % traceback.format_exc(), level=xbmc.LOGERROR)


class SubtitleOption(object):

    def __init__(self, subtitle=None):
        self.subtitle = subtitle

    @region.cache_on_arguments(expiration_time=datetime.timedelta(hours=4).total_seconds())
    def get_subtitle(self, subtitle_id):
        return self.subtitle

    def add_directory_item(self, base_url, handle, release_name, language, rating, sync):
        listitem = xbmcgui.ListItem(label=language, label2=release_name,
                                    thumbnailImage=self.get_thumbnail(), iconImage=str(rating))

        if sync:
            listitem.setProperty('sync', 'true')

        url = '%s?action=download&subtitle_id=%s' % (base_url, self.subtitle.id)
        xbmcplugin.addDirectoryItem(handle=handle, url=url, listitem=listitem, isFolder=False)

    def get_thumbnail(self):
        return language_converter.to_alpha2(self.subtitle.language)
