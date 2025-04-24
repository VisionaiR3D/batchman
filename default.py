import sys
import urllib.parse
import xbmc
from modules.common  import addon
from modules.batch   import add_to_batch, remove_from_batch, process_batch
from modules.fileops import move_item, delete_item, bulk_action
from modules.ui      import list_main_menu, list_section, list_folder, list_batch

handle = int(sys.argv[1])

if __name__ == "__main__":
    args = urllib.parse.parse_qs(sys.argv[2][1:])

    if "addtobatch" in args:
        add_to_batch(args["addtobatch"][0], args.get("action", [""])[0])

    elif "removefrombatch" in args:
        remove_from_batch(args["removefrombatch"][0], args.get("action", [""])[0])

    elif "processbatch" in args:
        process_batch(None)

    elif "move" in args:
        move_item(args["move"][0], args.get("type", [None])[0])

    elif "delete" in args:
        delete_item(args["delete"][0], args.get("type", [None])[0])

    elif "bulkaction" in args:
        bulk_action(args.get("path", [None])[0])

    # custom action uitvoeren via xbmc.executebuiltin als ingeschakeld
    elif "customaction" in args and addon.getSettingBool("use_custom_action"):
        command = addon.getSettingString("custom_action_command").strip()
        if command:
            xbmc.executebuiltin(command)

    elif "section" in args:
        list_section(args["section"][0])

    else:
        path = args.get("path", [None])[0]
        if path:
            list_folder(path)
        else:
            list_main_menu()
