import time
import xbmc
import xbmcgui
import xbmcaddon
import re

_addon = xbmcaddon.Addon()

def popinfo(message, heading=_addon.getAddonInfo('name'), icon=xbmcgui.NOTIFICATION_INFO, time=3000, sound=False): #NOTIFICATION_WARNING NOTIFICATION_ERROR
    xbmcgui.Dialog().notification(heading, message, icon, time, sound=sound)

def get_series_indexes(title) -> bool:
    indexes = re.search(r"[sS](\d{1,2})[eE](\d{1,2})", title)
    if indexes:
        season = int(indexes.group(1))
        episode = int(indexes.group(2))
        popinfo(f"Sezóna: {season}, Epizoda: {episode}")
    else:
        return None
    return  season, episode

class OverlayWindow(xbmcgui.WindowDialog):
    def __init__(self):
        super().__init__()
        self.button = xbmcgui.ControlButton(
            x=0, y=80, width=80, height=80,
            label = 'next episode',
        )

        self.addControl(self.button)


monitor = xbmc.Monitor()
player = xbmc.Player()

addon_id = "plugin.video.krastews"  # název tvého video pluginu

popinfo("Service addon spuštěn")

was_playing_my_video = False

overlay = None

# rozeznání streamu z webshare
# 70 vteřin před koncem popup

'''while not monitor.abortRequested():
    if player.isPlayingVideo():
        path = player.getPlayingFile()
        
        if path.startswith(f"https://vip.") or path.__contains__('wsfiles.cz'):
            if not was_playing_my_video:
                popinfo("Video z mého pluginu bylo spuštěno!")
                was_playing_my_video = True
                # ⬇️ spustíš libovolnou akci (API call, overlay, logování, atd.)
                video_title = player.getVideoInfoTag().getTitle()
                  
                
        else:
            was_playing_my_video = False
            overlay = None
    else:
        was_playing_my_video = False
        overlay = None

    if player.isPlayingVideo() and was_playing_my_video:
        if player.getTotalTime() - player.getTime() < 70 and overlay == None:
            get_series_indexes(video_title)
            overlay = OverlayWindow()
            overlay.show()


    if monitor.waitForAbort(2):
        break


if overlay:
    overlay.close()'''

popinfo("Service addon ukončen")
