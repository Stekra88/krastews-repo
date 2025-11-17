# -*- coding: utf-8 -*-

import xbmc
import xbmcaddon
import xbmcgui
import os
import io

# Možné ID doplňku Stream Cinema – podle instalace
SC_ADDON_IDS = [
    "plugin.video.stream-cinema",
]

def notify(heading, message, time_ms=5000):
    xbmcgui.Dialog().notification(heading, message, xbmcgui.NOTIFICATION_INFO, time_ms)


def find_sc_addon():
    """
    Pokusí se najít nainstalovaný Stream Cinema podle známých ID.
    Vrátí instanci xbmcaddon.Addon nebo None.
    """
    for addon_id in SC_ADDON_IDS:
        try:
            addon = xbmcaddon.Addon(addon_id)
            return addon
        except RuntimeError:
            # Není nainstalovaný pod tímto ID, pokračujeme dál
            continue
    return None


def patch_sc_headers(sc_path):
    """
    Najde sc.py v resources/lib/api/sc.py a doplní do headers() řádku:
        'Connection': 'close',
    pokud tam ještě není.
    """
    sc_file = os.path.join(sc_path, "resources", "lib", "api", "sc.py")
    if not os.path.exists(sc_file):
        notify("SC hotfix", "Nenalezen sc.py, nic se neopravilo.")
        return

    # Přečíst původní obsah
    with io.open(sc_file, "r", encoding="utf-8") as f:
        content = f.read()

    # Pokud už tam Connection: close je, nic nedělat
    if "'Connection': 'close'" in content or '"Connection": "close"' in content:
        notify("SC hotfix", "Hotfix už byl aplikován dříve.")
        return

    # Konkrétní blok, který chceme nahradit
    old_block = (
        "        headers = {\n"
        "            'User-Agent': user_agent(),\n"
        "            'X-Uuid': get_uuid(),\n"
        "        }\n"
    )

    new_block = (
        "        headers = {\n"
        "            'User-Agent': user_agent(),\n"
        "            'X-Uuid': get_uuid(),\n"
        "            'Connection': 'close',\n"
        "        }\n"
    )

    if old_block not in content:
        # Fallback: hrubší patch – vloží Connection mezi X-Uuid a zavírací složenou závorku
        # aby to nespadlo, když je formát trochu jiný
        if "'X-Uuid': get_uuid()," in content and "def headers(" in content:
            content = content.replace(
                "'X-Uuid': get_uuid(),",
                "'X-Uuid': get_uuid(),\n            'Connection': 'close',"
            )
        else:
            notify("SC hotfix", "Nepodařilo se najít blok headers(), patch neaplikován.")
            return
    else:
        content = content.replace(old_block, new_block)

    # Zápis zpět
    with io.open(sc_file, "w", encoding="utf-8") as f:
        f.write(content)

    notify("SC hotfix", "sc.py úspěšně opraven (Connection: close).")


def main():
    sc_addon = find_sc_addon()
    if sc_addon is None:
        notify("SC hotfix", "Nenalezen doplněk Stream Cinema.")
        return

    sc_path = sc_addon.getAddonInfo("path")
    patch_sc_headers(sc_path)

    # Po jednorázovém patchi můžeme službu ukončit
    # (Kodi službu nespouští v loopu, takže stačí return)
    return


if __name__ == "__main__":
    main()
