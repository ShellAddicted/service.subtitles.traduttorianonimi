# -*- coding: utf-8 -*-

import os,sys
import unicodedata
import xbmc
import xbmcvfs
import xbmcaddon
import xbmcgui
import xbmcplugin

import urllib
import requests
import zipfile
import StringIO
import traceback

__addon__ = xbmcaddon.Addon()
__author__ = __addon__.getAddonInfo('author')
__scriptid__ = __addon__.getAddonInfo('id')
__scriptname__ = __addon__.getAddonInfo('name')
__version__ = __addon__.getAddonInfo('version')
__language__ = __addon__.getLocalizedString
main_url = 'http://traduttorianonimi.weebly.com/'

__cwd__ = xbmc.translatePath(__addon__.getAddonInfo('path')).decode('utf-8')
__profile__ = xbmc.translatePath(__addon__.getAddonInfo('profile')).decode('utf-8')
__resource__ = xbmc.translatePath(os.path.join(__cwd__, 'resources', 'lib')).decode('utf-8')
__temp__ = xbmc.translatePath(os.path.join(__profile__, 'temp','')).decode('utf-8')

def log(msg, force = True):
    xbmc.log(("""*** [{}] -> {}""".format(__scriptname__,msg)).encode('utf-8'), level = xbmc.LOGNOTICE)
    return 0;
    if force:
        xbmc.log((u'### [' + __scriptname__ + u'] - ' + msg).encode('utf-8'), level = xbmc.LOGNOTICE)
    else:
        xbmc.log((u'### [' + __scriptname__ + u'] - ' + msg).encode('utf-8'), level = xbmc.LOGDEBUG)
        
sys.path.append(__resource__)
log("Final syspath=>{}".format(str(sys.path)))

import TraduttoriAnonimi;
        
def notify(msg,header=__scriptname__,time=5000,image=None):
    if (image!=None):
        xbmc.executebuiltin((u'Notification({},{},{},{})'.format(header, msg,time,image)).encode('utf-8'))
    else:
        xbmc.executebuiltin((u'Notification({},{},{})'.format(header, msg, time)).encode('utf-8'))
    
        
def RetriveURL(url):
    try:
        headers={'user-agent': 'Kodi-SubtitleService-TraduttoriAnonimi'};
        q=requests.get(url,headers=headers);
        return q;
    except:
        log(traceback.format_exc())
        notify("Errore di rete. controlla la tua connessione",time=3000)
        return None;

def normalizeString(str):
	return unicodedata.normalize(
		'NFKD', unicode(unicode(str, 'utf-8'))
	).encode('ascii', 'ignore')

def get_params():
	param = {}
	paramstring = sys.argv[2]
	if len(paramstring) >= 2:
		params = paramstring
		cleanedparams = params.replace('?', '')
		if (params[len(params) - 1] == '/'):
			params = params[0:len(params) - 2]
		pairsofparams = cleanedparams.split('&')
		param = {}
		for i in range(len(pairsofparams)):
			splitparams = pairsofparams[i].split('=')
			if (len(splitparams)) == 2:
				param[splitparams[0]] = splitparams[1]

	return param

def search(item):
    try:
        if ('ita' in item['languages']):
            if (item['tvshow']):
                x=TraduttoriAnonimi.TraduttoriAnonimi(ShowsListFile=None);
                results=x.SearchSubtitles(item["tvshow"], int(item["season"]), int(item["episode"]));
                if (results!=None):
                    for sub in results:
                        listitem = xbmcgui.ListItem(label='Italian',label2=sub["Name"],thumbnailImage='it')
                        xbmcplugin.addDirectoryItem(handle = int(sys.argv[1]), url = "plugin://{}/?action=download&url={}".format(__scriptid__,sub["URL"]), listitem = listitem, isFolder = False)
                    xbmcplugin.endOfDirectory(int(sys.argv[1]))	# send end of directory to XBMC
            else:
                notify("i sottotitoli sono disponibili solo per le serie tv il supporto ad i Film sara' aggiunto in futuro",time=12000)
                log('TelefilmAddicted only works with tv shows. Skipped')
        else:
            notify('i sottotitoli sono disponibili solo in italiano controlla le tue impostazioni [Video->Sottotitoli->Lingue per cui scaricare i sottotitoli]',time=17000)
            log('TelefilmAddicted only works with italian. Skipped')
    except requests.ConnectionError:
        log(traceback.format_exc())
        notify("Errore di rete. controlla la tua connessione",time=3000)
def download(url):
	exts=["srt"]
	o=[];
        try:
            content=RetriveURL(url).content
        except AttributeError:
            content=None;
	
	if content!=None:
		tmp=StringIO.StringIO(content)
		if content[0]=="P":
			q=zipfile.ZipFile(tmp)
			for name in q.namelist():
				if (name.split(".")[-1] in exts):
					q.extract(name,__temp__)
					o.append(os.path.join(__temp__,name));
			q.close();
            
		else:
			try:
				q=open(os.path.join(__temp__,os.path.basename(url)),"wb")
				q.write(content)
				q.close()
				o.append(os.path.join(__temp__,os.path.basename(url)))
			except Exception as exc:
				try:
					q.close();
				except:pass
				raise exc;
	return o;
	


log("Application version: {}".format(__version__))
if xbmc.Player().isPlayingVideo():
    for x in [__profile__,__temp__]:
        if (not xbmcvfs.exists(x)):
            xbmcvfs.mkdirs(x)
	params = get_params()

	if (params['action'] == 'search' or params['action'] == 'manualsearch'):
		item = {}
		item['mansearch'] = params['action'] == 'manualsearch'
                if (item['mansearch']):
                    notify("La Ricerca Manuale Non e' supportata ma verra' aggiunta in futuro",time=3000)
		item['season'] = str(xbmc.getInfoLabel('VideoPlayer.Season'))								# Season
		item['episode'] = str(xbmc.getInfoLabel('VideoPlayer.Episode')).zfill(2)					# Episode
		item['tvshow'] = normalizeString(xbmc.getInfoLabel('VideoPlayer.TVshowtitle'))				# Show
		item['file_original_path'] = xbmc.Player().getPlayingFile().decode('utf-8')             	# Full path
		item['languages'] = []

		if 'searchstring' in params:
			item['mansearch'] = True
			item['mansearchstr'] = urllib.unquote(params['searchstring'])

		for lang in urllib.unquote(params['languages']).decode('utf-8').split(','):
			item['languages'].append(xbmc.convertLanguage(lang, xbmc.ISO_639_2))

		if item['episode'].lower().find('s') > -1:									 # Check if season is "Special"
			item['season'] = '0'
			item['episode'] = item['episode'][-1:]

		search(item)
		
	elif (params['action'] == 'download'):
		subs=download(params["url"])
		for sub in subs:
			listitem = xbmcgui.ListItem(label = sub)
			xbmcplugin.addDirectoryItem(handle = int(sys.argv[1]), url = sub, listitem = listitem, isFolder = False)

		xbmcplugin.endOfDirectory(int(sys.argv[1]))
