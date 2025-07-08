import time
import xbmc
import xbmcgui
import xbmcaddon

_addon = xbmcaddon.Addon()

def popinfo(message, heading=_addon.getAddonInfo('name'), icon=xbmcgui.NOTIFICATION_INFO, time=3000, sound=False): #NOTIFICATION_WARNING NOTIFICATION_ERROR
    xbmcgui.Dialog().notification(heading, message, icon, time, sound=sound)

class OverlayWindow(xbmcgui.WindowDialog):
    def __init__(self):
        super().__init__()
        self.label = xbmcgui.ControlLabel(
            x=0, y=0, width=400, height=60,
            label="▶ Hraje se z mého pluginu",
            textColor="white",
            font="font13"
        )
        self.addControl(self.label)

    def update_text(self, new_text):
        self.label.setLabel(new_text)

monitor = xbmc.Monitor()
player = xbmc.Player()

addon_id = "plugin.video.krastews"  # název tvého video pluginu

popinfo("Service addon spuštěn")

was_playing_my_video = False

overlay = None

while not monitor.abortRequested():
    if player.isPlayingVideo():
        path = player.getPlayingFile()
        if path.startswith(f"https://vip."):
            if not was_playing_my_video:
                popinfo("🎬 Video z mého pluginu bylo spuštěno!")
                was_playing_my_video = True
                # ⬇️ spustíš libovolnou akci (API call, overlay, logování, atd.)
                overlay = OverlayWindow()
                overlay.show()
                
        else:
            was_playing_my_video = False
            overlay = None
    else:
        was_playing_my_video = False
        overlay = None

    if monitor.waitForAbort(2):
        break


if overlay:
    overlay.close()

popinfo("Service addon ukončen")
