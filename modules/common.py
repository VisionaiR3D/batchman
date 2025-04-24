import xbmcaddon
import xbmcvfs
import os

addon       = xbmcaddon.Addon()
addon_id    = addon.getAddonInfo('id')
profile     = addon.getAddonInfo('profile')
batch_file  = os.path.join(xbmcvfs.translatePath(profile), "batchlist.json")