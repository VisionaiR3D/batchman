# modules/fileops.py

import os
import shutil
import xbmcvfs
import xbmcgui
import xbmc

from .common import addon, addon_id

def get_free_space(path):
    """
    Return the number of free bytes on the filesystem containing `path`,
    or None on error.
    """
    try:
        real = xbmcvfs.translatePath(path)
        stats = os.statvfs(real)
        return stats.f_bavail * stats.f_frsize
    except:
        return None

def get_thumbnail_for_path(path):
    """
    Return a thumbnail path based on your movie/TV locations and settings.
    Respects the 'switch_to_network' boolean to swap external<>network thumbs.
    """
    if not addon.getSettingBool("use_thumbnails"):
        return ""

    def local(img):
        return f"special://home/addons/{addon_id}/resources/media/{img}"

    p1  = addon.getSettingString("path1")
    p2  = addon.getSettingString("path2")
    tv1 = addon.getSettingString("tvpath1")
    tv2 = addon.getSettingString("tvpath2")

    use_net = addon.getSettingBool("switch_to_network")

    if path.startswith(p1):
        return local("internal_movies.jpg")
    elif path.startswith(p2):
        return use_net and local("network_movies.jpg") or local("external_movies.jpg")
    elif path.startswith(tv1):
        return local("internal_tvshows.jpg")
    elif path.startswith(tv2):
        return use_net and local("network_tvshows.jpg") or local("external_tvshows.jpg")
    return ""

def get_move_destination(path):
    """
    Determine whether a path will move to Internal or External.
    """
    p1 = addon.getSettingString("path1")
    p2 = addon.getSettingString("path2")
    tv1 = addon.getSettingString("tvpath1")
    tv2 = addon.getSettingString("tvpath2")
    if path.startswith(p1) or path.startswith(tv1):
        return "External"
    if path.startswith(p2) or path.startswith(tv2):
        return "Internal"
    return "Unknown"

def get_item_location(path):
    """
    Determine whether a path currently lives in Internal or External.
    """
    p1 = addon.getSettingString("path1")
    p2 = addon.getSettingString("path2")
    tv1 = addon.getSettingString("tvpath1")
    tv2 = addon.getSettingString("tvpath2")
    if path.startswith(p1) or path.startswith(tv1):
        return "Internal"
    if path.startswith(p2) or path.startswith(tv2):
        return "External"
    return "Unknown"

def is_dir(path):
    """
    Check if a path is a directory:
    1) Try local filesystem (os.path.isdir)
    2) Fallback to xbmcvfs.listdir
    """
    try:
        real = xbmcvfs.translatePath(path)
        if os.path.exists(real):
            return os.path.isdir(real)
    except:
        pass
    try:
        xbmcvfs.listdir(path)
        return True
    except:
        return False

def gather_all_files(folder):
    """
    Recursively gather all files (any extension) in folder and subfolders.
    """
    out = []
    try:
        dirs, files = xbmcvfs.listdir(folder)
    except:
        return out
    for f in files:
        out.append(os.path.join(folder, f))
    for d in dirs:
        out.extend(gather_all_files(os.path.join(folder, d)))
    return out

def clean_empty_dirs(path):
    """
    Remove empty directories, walking upwards until non-empty or root.
    """
    while True:
        real = xbmcvfs.translatePath(path)
        try:
            if os.path.isdir(real) and not os.listdir(real):
                os.rmdir(real)
            else:
                break
        except:
            try:
                dirs, files = xbmcvfs.listdir(path)
                if dirs or files:
                    break
                xbmcvfs.rmdir(path)
            except:
                break
        parent = os.path.dirname(path.rstrip('/'))
        if not parent or parent == path:
            break
        path = parent

def move_item(source_path, item_type):
    from .batch import BATCH_CONFIRM_ALL
    try:
        p1  = addon.getSettingString("path1")
        p2  = addon.getSettingString("path2")
        tv1 = addon.getSettingString("tvpath1")
        tv2 = addon.getSettingString("tvpath2")

        if   source_path.startswith(p1):  dest = source_path.replace(p1, p2, 1)
        elif source_path.startswith(p2):  dest = source_path.replace(p2, p1, 1)
        elif source_path.startswith(tv1): dest = source_path.replace(tv1, tv2, 1)
        elif source_path.startswith(tv2): dest = source_path.replace(tv2, tv1, 1)
        else:
            xbmcgui.Dialog().ok("Move failed", "Path not in known locations.")
            return False

        if xbmcvfs.exists(dest):
            overwrite = BATCH_CONFIRM_ALL or xbmcgui.Dialog().yesno(
                "Already exists", f"Overwrite {os.path.basename(dest)}?")
            if not overwrite:
                return False
            if item_type == "dir":
                delete_dir(dest)
            else:
                xbmcvfs.delete(dest)

        success = False
        if item_type == "dir":
            if xbmcvfs.rename(source_path, dest):
                success = True
            elif copy_dir(source_path, dest):
                delete_dir(source_path)
                success = True
        else:
            if xbmcvfs.rename(source_path, dest):
                success = True
            elif xbmcvfs.copy(source_path, dest):
                xbmcvfs.delete(source_path)
                success = True

        if success:
            xbmcgui.Dialog().notification("Moved", os.path.basename(source_path),
                                         xbmcgui.NOTIFICATION_INFO, 2000)
        else:
            xbmcgui.Dialog().notification("Error", f"Could not move {os.path.basename(source_path)}",
                                         xbmcgui.NOTIFICATION_ERROR, 3000)
        return success

    except Exception as e:
        xbmcgui.Dialog().notification("Error in move_item", str(e),
                                     xbmc.NOTIFICATION_ERROR, 5000)
        return False
    finally:
        xbmc.executebuiltin('Container.Refresh')

def copy_dir(src, dst):
    from .batch import BATCH_CONFIRM_ALL
    try:
        if not xbmcvfs.exists(dst):
            if not xbmcvfs.mkdir(dst):
                xbmcgui.Dialog().notification("Error", f"Cannot create folder:\n{dst}",
                                             xbmcgui.NOTIFICATION_ERROR, 3000)
                return False

        dirs, files = xbmcvfs.listdir(src)
        for f in files:
            s = f"{src}/{f}"
            d = f"{dst}/{f}"
            if xbmcvfs.exists(d):
                overwrite = BATCH_CONFIRM_ALL or xbmcgui.Dialog().yesno(
                    "File exists", f"Overwrite {f}?")
                if not overwrite:
                    continue
                xbmcvfs.delete(d)
            if not xbmcvfs.copy(s, d):
                if not BATCH_CONFIRM_ALL:
                    cont = xbmcgui.Dialog().yesno("Copy error", f"Cannot copy {f}, continue?")
                    if not cont:
                        return False

        for d in dirs:
            if not copy_dir(f"{src}/{d}", f"{dst}/{d}"):
                return False

        return True

    except Exception as e:
        xbmcgui.Dialog().notification("Error", f"copy_dir failed:\n{e}",
                                     xbmcgui.NOTIFICATION_ERROR, 3000)
        return False

def delete_dir(path):
    try:
        dirs, files = xbmcvfs.listdir(path)
        for f in files:
            xbmcvfs.delete(f"{path}/{f}")
        for d in dirs:
            delete_dir(f"{path}/{d}")
        xbmcvfs.rmdir(path)
    except:
        pass

def delete_item(path, item_type=None):
    from .batch import BATCH_CONFIRM_ALL

    allow = addon.getSettingBool("allow_delete")
    if not allow:
        xbmcgui.Dialog().notification("Deletion Disabled", "Deleting is disabled in settings.",
                                     xbmcgui.NOTIFICATION_INFO, 2000)
        return False
    try:
        if not BATCH_CONFIRM_ALL:
            if not xbmcgui.Dialog().yesno("Delete?", os.path.basename(path)):
                return False

        typ = item_type or ("dir" if is_dir(path) else "file")
        if typ == "dir":
            delete_dir(path)
            xbmcgui.Dialog().notification("Deleted folder", os.path.basename(path),
                                         xbmcgui.NOTIFICATION_INFO, 2000)
        else:
            if not xbmcvfs.delete(path):
                real = xbmcvfs.translatePath(path)
                if os.path.exists(real):
                    os.remove(real)
            xbmcgui.Dialog().notification("Deleted file", os.path.basename(path),
                                         xbmcgui.NOTIFICATION_INFO, 2000)
        return True

    except Exception as e:
        xbmcgui.Dialog().notification("Error deleting", str(e),
                                     xbmcgui.NOTIFICATION_ERROR, 3000)
        return False
    finally:
        xbmc.executebuiltin('Container.Refresh')

def bulk_action(path):
    xbmcgui.Dialog().ok("Bulk Action", "Not implemented")

def update_plex():
    script = f"special://home/addons/{addon_id}/resources/updateplex.py"
    xbmc.executebuiltin(f"RunScript({script})")
