# -*- coding: utf-8 -*-
#
#  service.py
#  
#  Copyright 2016 ShellAddicted <shelladdicted@gmail.com<>
#  
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3 of the License
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#  
#
import os;
import sys;
import unicodedata;
import xbmc;
import xbmcvfs;
import xbmcaddon;
import xbmcgui;
import xbmcplugin;

import urllib;
import requests;
import zipfile;
import StringIO;
import traceback;

addon = xbmcaddon.Addon();
author = addon.getAddonInfo("author");
scriptid = addon.getAddonInfo("id");
scriptname = addon.getAddonInfo("name");
version = addon.getAddonInfo("version");
language = addon.getLocalizedString;
main_url = "http://traduttorianonimi.it";

cwd = xbmc.translatePath(addon.getAddonInfo("path")).decode("utf-8");
profile = xbmc.translatePath(addon.getAddonInfo("profile")).decode("utf-8");
resource = xbmc.translatePath(os.path.join(cwd, "resources", "lib")).decode("utf-8");
temp = xbmc.translatePath(os.path.join(profile, "temp","")).decode("utf-8");
        
sys.path.append(resource)

import TraduttoriAnonimi

def log(msg):
    xbmc.log(("""*** [{}] -> {}""".format(scriptname,msg)).encode("utf-8"), level = xbmc.LOGNOTICE)
    
def notify(msg,header=scriptname,time=5000,image=None):
    if (image!=None):
        xbmc.executebuiltin((u"Notification({},{},{},{})".format(header, msg,time,image)).encode("utf-8"))
    else:
        xbmc.executebuiltin((u"Notification({},{},{})".format(header, msg, time)).encode("utf-8"))
        
def RetriveURL(url):
    try:
        headers={"user-agent": "Kodi-SubtitleService-TraduttoriAnonimi"};
        q=requests.get(url,headers=headers);
        return q;
    except:
        log(traceback.format_exc())
        notify("Errore di rete. controlla la tua connessione",time=3000)
        return None;
    
def normalizeString(String2Normalize):
    return unicodedata.normalize("NFKD",unicode(unicode(String2Normalize,"utf-8").encode("ascii","ignore")))

def GetParams():
    param={}
    if (len(sys.argv[2])>=2):
        for pairsofparam in sys.argv[2].replace("?","").split("&"):
            tmp=pairsofparam.split("=");
            if (len(tmp)==2):
                param[tmp[0]]=tmp[1];
    return param;

def search(item):
    try:
        if ('ita' in item['languages']):
            if (item['tvshow']):
                x=TraduttoriAnonimi.TraduttoriAnonimi();
                results=x.GrabSubtitle(item["tvshow"], int(item["season"]), int(item["episode"]));
                if (results!=None):
                    for result in results:
                        subs=download(result["URL"])
                        for sub in subs:
                            listitem = xbmcgui.ListItem(label='Italian',label2=os.path.basename(sub),thumbnailImage='it') #sub["Name"]
                            xbmcplugin.addDirectoryItem(handle = int(sys.argv[1]), url = "plugin://{}/?action=download&url={}".format(scriptid,sub), listitem = listitem, isFolder = False)#sub["URL"]
                        xbmcplugin.endOfDirectory(int(sys.argv[1]))	# send end of directory to XBMC
            else:
                notify("i sottotitoli sono disponibili solo per le serie tv il supporto ad i Film sara' aggiunto in futuro",time=12000)
                log('TraduttoriAnonimi only works with tv shows. Skipped')
        else:
            notify('i sottotitoli sono disponibili solo in italiano controlla le tue impostazioni [Video->Sottotitoli->Lingue per cui scaricare i sottotitoli]',time=17000)
            log('TraduttoriAnonimi only works with italian. Skipped')
    except requests.ConnectionError:
        log(traceback.format_exc())
        notify("Errore di rete. controlla la tua connessione",time=3000)
        
def download(url):
    log("Downloading => {}".format(url))
    if (os.path.isfile(url)):
        log("url is a local path")
        return [url]
    exts=["srt"]
    out=[]
    
    r=RetriveURL(url)
    if (r!=None):
        content=r.content;
        tmp=StringIO.StringIO(content)
        if (content[0]=="P"):
            log("ZipFile Detected")
            q=zipfile.ZipFile(tmp);
            for name in q.namelist():
                if (name.split(".")[-1] in exts):
                    q.extract(name, temp)
                    out.append(os.path.join(temp,name))
            q.close();
        else:
            log("Unpacked file detected")
            try:
                if (os.path.basename(url).split(".")[-1] in exts):
                    q=open(os.path.join(temp,os.path.basename(url)),"wb")
                    q.write(content)
                    q.close()
                    out.append(os.path.join(temp,os.path.basename(url)))
                else:
                    log("Downloaded File ({}) is not in exts[{}]".format(os.path.basename(url),str(exts)))
            except Exception as exc:
                try:q.close();
                except:pass
                raise exc;
    return out;

def main():
    log("Application version: {}".format(version))
    if (xbmc.Player().isPlayingVideo()):
        for x in [profile,temp]:
            if (not xbmcvfs.exists(x)):
                xbmcvfs.mkdirs(x)
    params = GetParams()
    
    if (params["action"] == "search" or params["action"] == "manualsearch"):
        item = {}
        item["mansearch"] = params["action"] == "manualsearch"
        
        if (item['mansearch']):
            notify("La Ricerca Manuale Non e' supportata ma verra' aggiunta in futuro",time=3000)
        
        item["season"] = str(xbmc.getInfoLabel("VideoPlayer.Season"));                              # Season
        item["episode"] = str(xbmc.getInfoLabel("VideoPlayer.Episode")).zfill(2);					# Episode
        item["tvshow"] = normalizeString(xbmc.getInfoLabel("VideoPlayer.TVshowtitle"));				# Show
        item["file_original_path"] = xbmc.Player().getPlayingFile().decode("utf-8");             	# Full path
        item["languages"] = [];
        
        if ("searchstring" in params):
            item["mansearch"] = True
            item["mansearchstr"] = urllib.unquote(params["searchstring"])
        
        for lang in urllib.unquote(params["languages"]).decode("utf-8").split(","):
            item["languages"].append(xbmc.convertLanguage(lang, xbmc.ISO_639_2))
        
        if (item["episode"].lower().find("s") > -1): # Check if season is "Special"
            item["season"] = "0"
            item["episode"] = item["episode"][-1:]
        search(item)
    
    elif (params["action"] == "download"):
        subs=download(params["url"])
        for sub in subs:
            listitem = xbmcgui.ListItem(label = sub)
            xbmcplugin.addDirectoryItem(handle = int(sys.argv[1]), url = sub, listitem = listitem, isFolder = False)
        xbmcplugin.endOfDirectory(int(sys.argv[1]))
        
main()