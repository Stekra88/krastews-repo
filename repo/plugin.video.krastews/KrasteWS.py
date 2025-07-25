# -*- coding: utf-8 -*-
# Module: default
# Author: cache-sk
# Created on: 10.5.2020
# License: AGPL v.3 https://www.gnu.org/licenses/agpl-3.0.html


import io
import os
import sys
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmcvfs
import requests.cookies
from xml.etree import ElementTree as ET
import hashlib
from md5crypt import md5crypt
import traceback
import json
import unidecode
import re
import zipfile
import uuid
import math

try:
    from urllib import urlencode
    from urlparse import parse_qsl, urlparse
except ImportError:
    from urllib.parse import urlencode
    from urllib.parse import parse_qsl, urlparse

try:
    from xbmc import translatePath
except ImportError:
    from xbmcvfs import translatePath

BASE = 'https://webshare.cz'
API = BASE + '/api/'
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36"
HEADERS = {'User-Agent': UA, 'Referer':BASE}
REALM = ':Webshare:'
CATEGORIES = ['','video','images','audio','archives','docs','adult']
SORTS = ['','recent','rating','largest','smallest']
SEARCH_HISTORY = 'search_history'
NONE_WHAT = '%#NONE#%'
BACKUP_DB = 'D1iIcURxlR'
LOG_FILE = "C:\\Users\\Legion\\AppData\\Local\\Packages\\XBMCFoundation.Kodi_4n2hpmxwrvr6p\\LocalCache\\Roaming\\Kodi\\addons\\plugin.video.krastews\\"

_url = sys.argv[0]
_handle = int(sys.argv[1])
_addon = xbmcaddon.Addon()
_session = requests.Session()
_session.headers.update(HEADERS)
_profile = translatePath( _addon.getAddonInfo('profile'))
try:
    _profile = _profile.decode("utf-8")
except:
    pass

def get_url(**kwargs):
    return '{0}?{1}'.format(_url, urlencode(kwargs, 'utf-8'))

def api(fnct, data):
    response = _session.post(API + fnct + "/", data=data)
    return response

def is_ok(xml):
    status = xml.find('status').text
    return status == 'OK'

def popinfo(message, heading=_addon.getAddonInfo('name'), icon=xbmcgui.NOTIFICATION_INFO, time=3000, sound=False): #NOTIFICATION_WARNING NOTIFICATION_ERROR
    xbmcgui.Dialog().notification(heading, message, icon, time, sound=sound)

def login():
    username = _addon.getSetting('wsuser')
    password = _addon.getSetting('wspass')
    if username == '' or password == '':
        popinfo(_addon.getLocalizedString(30101), sound=True)
        _addon.openSettings()
        return
    response = api('salt', {'username_or_email': username})
    xml = ET.fromstring(response.content)
    if is_ok(xml):
        salt = xml.find('salt').text
        try:
            encrypted_pass = hashlib.sha1(md5crypt(password.encode('utf-8'), salt.encode('utf-8'))).hexdigest()
            pass_digest = hashlib.md5(username.encode('utf-8') + REALM + encrypted_pass.encode('utf-8')).hexdigest()
        except TypeError:
            encrypted_pass = hashlib.sha1(md5crypt(password.encode('utf-8'), salt.encode('utf-8')).encode('utf-8')).hexdigest()
            pass_digest = hashlib.md5(username.encode('utf-8') + REALM.encode('utf-8') + encrypted_pass.encode('utf-8')).hexdigest()
        response = api('login', {'username_or_email': username, 'password': encrypted_pass, 'digest': pass_digest, 'keep_logged_in': 1})
        xml = ET.fromstring(response.content)
        if is_ok(xml):
            token = xml.find('token').text
            _addon.setSetting('token', token)
            return token
        else:
            popinfo(_addon.getLocalizedString(30102), icon=xbmcgui.NOTIFICATION_ERROR, sound=True)
            _addon.openSettings()
    else:
        popinfo(_addon.getLocalizedString(30102), icon=xbmcgui.NOTIFICATION_ERROR, sound=True)
        _addon.openSettings()

def revalidate():
    token = _addon.getSetting('token')
    if len(token) == 0:
        if login():
            return revalidate()
    else:
        response = api('user_data', { 'wst': token })
        xml = ET.fromstring(response.content)
        status = xml.find('status').text
        if is_ok(xml):
            vip = xml.find('vip').text
            if vip != '1':
                popinfo(_addon.getLocalizedString(30103), icon=xbmcgui.NOTIFICATION_WARNING)
            return token
        else:
            if login():
                return revalidate()

def todict(xml, skip=[]):
    result = {}
    for e in xml:
        if e.tag not in skip:
            value = e.text if len(list(e)) == 0 else todict(e,skip)
            if e.tag in result:
                if isinstance(result[e.tag], list):
                    result[e.tag].append(value)
                else:
                    result[e.tag] = [result[e.tag],value]
            else:
                result[e.tag] = value
    #result = {e.tag:(e.text if len(list(e)) == 0 else todict(e,skip)) for e in xml if e.tag not in skip}
        
    return result
            
def sizelize(txtsize, units=['B','KB','MB','GB']):
    if txtsize:
        size = float(txtsize)
        if size < 1024:
            size = str(size) + units[0]
        else:
            size = size / 1024
            if size < 1024:
                size = str(int(round(size))) + units[1]
            else:
                size = size / 1024
                if size < 1024:
                    size = str(round(size,2)) + units[2]
                else:
                    size = size / 1024
                    size = str(round(size,2)) + units[3]
        return size
    return str(txtsize)
    
def labelize(file):
    if 'size' in file:
        size = sizelize(file['size'])
    elif 'sizelized' in file:
        size = file['sizelized']
    else:
        size = '?'
    label = file['name'] + ' (' + size + ')'
    return label
    
def tolistitem(file, addcommands=[]):
    label = labelize(file)
    listitem = xbmcgui.ListItem(label=label)
    if 'img' in file:
        listitem.setArt({'thumb': file['img']})
    listitem.setInfo('video', {'title': label})
    listitem.setProperty('IsPlayable', 'true')
    commands = []
    commands.append(( _addon.getLocalizedString(30211), 'RunPlugin(' + get_url(action='info',ident=file['ident']) + ')'))
    commands.append(( _addon.getLocalizedString(30212), 'RunPlugin(' + get_url(action='download',ident=file['ident']) + ')'))
    if addcommands:
        commands = commands + addcommands
    listitem.addContextMenuItems(commands)
    return listitem

def ask(what):
    if what is None:
        what = ''
    kb = xbmc.Keyboard(what, _addon.getLocalizedString(30007))
    kb.doModal() # Onscreen keyboard appears
    if kb.isConfirmed():
        return kb.getText() # User input
    return None
    
def loadsearch():
    history = []
    try:
        if not os.path.exists(_profile):
            os.makedirs(_profile)
    except Exception as e:
        traceback.print_exc()
    
    try:
        with io.open(os.path.join(_profile, SEARCH_HISTORY), 'r', encoding='utf8') as file:
            fdata = file.read()
            file.close()
            try:
                history = json.loads(fdata, "utf-8")
            except TypeError:
                history = json.loads(fdata)
    except Exception as e:
        traceback.print_exc()

    return history
    
def storesearch(what):
    if what:
        size = int(_addon.getSetting('shistory'))

        history = loadsearch()

        if what in history:
            history.remove(what)

        history = [what] + history
        
        if len(history)>size:
            history = history[:size]

        try:
            with io.open(os.path.join(_profile, SEARCH_HISTORY), 'w', encoding='utf8') as file:
                try:
                    data = json.dumps(history).decode('utf8')
                except AttributeError:
                    data = json.dumps(history)
                file.write(data)
                file.close()
        except Exception as e:
            traceback.print_exc()

def removesearch(what):
    if what:
        history = loadsearch()
        if what in history:
            history.remove(what)
            try:
                with io.open(os.path.join(_profile, SEARCH_HISTORY), 'w', encoding='utf8') as file:
                    try:
                        data = json.dumps(history).decode('utf8')
                    except AttributeError:
                        data = json.dumps(history)
                    file.write(data)
                    file.close()
            except Exception as e:
                traceback.print_exc()

def dosearch_fast(token, what, category, sort, limit, offset, action):



    #if (_addon.getSetting('searchczech') == "true"): what = what+' cz'

    response = api('search',{'what':'' if what == NONE_WHAT else what, 'category':category, 'sort':sort, 'limit': limit, 'offset': offset, 'wst':token, 'maybe_removed':'true'})
    xml = ET.fromstring(response.content)
    if is_ok(xml):

        #json.dump(item, open(LOG_FILE, 'w'))


        # seřadit do listů
        elements_tree = xml.iter('file')


        if offset > 0: #prev page
            listitem = xbmcgui.ListItem(label=_addon.getLocalizedString(30206))
            listitem.setArt({'icon': 'DefaultAddonsSearch.png'})
            xbmcplugin.addDirectoryItem(_handle, get_url(action=action, what=what, category=category, sort=sort, limit=limit, offset=offset - limit if offset > limit else 0), listitem, True)

        

        scored_items = []

        for file in elements_tree:
            item = todict(file)
            info = getinfo(item['ident'], token)
            response = info
            score = calculate_video_score(response, what)
            scored_items.append((score, item, response))

        # Seřadit
        scored_items.sort(reverse=True, key=lambda x: x[0])

        #for file in elements_tree:
        for file in scored_items:
            item = file[1]
            commands = []
            commands.append(( _addon.getLocalizedString(30214), 'Container.Update(' + get_url(action='search',toqueue=item['ident'], what=what, offset=offset) + ')'))
            listitem = tolistitem(item,commands)
            xbmcplugin.addDirectoryItem(_handle, get_url(action='play',ident=item['ident'],name=item['name']), listitem, False)
        
        xml_info = getinfo(item['ident'], token)
        #save_to_xml(xml_info)

        try:
            total = int(xml.find('total').text)
        except:
            total = 0
            
        if offset + limit < total: 
            listitem = xbmcgui.ListItem(label=_addon.getLocalizedString(30207)) #next page
            listitem.setArt({'icon': 'DefaultAddonsSearch.png'})
            xbmcplugin.addDirectoryItem(_handle, get_url(action=action, what=what, category=category, sort=sort, limit=limit, offset=offset+limit), listitem, True)
    else:
        popinfo(_addon.getLocalizedString(30107), icon=xbmcgui.NOTIFICATION_WARNING)

def dosearch_folders(token, what, category, sort, limit, offset, action):
    all_file_infos = []
    total = 999999  # dummy hodnota pro začátek
    current_offset = 0

    while current_offset < total:
        response = api('search', {
            'what': '' if what == NONE_WHAT else what,
            'category': category,
            'sort': sort,
            'limit': limit,
            'offset': current_offset,
            'wst': token,
            'maybe_removed': 'true'
        })

        xml = ET.fromstring(response.content)
        if not is_ok(xml):
            popinfo(_addon.getLocalizedString(30107), icon=xbmcgui.NOTIFICATION_WARNING)
            return

        files = list(xml.iter('file'))

        for f in files:
            item = todict(f)
            ident = item['ident']
            info = getinfo(ident, token)
            name = info.find('name').text if info is not None else ""
            all_file_infos.append({
                'ident': ident,
                'name': name,
                'item': item
            })

        # zjisti celkový počet jen jednou
        if current_offset == 0:
            try:
                total = int(xml.find('total').text)
            except:
                total = 0

        current_offset += limit

    # --- Dále stejné jako předtím ---
    folders = []
    ostatni = []
    processed = set()

    for i, file1 in enumerate(all_file_infos):
        if file1['ident'] in processed:
            continue

        group = [file1]
        processed.add(file1['ident'])

        for j, file2 in enumerate(all_file_infos):
            if file2['ident'] in processed:
                continue
            if get_string_similarity(file1['name'], file2['name']) > 70:
                group.append(file2)
                processed.add(file2['ident'])

        if len(group) > 1:
            folders.append(group)
        else:
            ostatni.append(file1)

    folders.sort(key=lambda g: len(g), reverse=True)

    for group in folders:
        main_name = group[0]['name']
        label = f"{main_name} ({len(group)} položek)"
        listitem = xbmcgui.ListItem(label=label)
        listitem.setArt({'icon': 'DefaultFolder.png'})
        ident_list = ','.join([f['ident'] for f in group])
        url = get_url(action='show_folder', idents=ident_list)
        xbmcplugin.addDirectoryItem(_handle, url, listitem, True)

    if ostatni:
        label = f"Ostatní ({len(ostatni)} položek)"
        listitem = xbmcgui.ListItem(label=label)
        listitem.setArt({'icon': 'DefaultFolder.png'})
        ident_list = ','.join([f['ident'] for f in ostatni])
        url = get_url(action='show_folder', idents=ident_list)
        xbmcplugin.addDirectoryItem(_handle, url, listitem, True)

    xbmcplugin.endOfDirectory(_handle)

def dosearch(token, what, category, sort, limit, offset, action):
    if _addon.getSetting('folders') == 'true': 
        dosearch_folders(token, what, category, sort, limit, offset, action)
    else: 
        dosearch_fast(token, what, category, sort, limit, offset, action)

def search(params):
    xbmcplugin.setPluginCategory(_handle, _addon.getAddonInfo('name') + " \ " + _addon.getLocalizedString(30201))
    token = revalidate()
    
    updateListing=False
    
    if 'remove' in params:
        removesearch(params['remove'])
        updateListing=True
        
    if 'toqueue' in params:
        toqueue(params['toqueue'],token)
        updateListing=True
    
    what = None
    
    if 'what' in params:
        what = params['what']
    
    if 'ask' in params:
        slast = _addon.getSetting('slast')
        if slast != what:
            what = ask(what)
            if what is not None:
                storesearch(what)
            else:
                updateListing=True

    if what is not None:
        if 'offset' not in params:
            _addon.setSetting('slast',what)
        else:
            _addon.setSetting('slast',NONE_WHAT)
            updateListing=True
        
        category = params['category'] if 'category' in params else CATEGORIES[int(_addon.getSetting('scategory'))]
        sort = params['sort'] if 'sort' in params else SORTS[int(_addon.getSetting('ssort'))]
        limit = int(params['limit']) if 'limit' in params else int(_addon.getSetting('slimit'))
        offset = int(params['offset']) if 'offset' in params else 0
        dosearch(token, what, category, sort, limit, offset, 'search')


    else:
        _addon.setSetting('slast',NONE_WHAT)
        history = loadsearch()
        listitem = xbmcgui.ListItem(label=_addon.getLocalizedString(30205))
        listitem.setArt({'icon': 'DefaultAddSource.png'})
        xbmcplugin.addDirectoryItem(_handle, get_url(action='search',ask=1), listitem, True)

        for search in history:
            listitem = xbmcgui.ListItem(label=search)
            listitem.setArt({'icon': 'DefaultAddonsSearch.png'})
            commands = []
            commands.append(( _addon.getLocalizedString(30213), 'Container.Update(' + get_url(action='search',remove=search) + ')'))
            listitem.addContextMenuItems(commands)
            xbmcplugin.addDirectoryItem(_handle, get_url(action='search',what=search,ask=1), listitem, True)
    xbmcplugin.endOfDirectory(_handle, updateListing=updateListing)

def queue(params):
    xbmcplugin.setPluginCategory(_handle, _addon.getAddonInfo('name') + " \ " + _addon.getLocalizedString(30202))
    token = revalidate()
    updateListing=False
    
    if 'dequeue' in params:
        response = api('dequeue_file',{'ident':params['dequeue'],'wst':token})
        xml = ET.fromstring(response.content)
        if is_ok(xml):
            popinfo(_addon.getLocalizedString(30106))
        else:
            popinfo(_addon.getLocalizedString(30107), icon=xbmcgui.NOTIFICATION_WARNING)
        updateListing=True
    
    response = api('queue',{'wst':token})
    xml = ET.fromstring(response.content)
    if is_ok(xml):
        for file in xml.iter('file'):
            item = todict(file)
            commands = []
            commands.append(( _addon.getLocalizedString(30215), 'Container.Update(' + get_url(action='queue',dequeue=item['ident']) + ')'))
            listitem = tolistitem(item,commands)
            xbmcplugin.addDirectoryItem(_handle, get_url(action='play',ident=item['ident'],name=item['name']), listitem, False)
    else:
        popinfo(_addon.getLocalizedString(30107), icon=xbmcgui.NOTIFICATION_WARNING)
    xbmcplugin.endOfDirectory(_handle,updateListing=updateListing)

def toqueue(ident,token):
    response = api('queue_file',{'ident':ident,'wst':token})
    xml = ET.fromstring(response.content)
    if is_ok(xml):
        popinfo(_addon.getLocalizedString(30105))
    else:
        popinfo(_addon.getLocalizedString(30107), icon=xbmcgui.NOTIFICATION_WARNING)

def history(params):
    xbmcplugin.setPluginCategory(_handle, _addon.getAddonInfo('name') + " \ " + _addon.getLocalizedString(30203))
    token = revalidate()
    updateListing=False
    
    if 'remove' in params:
        remove = params['remove']
        updateListing=True
        response = api('history',{'wst':token})
        xml = ET.fromstring(response.content)
        ids = []
        if is_ok(xml):
            for file in xml.iter('file'):
                if remove == file.find('ident').text:
                    ids.append(file.find('download_id').text)
        else:
            popinfo(_addon.getLocalizedString(30107), icon=xbmcgui.NOTIFICATION_WARNING)
        if ids:
            rr = api('clear_history',{'ids[]':ids,'wst':token})
            xml = ET.fromstring(rr.content)
            if is_ok(xml):
                popinfo(_addon.getLocalizedString(30104))
            else:
                popinfo(_addon.getLocalizedString(30107), icon=xbmcgui.NOTIFICATION_WARNING)
    
    if 'toqueue' in params:
        toqueue(params['toqueue'],token)
        updateListing=True
    
    response = api('history',{'wst':token})
    xml = ET.fromstring(response.content)
    files = []
    if is_ok(xml):
        for file in xml.iter('file'):
            item = todict(file, ['ended_at', 'download_id', 'started_at'])
            if item not in files:
                files.append(item)
        for file in files:
            commands = []
            commands.append(( _addon.getLocalizedString(30213), 'Container.Update(' + get_url(action='history',remove=file['ident']) + ')'))
            commands.append(( _addon.getLocalizedString(30214), 'Container.Update(' + get_url(action='history',toqueue=file['ident']) + ')'))
            listitem = tolistitem(file, commands)
            xbmcplugin.addDirectoryItem(_handle, get_url(action='play',ident=file['ident'],name=file['name']), listitem, False)
    else:
        popinfo(_addon.getLocalizedString(30107), icon=xbmcgui.NOTIFICATION_WARNING)
    xbmcplugin.endOfDirectory(_handle,updateListing=updateListing)
    
def settings(params):
    _addon.openSettings()
    xbmcplugin.setResolvedUrl(_handle, False, xbmcgui.ListItem())

def infonize(data,key,process=str,showkey=True,prefix='',suffix='\n'):
    if key in data:
        return prefix + (key.capitalize() + ': ' if showkey else '') + process(data[key]) + suffix
    return ''

def fpsize(fps):
    x = round(float(fps),3)
    if int(x) == x:
       return str(int(x))
    return str(x)
    
def getinfo_old(ident,wst):
    response = api('file_info',{'ident':ident,'wst': wst})
    xml = ET.fromstring(response.content)
    ok = is_ok(xml)
    if not ok:
        response = api('file_info',{'ident':ident,'wst': wst, 'maybe_removed':'true'})
        xml = ET.fromstring(response.content)
        ok = is_ok(xml)
    if ok:
        return xml
    else:
        popinfo(_addon.getLocalizedString(30107), icon=xbmcgui.NOTIFICATION_WARNING)
        return None

def getinfo(ident, wst):
    try:
        response = api('file_info', {'ident': ident, 'wst': wst})
        xml = ET.fromstring(response.content)
        if not is_ok(xml):
            response = api('file_info', {'ident': ident, 'wst': wst, 'maybe_removed': 'true'})
            xml = ET.fromstring(response.content)
        return xml if is_ok(xml) else None
    except ET.ParseError as e:
        print(f"[getinfo] XML ParseError for ident {ident}: {e}")
        return None
    except Exception as e:
        print(f"[getinfo] Error fetching info for {ident}: {e}")
        return None

def info(params):
    token = revalidate()
    xml = getinfo(params['ident'],token)
    
    if xml is not None:
        info = todict(xml)
        text = ''
        text += infonize(info, 'name')
        text += infonize(info, 'size', sizelize)
        text += infonize(info, 'type')
        text += infonize(info, 'width')
        text += infonize(info, 'height')
        text += infonize(info, 'format')
        text += infonize(info, 'fps', fpsize)
        text += infonize(info, 'bitrate', lambda x:sizelize(x,['bps','Kbps','Mbps','Gbps']))
        if 'video' in info and 'stream' in info['video']:
            streams = info['video']['stream']
            if isinstance(streams, dict):
                streams = [streams]
            for stream in streams:
                text += 'Video stream: '
                text += infonize(stream, 'width', showkey=False, suffix='')
                text += infonize(stream, 'height', showkey=False, prefix='x', suffix='')
                text += infonize(stream,'format', showkey=False, prefix=', ', suffix='')
                text += infonize(stream,'fps', fpsize, showkey=False, prefix=', ', suffix='')
                text += '\n'
        if 'audio' in info and 'stream' in info['audio']:
            streams = info['audio']['stream']
            if isinstance(streams, dict):
                streams = [streams]
            for stream in streams:
                text += 'Audio stream: '
                text += infonize(stream, 'format', showkey=False, suffix='')
                text += infonize(stream,'channels', prefix=', ', showkey=False, suffix='')
                text += infonize(stream,'bitrate', lambda x:sizelize(x,['bps','Kbps','Mbps','Gbps']), prefix=', ', showkey=False, suffix='')
                text += '\n'
        text += infonize(info, 'removed', lambda x:'Yes' if x=='1' else 'No')
        xbmcgui.Dialog().textviewer(_addon.getAddonInfo('name'), text)

def getlink(ident,wst,dtype='video_stream'):
    #uuid experiment
    duuid = _addon.getSetting('duuid')
    if not duuid:
        duuid = str(uuid.uuid4())
        _addon.setSetting('duuid',duuid)
    data = {'ident':ident,'wst': wst,'download_type':dtype,'device_uuid':duuid}
    #TODO password protect
    #response = api('file_protected',data) #protected
    #xml = ET.fromstring(response.content)
    #if is_ok(xml) and xml.find('protected').text != 0:
    #    pass #ask for password
    response = api('file_link',data)
    xml = ET.fromstring(response.content)
    if is_ok(xml):
        return xml.find('link').text
    else:
        popinfo(_addon.getLocalizedString(30107), icon=xbmcgui.NOTIFICATION_WARNING)
        return None

def play(params):
    token = revalidate()
    link = getlink(params['ident'],token)
    if link is not None:
        #headers experiment
        headers = _session.headers
        if headers:
            headers.update({'Cookie':'wst='+token})
            link = link + '|' + urlencode(headers)
        listitem = xbmcgui.ListItem(label=params['name'],path=link)
        listitem.setProperty('mimetype', 'application/octet-stream')
        xbmcplugin.setResolvedUrl(_handle, True, listitem)
    else:
        popinfo(_addon.getLocalizedString(30107), icon=xbmcgui.NOTIFICATION_WARNING)
        xbmcplugin.setResolvedUrl(_handle, False, xbmcgui.ListItem())

def join(path, file):
    if path.endswith('/') or path.endswith('\\'):
        return path + file
    else:
        return path + '/' + file

def download(params):
    token = revalidate()
    where = _addon.getSetting('dfolder')
    if not where or not xbmcvfs.exists(where):
        popinfo('set folder!', sound=True)#_addon.getLocalizedString(30101)
        _addon.openSettings()
        return
        
    local = os.path.exists(where)
        
    normalize = 'true' == _addon.getSetting('dnormalize')
    notify = 'true' == _addon.getSetting('dnotify')
    every = _addon.getSetting('dnevery')
    try:
        every = int(re.sub(r'[^\d]+', '', every))
    except:
        every = 10
        
    try:
        link = getlink(params['ident'],token,'file_download')
        info = getinfo(params['ident'],token)
        name = info.find('name').text
        if normalize:
            name = unidecode.unidecode(name)
        bf = io.open(os.path.join(where,name), 'wb') if local else xbmcvfs.File(join(where,name), 'w')
        response = _session.get(link, stream=True)
        total = response.headers.get('content-length')
        if total is None:
            popinfo(_addon.getLocalizedString(30301) + name, icon=xbmcgui.NOTIFICATION_WARNING, sound=True)
            bf.write(response.content)
        elif not notify:
            popinfo(_addon.getLocalizedString(30302) + name)
            bf.write(response.content)
        else:
            popinfo(_addon.getLocalizedString(30302) + name)
            dl = 0
            total = int(total)
            pct = total / 100
            lastpop=0
            for data in response.iter_content(chunk_size=4096):
                dl += len(data)
                bf.write(data)
                done = int(dl / pct)
                if done % every == 0 and lastpop != done:
                    popinfo(str(done) + '% - ' + name)
                    lastpop = done
        bf.close()
        popinfo(_addon.getLocalizedString(30303) + name, sound=True)
    except Exception as e:
        #TODO - remove unfinished file?
        traceback.print_exc()
        popinfo(_addon.getLocalizedString(30304) + name, icon=xbmcgui.NOTIFICATION_ERROR, sound=True)

def loaddb(dbdir,file):
    try:
        data = {}
        with io.open(os.path.join(dbdir, file), 'r', encoding='utf8') as file:
            fdata = file.read()
            file.close()
            try:
                data = json.loads(fdata, "utf-8")['data']
            except TypeError:
                data = json.loads(fdata)['data']
        return data
    except Exception as e:
        traceback.print_exc()
        return {}

def db(params):
    token = revalidate()
    updateListing=False

    dbdir = os.path.join(_profile,'db')
    if not os.path.exists(dbdir):
        link = getlink(BACKUP_DB,token)
        dbfile = os.path.join(_profile,'db.zip')
        with io.open(dbfile, 'wb') as bf:
            response = _session.get(link, stream=True)
            bf.write(response.content)
            bf.flush()
            bf.close()
        with zipfile.ZipFile(dbfile, 'r') as zf:
            zf.extractall(_profile)
        os.unlink(dbfile)
    
    if 'toqueue' in params:
        toqueue(params['toqueue'],token)
        updateListing=True
    
    if 'file' in params and 'key' in params:
        data = loaddb(dbdir,params['file'])
        item = next((x for x in data if x['id'] == params['key']), None)
        if item is not None:
            for stream in item['streams']:
                commands = []
                commands.append(( _addon.getLocalizedString(30214), 'Container.Update(' + get_url(action='db',file=params['file'],key=params['key'],toqueue=stream['ident']) + ')'))
                listitem = tolistitem({'ident':stream['ident'],'name':stream['quality'] + ' - ' + stream['lang'] + stream['ainfo'],'sizelized':stream['size']},commands)
                xbmcplugin.addDirectoryItem(_handle, get_url(action='play',ident=stream['ident'],name=item['title']), listitem, False)
    elif 'file' in params:
        data = loaddb(dbdir,params['file'])
        for item in data:
            listitem = xbmcgui.ListItem(label=item['title'])
            if 'plot' in item:
                listitem.setInfo('video', {'title': item['title'],'plot': item['plot']})
            xbmcplugin.addDirectoryItem(_handle, get_url(action='db',file=params['file'],key=item['id']), listitem, True)
    else:
        if os.path.exists(dbdir):
            dbfiles = [f for f in os.listdir(dbdir) if os.path.isfile(os.path.join(dbdir, f))]
            for dbfile in dbfiles:
                listitem = xbmcgui.ListItem(label=os.path.splitext(dbfile)[0])
                xbmcplugin.addDirectoryItem(_handle, get_url(action='db',file=dbfile), listitem, True)
    xbmcplugin.addSortMethod(_handle,xbmcplugin.SORT_METHOD_LABEL)
    xbmcplugin.endOfDirectory(_handle, updateListing=updateListing)

def menu():
    revalidate()
    xbmcplugin.setPluginCategory(_handle, _addon.getAddonInfo('name'))

    listitem = xbmcgui.ListItem(label=_addon.getLocalizedString(30201))
    listitem.setArt({'icon': 'DefaultAddonsSearch.png'})
    xbmcplugin.addDirectoryItem(_handle, get_url(action='search'), listitem, True)
    
    listitem = xbmcgui.ListItem(label=_addon.getLocalizedString(30202))
    listitem.setArt({'icon': 'DefaultPlaylist.png'})
    xbmcplugin.addDirectoryItem(_handle, get_url(action='queue'), listitem, True)
    
    listitem = xbmcgui.ListItem(label=_addon.getLocalizedString(30203))
    listitem.setArt({'icon': 'DefaultAddonsUpdates.png'})
    xbmcplugin.addDirectoryItem(_handle, get_url(action='history'), listitem, True)
    
    if 'true' == _addon.getSetting('experimental'):
        listitem = xbmcgui.ListItem(label='Backup DB')
        listitem.setArt({'icon': 'DefaultAddonsZip.png'})
        xbmcplugin.addDirectoryItem(_handle, get_url(action='db'), listitem, True)

    listitem = xbmcgui.ListItem(label=_addon.getLocalizedString(30204))
    listitem.setArt({'icon': 'DefaultAddonService.png'})
    xbmcplugin.addDirectoryItem(_handle, get_url(action='settings'), listitem, False)

    xbmcplugin.endOfDirectory(_handle)

def show_folder(params):
    ident_string = params.get('idents')
    if not ident_string:
        popinfo("Složka neobsahuje žádné položky.", icon=xbmcgui.NOTIFICATION_WARNING)
        return

    idents = ident_string.split(',')
    for ident in idents:
        info = getinfo(ident, None)
        if info is None:
            continue

        item = todict(info)
        item['ident'] = ident  # 🔧 Doplnění chybějícího klíče
        name = info.find('name').text if info.find('name') is not None else "Bez názvu"

        commands = [(_addon.getLocalizedString(30214), 'Container.Update(' + get_url(action='search', toqueue=ident) + ')')]
        listitem = tolistitem(item, commands)

        xbmcplugin.addDirectoryItem(
            _handle,
            get_url(action='play', ident=ident, name=name),
            listitem,
            False
        )

    xbmcplugin.endOfDirectory(_handle)

def router(paramstring):
    params = dict(parse_qsl(paramstring))
    if params:
        if params['action'] == 'search':
            search(params)
        elif params['action'] == 'queue':
            queue(params)
        elif params['action'] == 'history':
            history(params)
        elif params['action'] == 'settings':
            settings(params)
        elif params['action'] == 'info':
            info(params)
        elif params['action'] == 'play':
            play(params)
        elif params['action'] == 'download':
            download(params)
        elif params['action'] == 'db':
            db(params)
        elif params['action'] == 'show_folder':
            show_folder(params)
        else:
            menu()
    else:
        menu()

#saves to defined xml file
def save_to_xml(xml_info):
    xml_str = ET.tostring(xml_info, encoding="utf-8", method="xml")
    with open(LOG_FILE + "test.xml", "wb") as f:
        f.write(xml_str)

#calculate score based on human like
import xml.etree.ElementTree as ET

def calculate_video_score(response, what, log_file_path=LOG_FILE + "scores.txt"):
    def get_int(tag):
        elem = response.find(tag)
        return int(elem.text) if elem is not None and elem.text else 0
    
    def get_str(tag):
        elem = response.find(tag)
        return str(elem.text) if elem is not None and elem.text else ""

    def get_float(tag):
        elem = response.find(tag)
        return float(elem.text) if elem is not None and elem.text else 0.0

    def get_audio_info():
        audio_stream = response.find("audio/stream")
        if audio_stream is not None:
            bitrate = get_int("audio/stream/bitrate")
            channels = get_int("audio/stream/channels")
            return bitrate, channels
        return 0, 0

    # Extrahuj hodnoty
    name = get_str("name")
    pos_votes = get_int("positive_votes")
    neg_votes = get_int("negative_votes")
    width = get_int("width")
    height = get_int("height")
    bitrate = get_int("bitrate")
    fps = get_float("fps")
    audio_bitrate, audio_channels = get_audio_info()
    adult = get_int("adult")
    password = get_int("password")
    removed = get_int("removed")
    copyrighted = get_int("copyrighted")

    # Body za název
    if "dab" in name.lower():
        dabing = 20
    elif "tit" in name.lower():
        dabing = 5
    else:
        dabing = 0

    what2 = what.replace(" ", "-")

    if what.lower() in name.lower():
        name_score = 200
    else:
        name_score = 0

    if what2.lower() in name.lower():
        name_score2 = 200
    else:
        name_score2 = 0

    # Výpočty jednotlivých složek (vážené a normalizované)
    s_dabing = dabing  # +20 nebo +5 nebo 0

    s_pos_votes = 2 * pos_votes
    s_neg_votes = -5 * neg_votes

    # Rozlišení škálované na 0–100 (1080p = 50, 2K = 100)
    s_resolution = (width * height / 2073600) * 100

    # Bitrate videa logaritmicky, váha 5 (rozsah typicky 0–50)
    s_bitrate = (math.log2(max(bitrate, 1)) * 5)/10

    # FPS s lineární vahou
    s_fps = fps * 1

    # Audio bitrate logaritmicky, váha 3
    s_audio_bitrate = (math.log2(max(audio_bitrate, 1)) * 3)/2

    # Počet kanálů, např. stereo = 2, 5.1 = 6
    s_audio_channels = audio_channels * 1.5

    # Penalizace
    s_adult = -1000 * adult
    s_password = -1000 * password
    s_removed = -1000 * removed
    s_copyrighted = 0 # -1000 * copyrighted
    

    # Celkové skóre
    score = (
        s_dabing + s_pos_votes + s_neg_votes + s_resolution +
        s_bitrate + s_fps + s_audio_bitrate + s_audio_channels +
        s_adult + s_password + s_removed + s_copyrighted + name_score + name_score2
    )

    # Zapsat do souboru

    '''
    with open(log_file_path, "a", encoding="utf-8") as f:
        f.write(f"\nNÁZEV: {name}\n")
        f.write(f"\nSEARCHED: .{what}.\n")
        f.write(f"  +{name_score:.2f}  porovnani názvu\n")
        f.write(f"  +{s_dabing:.2f}  dabing/titulky podle názvu\n")
        f.write(f"  +{s_pos_votes:.2f}  kladné hlasy ({pos_votes})\n")
        f.write(f"  {s_neg_votes:.2f}  záporné hlasy ({neg_votes})\n")
        f.write(f"  +{s_resolution:.2f}  rozlišení ({width}x{height})\n")
        f.write(f"  +{s_bitrate:.2f}  bitrate videa ({bitrate})\n")
        f.write(f"  +{s_fps:.2f}  snímková frekvence ({fps})\n")
        f.write(f"  +{s_audio_bitrate:.2f}  bitrate zvuku ({audio_bitrate})\n")
        f.write(f"  +{s_audio_channels:.2f}  audio kanály ({audio_channels})\n")
        if adult: f.write(f"  {s_adult:.2f}  ADULT obsah\n")
        if password: f.write(f"  {s_password:.2f}  chráněno heslem\n")
        if removed: f.write(f"  {s_removed:.2f}  smazáno\n")
        if copyrighted: f.write(f"  {s_copyrighted:.2f}  copyright porušení\n")
        f.write(f"===> CELKOVÉ SKÓRE: {score:.2f}\n")
        f.write("-" * 40 + "\n")

    '''
    return score

"""
BODY ZA PŘESNEJ NÁZEV
ÚSPĚŠNĚ PŘIHLÁŠENO


"""

def get_string_similarity(string1, string2):


    if len(string1) == 0 or len(string2) == 0:
        return 0
    
    if len(string2) > len(string1):
        string1, string2 = string2, string1

    i = 0
    for char in string1:
        if i >= len(string2): break
        if char == string2[i]:
            i += 1
        else:
            break
    percentage = (i*100) / len(string1)
    return percentage