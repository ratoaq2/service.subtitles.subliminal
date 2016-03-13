# -*- coding: UTF-8 -*-
from gio._gio import Error

import xbmc
import os
import shutil
import tempfile

import xbmcaddon
import xbmcvfs

__addon__ = xbmcaddon.Addon()
__profile__ = xbmc.translatePath(__addon__.getAddonInfo('profile')).decode('utf-8')
__temp__ = xbmc.translatePath(os.path.join(__profile__, 'temp', '')).decode('utf-8')
RAR_ID = b'\x52\x61\x72\x21\x1A\x07\x00'


def is_rarfile(fd):
    buf = fd.getvalue()[:len(RAR_ID)]
    return buf == RAR_ID


class RarFile(object):

    def __init__(self, fp):
        self.rar_file = None
        self.extract_path = None
        self.fp = fp

    def __enter__(self):
        self.rar_file = tempfile.mkstemp(suffix='.rar', dir=__temp__)[1]
        self.extract_path = tempfile.mkdtemp(dir=__temp__)

        with open(self.rar_file, 'w') as f:
            f.write(self.fp.getvalue())

        xbmc.executebuiltin('XBMC.Extract(%s, %s)' % (self.rar_file, self.extract_path))
        xbmc.sleep(1000)
        return self

    def __exit__(self, type, value, traceback):
        try:
            os.remove(self.rar_file)
        finally:
            shutil.rmtree(self.extract_path)

    def namelist(self):
        return [os.path.join(dp, f).replace(self.extract_path + '/', '', 1)
                for dp, dn, fn in os.walk(self.extract_path) for f in fn]

    def read(self, name):
        target_file = os.path.join(self.extract_path, name)
        with open(target_file, 'r') as f:
            return f.read()


class NotRarFile(Error):
    pass
