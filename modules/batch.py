# modules/batch.py

import os
import json
import xbmcgui
import xbmc
import xbmcvfs

from .common import batch_file, addon, addon_id
from .fileops import (
    move_item, delete_item, is_dir,
    gather_all_files, clean_empty_dirs
)

# Globale vlag om bevestigingen tijdens batchverwerking te omzeilen.
BATCH_CONFIRM_ALL = False

# Pad voor lockfile om actieve batchsessie te herkennen
real_profile = xbmcvfs.translatePath(addon.getAddonInfo('profile'))
lock_file    = os.path.join(real_profile, 'batch_running.lock')

def is_running():
    try:
        return os.path.exists(lock_file)
    except:
        return False

def set_running(flag: bool):
    try:
        os.makedirs(real_profile, exist_ok=True)
        if flag:
            with open(lock_file, 'w'):
                pass
        else:
            if os.path.exists(lock_file):
                os.remove(lock_file)
    except:
        pass

def load_batchlist():
    if not os.path.exists(batch_file):
        return []
    try:
        with open(batch_file, 'r') as f:
            return json.load(f)
    except:
        xbmcgui.Dialog().notification("Batch", "Could not load batch list",
                                      xbmcgui.NOTIFICATION_ERROR, 2000)
        return []

def save_batchlist(batchlist):
    try:
        with open(batch_file, 'w') as f:
            json.dump(batchlist, f)
    except:
        xbmcgui.Dialog().notification("Batch", "Could not save batch list",
                                      xbmcgui.NOTIFICATION_ERROR, 2000)

def add_to_batch(path, action):
    bl = load_batchlist()
    if any(i['path'] == path and i['action'] == action for i in bl):
        xbmcgui.Dialog().notification("Batch", "Item already in batch",
                                      xbmcgui.NOTIFICATION_INFO, 2000)
        return
    bl.append({'path': path, 'action': action})
    save_batchlist(bl)
    xbmcgui.Dialog().notification("Batch", f"Added for {action}",
                                  xbmcgui.NOTIFICATION_INFO, 2000)

def remove_from_batch(path, action):
    bl = load_batchlist()
    bl = [i for i in bl if not (i['path'] == path and i['action'] == action)]
    save_batchlist(bl)
    xbmcgui.Dialog().notification("Batch", "Removed item from batch",
                                  xbmcgui.NOTIFICATION_INFO, 2000)
    xbmc.executebuiltin('Container.Refresh')

def process_batch(_):
    """
    Voer alle batch-items uit en – indien ingeschakeld – de custom action achteraf.
    """
    global BATCH_CONFIRM_ALL

    # Haal custom-action instellingen
    enabled = addon.getSettingBool("use_custom_action")
    label   = addon.getSettingString("custom_action_label").strip()
    command = addon.getSettingString("custom_action_command").strip()
    use_custom = enabled and label and command

    # Als er al een proces draait
    if is_running():
        choice = xbmcgui.Dialog().select("Batch Process", ["Continue", "Stop Batch Process"])
        if choice == 1:
            if xbmcgui.Dialog().yesno("Stop Batch Process", "Are you sure you want to stop the batch process?"):
                set_running(False)
                xbmcgui.Dialog().notification("Batch", "Batch process stopped",
                                              xbmcgui.NOTIFICATION_INFO, 2000)
        return

    # Laad en controleer batchlijst
    original = load_batchlist()
    if not original:
        xbmcgui.Dialog().notification("Batch", "Batch list is empty", xbmcgui.NOTIFICATION_INFO, 2000)
        return

    # Stel keuzelijst samen
    opts = ["Cancel", "Process with confirmation", "Yes to All"]
    if use_custom:
        opts.append(f"Yes to All and {label}")
    choice = xbmcgui.Dialog().select("Batch Process", opts)
    if choice in (-1, 0):
        return

    update_after      = (choice == 3 and use_custom)
    BATCH_CONFIRM_ALL = (choice >= 2)
    set_running(True)

    # Verzamel operaties en mappen voor cleanup
    ops = []
    dirs_to_cleanup = set()
    for item in original:
        p, act = item['path'], item['action']
        if act == 'move' and is_dir(p):
            files = gather_all_files(p)
            if files:
                dirs_to_cleanup.add(p)
                for fp in files:
                    ops.append((fp, 'move'))
                    dirs_to_cleanup.add(os.path.dirname(fp))
        elif act == 'delete' and is_dir(p):
            ops.append((p, 'delete_dir'))
            dirs_to_cleanup.add(os.path.dirname(p))
        else:
            ops.append((p, act))
            dirs_to_cleanup.add(os.path.dirname(p))

    total     = len(ops)
    remaining = list(ops)

    # Uitvoeren van de batch
    for idx, (path, action) in enumerate(ops, start=1):
        xbmcgui.Dialog().notification(
            "Batch Process",
            f"Processing {idx}/{total}: {os.path.basename(path)}",
            xbmcgui.NOTIFICATION_INFO, 2000
        )
        if action == 'move':
            move_item(path, 'file')
        elif action == 'delete_dir':
            delete_item(path, 'dir')
        else:
            delete_item(path, 'file')

        remaining.pop(0)
        save_batchlist([{'path': p, 'action': a} for p, a in remaining])
        xbmc.executebuiltin('Container.Refresh')

    # Opruimen lege directories
    for d in dirs_to_cleanup:
        clean_empty_dirs(d)

    # Afronding batch
    save_batchlist([])
    xbmcgui.Dialog().notification("Batch", "Batch complete",
                                  xbmcgui.NOTIFICATION_INFO, 3000)
    BATCH_CONFIRM_ALL = False
    set_running(False)

    # Voer custom actie uit als gekozen
    if update_after:
        xbmc.executebuiltin(command)

    xbmc.executebuiltin(f'Container.Update(plugin://{addon_id})')