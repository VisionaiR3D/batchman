# modules/ui.py

import xbmc
import xbmcplugin
import xbmcgui
import sys
import urllib.parse
import os
import time
import xbmcvfs

from .common import addon, addon_id
from .batch import load_batchlist, remove_from_batch
from .fileops import (
    get_move_destination,
    get_item_location,
    move_item,
    delete_item,
    bulk_action,
    get_thumbnail_for_path,
    get_free_space
)

handle = int(sys.argv[1])

def list_main_menu():
    add_section("Movies", "movies")
    add_section("TV Shows", "tvshows")
    add_section("Batch List", "batchlist")

    if addon.getSettingBool("use_custom_action"):
        label = addon.getSettingString("custom_action_label").strip()
        script = addon.getSettingString("custom_action_script").strip()
        if label and script:
            add_section(label, "custom_action")

    xbmcplugin.endOfDirectory(handle)

def add_section(title, section):
    if section == "custom_action":
        url = f"plugin://{addon_id}?customaction=1"
        is_folder = False
    else:
        url = f"plugin://{addon_id}?section={section}"
        is_folder = True

    li = xbmcgui.ListItem(label=title)
    li.setProperty("IsFolder", "true" if is_folder else "false")

    if addon.getSettingBool("use_thumbnails"):
        art_map = {
            'movies':        "main_movies.jpg",
            'tvshows':       "main_tvshows.jpg",
            'batchlist':     "batchlist.jpg",
            'custom_action': "updateplex.jpg"
        }
        art = art_map.get(section)
        if art:
            thumb = f"special://home/addons/{addon_id}/resources/media/{art}"
            li.setArt({'thumb': thumb, 'icon': thumb})

    xbmcplugin.addDirectoryItem(handle, url, li, isFolder=is_folder)

def list_section(section):
    sw_net = addon.getSettingBool("switch_to_network")
    if section == "movies":
        add_dir("Internal Storage Movies", addon.getSettingString("path1"))
        ext_label = "Network Location Movies" if sw_net else "External USB Movies"
        add_dir(ext_label, addon.getSettingString("path2"))
    elif section == "tvshows":
        add_dir("Internal Storage TV Shows", addon.getSettingString("tvpath1"))
        ext_label = "Network Location TV Shows" if sw_net else "External USB TV Shows"
        add_dir(ext_label, addon.getSettingString("tvpath2"))
    elif section == "batchlist":
        list_batch()
    xbmcplugin.endOfDirectory(handle)

def add_dir(name, path):
    free = get_free_space(path)
    if free is not None:
        gb = free / (1024**3)
        name = f"{name} [COLOR lightblue]({gb:.1f} GB free)[/COLOR]"

    url = f"plugin://{addon_id}?path={urllib.parse.quote(path)}"
    li = xbmcgui.ListItem(label=name)
    li.setProperty("IsFolder", "true")
    li.setPath(path)

    thumb = get_thumbnail_for_path(path)
    if thumb:
        li.setArt({'thumb': thumb, 'icon': thumb})

    try:
        real = xbmcvfs.translatePath(path)
        mtime = os.path.getmtime(real)
        date_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mtime))
    except:
        date_str = ""
    li.setInfo('video', {'title': name, 'date': date_str})

    xbmcplugin.addDirectoryItem(handle, url, li, isFolder=True)
    xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_LABEL)
    xbmcplugin.setContent(handle, "videos")

def list_batch():
    bl = load_batchlist()
    allow_del = addon.getSettingBool("allow_delete")

    if not bl:
        li = xbmcgui.ListItem(label="No items in batch list")
        li.setProperty("IsPlayable", "false")
        xbmcplugin.addDirectoryItem(handle, "", li, isFolder=False)
    else:
        for item in bl:
            action, path = item['action'], item['path']
            base   = os.path.basename(path)
            parent = os.path.basename(os.path.dirname(path))
            title  = f"{parent} – {base}"

            if action == 'move':
                location = get_move_destination(path)
                thumb    = "batch_move.jpg"
                label    = f"[COLOR lightblue]Move to {location}:[/COLOR] {title}"
            else:
                location = get_item_location(path)
                thumb    = "batch_delete.jpg"
                label    = f"[COLOR orange]Delete from {location}:[/COLOR] {title}"

            li = xbmcgui.ListItem(label=label)
            li.setProperty("IsFolder", "false")
            li.setProperty("IsPlayable", "false")
            li.setArt({'thumb': f"special://home/addons/{addon_id}/resources/media/{thumb}"})

            remove_url = f"{sys.argv[0]}?removefrombatch={urllib.parse.quote(path)}&action={action}"
            li.addContextMenuItems([("[B]Remove from Batch[/B]", f"RunPlugin({remove_url})")])
            xbmcplugin.addDirectoryItem(handle, "", li, isFolder=False)

    proc = xbmcgui.ListItem(label="Batch Process")
    proc_url = f"{sys.argv[0]}?processbatch=1"
    proc.setArt({'thumb': f"special://home/addons/{addon_id}/resources/media/startbatch.jpg"})
    proc.setProperty("IsPlayable", "false")
    xbmcplugin.addDirectoryItem(handle, proc_url, proc, isFolder=False)

    xbmcplugin.endOfDirectory(handle)

def list_folder(path):
    try:
        dirs, files = xbmcvfs.listdir(path)
        allow_del = addon.getSettingBool("allow_delete")

        for d in dirs:
            fpath = os.path.join(path, d)
            li = xbmcgui.ListItem(label=f"[{d}]")
            li.setProperty("IsFolder", "true")
            li.setPath(fpath)
            url = f"{sys.argv[0]}?path={urllib.parse.quote(fpath)}"

            thumb = get_thumbnail_for_path(path)
            if thumb:
                li.setArt({'thumb': thumb, 'icon': thumb})

            try:
                mtime = os.path.getmtime(xbmcvfs.translatePath(fpath))
                date_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mtime))
            except:
                date_str = ""
            li.setInfo('video', {'title': d, 'date': date_str})

            ctx = [
                ("[COLOR lightblue]Move[/COLOR] to other location",
                 f"RunPlugin({sys.argv[0]}?move={urllib.parse.quote(fpath)}&type=dir)")
            ]
            if allow_del:
                ctx.append(("[COLOR orange]Delete[/COLOR] folder",
                            f"RunPlugin({sys.argv[0]}?delete={urllib.parse.quote(fpath)}&type=dir)"))
            ctx.append(("[B]Batch[/B] [COLOR lightblue]Move[/COLOR]",
                        f"RunPlugin({sys.argv[0]}?addtobatch={urllib.parse.quote(fpath)}&action=move)"))
            if allow_del:
                ctx.append(("[B]Batch[/B] [COLOR orange]Delete[/COLOR]",
                            f"RunPlugin({sys.argv[0]}?addtobatch={urllib.parse.quote(fpath)}&action=delete)"))
            li.addContextMenuItems(ctx)
            xbmcplugin.addDirectoryItem(handle, url, li, isFolder=True)

        for f in files:
            fpath = os.path.join(path, f)
            li = xbmcgui.ListItem(label=f)
            li.setPath(fpath)

            if f.lower().endswith(('.nfo', '.txt', '.srt')):
                li.setProperty("IsPlayable", "false")
                li.setProperty("IsFolder", "true")
                thumb = f"special://home/addons/{addon_id}/resources/media/srt.jpg"
                li.setArt({'thumb': thumb, 'icon': thumb})
            else:
                li.setProperty("IsPlayable", "true")

            try:
                real = xbmcvfs.translatePath(fpath)
                mtime = os.path.getmtime(real)
                size = os.path.getsize(real)
                date_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mtime))
            except:
                size = 0
                date_str = ""
            li.setInfo('video', {'title': f, 'date': date_str, 'size': size})

            ctx = [
                ("[COLOR lightblue]Move[/COLOR] to other location",
                 f"RunPlugin({sys.argv[0]}?move={urllib.parse.quote(fpath)}&type=file)")
            ]
            if allow_del:
                ctx.append(("[COLOR orange]Delete[/COLOR] file",
                            f"RunPlugin({sys.argv[0]}?delete={urllib.parse.quote(fpath)})"))
            ctx.append(("[B]Batch[/B] [COLOR lightblue]Move[/COLOR]",
                        f"RunPlugin({sys.argv[0]}?addtobatch={urllib.parse.quote(fpath)}&action=move)"))
            if allow_del:
                ctx.append(("[B]Batch[/B] [COLOR orange]Delete[/COLOR]",
                            f"RunPlugin({sys.argv[0]}?addtobatch={urllib.parse.quote(fpath)}&action=delete)"))
            li.addContextMenuItems(ctx)

            is_folder = f.lower().endswith(('.nfo', '.txt', '.srt'))
            xbmcplugin.addDirectoryItem(handle, fpath, li, isFolder=is_folder)

        xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_LABEL)
        xbmcplugin.setContent(handle, "videos")
        xbmcplugin.endOfDirectory(handle)

    except Exception as e:
        xbmcgui.Dialog().notification("Error", f"Cannot open folder:\n{e}",
                                      xbmcgui.NOTIFICATION_ERROR, 4000)
