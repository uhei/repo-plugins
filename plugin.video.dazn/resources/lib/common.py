# -*- coding: utf-8 -*-

import base64
import datetime
import hashlib
import json
import time
import urllib
import uuid
import xbmc
import xbmcaddon
import xbmcgui
import _strptime
from inputstreamhelper import Helper
from resources import resources

class Common:

    def __init__(self, addon_handle=None, addon_url=None):
        self.api_base = 'https://isl.dazn.com/misl/'
        self.time_format = '%Y-%m-%dT%H:%M:%SZ'
        self.date_format = '%Y-%m-%d'
        self.portability_list = ['AT', 'DE']

        addon = self.get_addon()
        self.addon_handle = addon_handle
        self.addon_url = addon_url
        self.addon_id = addon.getAddonInfo('id')
        self.addon_name = addon.getAddonInfo('name')
        self.addon_version = addon.getAddonInfo('version')
        self.addon_icon = addon.getAddonInfo('icon')
        self.addon_fanart = addon.getAddonInfo('fanart')
        self.content = addon.getSetting('content')
        self.view_id = addon.getSetting('view_id')
        self.view_id_videos = addon.getSetting('view_id_videos')
        self.view_id_epg = addon.getSetting('view_id_epg')
        self.force_view = addon.getSetting('force_view') == 'true'
        self.startup = addon.getSetting('startup') == 'true'

    def utfenc(self, text):
        result = text
        if isinstance(text, unicode):
            result = text.encode('utf-8')
        return result

    def b64dec(self, data):
        missing_padding = len(data) % 4
        if missing_padding != 0:
            data += b'='* (4 - missing_padding)
        return base64.b64decode(data)

    def get_addon(self):
        return xbmcaddon.Addon()

    def get_dialog(self):
        return xbmcgui.Dialog()

    def set_setting(self, key, value):
        return self.get_addon().setSetting(key, value)

    def get_setting(self, key):
        return self.get_addon().getSetting(key)

    def get_string(self, id_):
        return self.utfenc(self.get_addon().getLocalizedString(id_))

    def dialog_ok(self, id_):
        self.get_dialog().ok(self.addon_name, self.get_string(id_))

    def get_resource(self, string):
        result = self.utfenc(string)
        id_ = resources(string)
        if isinstance(id_, int) and id_ != 0:
            result = self.get_string(id_)
        return result

    def get_credentials(self):
        email = self.get_dialog().input(self.addon_name + self.get_string(30002), type=xbmcgui.INPUT_ALPHANUM)
        if '@' in email:
            password = self.get_dialog().input(self.addon_name + self.get_string(30003), type=xbmcgui.INPUT_ALPHANUM, option=xbmcgui.ALPHANUM_HIDE_INPUT)
            if len(password) > 4:
                return {
                    'email': email,
                    'password': password
                }
        return None

    def log(self, msg):
        xbmc.log(str(msg), xbmc.LOGDEBUG)

    def build_url(self, query):
        return self.addon_url + '?' + urllib.urlencode(query)

    def get_language(self):
        language = xbmc.getLanguage().split(' (')[0]
        return xbmc.convertLanguage(language, xbmc.ISO_639_1)

    def time_now(self):
        return datetime.datetime.now().strftime(self.time_format)

    def time_stamp(self, str_date):
        return datetime.datetime.fromtimestamp(time.mktime(time.strptime(str_date, self.time_format)))

    def timedelta_total_seconds(self, timedelta):
        return (
            timedelta.microseconds + 0.0 +
            (timedelta.seconds + timedelta.days * 24 * 3600) * 10 ** 6) / 10 ** 6

    def utc2local(self, date_string):
        if str(date_string).startswith('2'):
            utc = datetime.datetime(*(time.strptime(date_string, self.time_format)[0:6]))
            epoch = time.mktime(utc.timetuple())
            offset = datetime.datetime.fromtimestamp(epoch) - datetime.datetime.utcfromtimestamp(epoch)
            return (utc + offset).strftime(self.time_format)

    def uniq_id(self):
        device_id = ''
        mac_addr = xbmc.getInfoLabel('Network.MacAddress')
        if not ":" in mac_addr: 
            mac_addr = xbmc.getInfoLabel('Network.MacAddress')
        # hack response busy
        i = 0
        while not ":" in mac_addr and i < 3:
            i += 1
            time.sleep(1)
            mac_addr = xbmc.getInfoLabel('Network.MacAddress')
        if ":" in mac_addr:
            device_id = str(uuid.UUID(hashlib.md5(str(mac_addr.decode("utf-8"))).hexdigest()))
        else:
            self.log("[{0}] error: failed to get device id ({1})".format(self.addon_id, str(mac_addr)))
            self.dialog_ok(30051)
        self.set_setting('device_id', device_id)
        return device_id

    def open_is_settings(self):
        xbmcaddon.Addon(id='inputstream.adaptive').openSettings()

    def start_is_helper(self):
        helper = Helper(protocol='mpd', drm='widevine')
        return helper.check_inputstream()

    def days(self, title, now, start):
        today = datetime.date.today()
        if start and not title == 'Live':
            if now[:10] == start[:10]:
                return 'Today'
            elif str(today + datetime.timedelta(days=1)) == start[:10]:
                return 'Tomorrow'
            else:
                for i in range(2,8):
                    if str(today + datetime.timedelta(days=i)) == start[:10]:
                        return (today + datetime.timedelta(days=i)).strftime('%A')
        return title

    def epg_date(self, date):
        return datetime.datetime.fromtimestamp(time.mktime(time.strptime(date, self.date_format)))

    def get_prev_day(self, date):
        return (date - datetime.timedelta(days=1))

    def get_next_day(self, date):
        return (date + datetime.timedelta(days=1))

    def get_date(self):
        date = 'today'
        dlg = self.get_dialog().numeric(1, self.get_string(30230))
        if dlg:
            spl = dlg.split('/')
            date = '%s-%s-%s' % (spl[2], spl[1], spl[0])
        return date

    def get_mpx(self, token):
        token_data = json.loads(self.b64dec(token.split('.')[1]))
        return token_data['mpx']

    def portability_country(self, country, user_country):
        if user_country in self.portability_list:
            country = user_country
        return country