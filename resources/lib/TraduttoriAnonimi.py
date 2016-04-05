# -*- coding: utf-8 -*-
import xbmc
from bs4 import BeautifulSoup;
import requests,re,time,logging,os,urlparse;
import traceback
import json;

class LogStream(object):
    def write(self,data):
        xbmc.log(("""*** [TraduttoriAnonimiCore] -> {}""".format(data)).encode('utf-8'), level = xbmc.LOGNOTICE)
        
log=logging.getLogger("TraduttoriAnonimiCore")
log.setLevel(logging.DEBUG);
style=logging.Formatter("%(asctime)s {%(levelname)s} %(name)s.%(funcName)s() -->> %(message)s");
consoleHandler = logging.StreamHandler(LogStream());
consoleHandler.setFormatter(style)
log.addHandler(consoleHandler);

def nstring(s):
    try:
        return s.encode(errors="replace").replace("?"," ")
    except:
        try:
            return s.decode(errors="replace").replace(u"\ufffd\ufffd\ufffd"," ")
        except:
            return s;

class SearchableDict(dict):
    def __getitem__(self, token):
        p=re.compile(token,re.IGNORECASE)
        result=[];
        for x,y in self.items():
            if re.search(p,nstring(x)):
                result.append({"ShowName":x,"Object":y});
                
        if (len(result)==0):
            result=None;
        
        return result;
        
class SearchableList(list):
    def __getitem__(self, token):
        p=re.compile(token,re.IGNORECASE)
        result=[];
        for x in self:
            if re.search(p,x):
                result.append(x);
                
        if (len(result)==0):
            result=None;
        
        return result;
        

def RetriveURL(url):
    try:
        headers={'user-agent': 'Kodi-SubtitleService-TraduttoriAnonimi'};
        q=requests.get(url,headers=headers);
        return q;
    except Exception as exc:
        log.error(traceback.format_exc())
        #notify("Errore di rete. controlla la tua connessione",time=3000)
        raise exc;
    
def RetriveURLx(url):
    headers={'user-agent': 'Kodi-SubtitleService-TraduttoriAnonimi'};
    start=time.time()
    log.info("Downloading HTML of {}".format(url));
    q=requests.get(url,headers=headers);
    log.info("HTML of {} Downloaded Successfully, Elapsed Time {}secs".format(url,time.time()-start));
    return (q.text,q);

class TraduttoriAnonimi(object):
    
    class Show(object):
    
        def __str__(self):
            return "<TraduttoriAnonimiShow -> {} >".format(nstring(self._ShowName));
        
        def __repr__(self):return self.__str__();
        
        def __init__(self,ShowName,url,BaseURL,autoload=False):
            self._Loaded=False;
            self.BaseURL="http://traduttorianonimi.weebly.com/"
            self.url=url;
            self.ShowName=ShowName;
            self.Seasons={};
            if (autoload==True):
                self.Load();
        
        @property    
        def ShowName(self):
            if (self._Loaded==False):
                self.Load();
            return self._ShowName;
        
        @ShowName.setter
        def ShowName(self,value):
            self._ShowName=value;
            
        @property    
        def Seasons(self):
            if (self._Loaded==False):
                self.Load();
            return self._Seasons;
        
        @Seasons.setter
        def Seasons(self,value):
            self._Seasons=value;
            
        def GetSeason(self,SeasonNumber):
            return self.Seasons[SeasonNumber];
        
        def GetEpisodeSubtitleURL(self,season,episode):
            return self.Seasons[season][episode];
        
        def Load(self):
            self._Loaded="Loading";
            regex=re.compile("(?:.+\/)(?P<tvshowname>.+)(?:(?:s|\.)|\.s|\.so)(?P<season>\d+)(?:x|e|\.x|\.e)(?P<episode>\d+)", re.IGNORECASE);
            c=0;
            self.Seasons={};
            while (1):
                c+=1;
                r=RetriveURL(urlparse.urljoin(self.url,str(c)));
                if (r!=None and r.status_code!=404):
                    html=r.content;
                else:
                    break;
                self.parser=BeautifulSoup(html,"html.parser");
                for tag in self.parser.find("td",{"valign":"top"}).findAll("a"):
                    if tag.attrs["href"].endswith(".srt"):
                        m=regex.search(tag.attrs["href"])
                        if (m):
                            if (int(m.group("season")) not in self.Seasons):
                                self.Seasons[int(m.group("season"))]={};
                            if (int(m.group("episode")) not in self.Seasons[int(m.group("season"))]):
                                self.Seasons[int(m.group("season"))][int(m.group("episode"))]=[];
                            self.Seasons[int(m.group("season"))][int(m.group("episode"))].append(urlparse.urljoin(self.BaseURL,tag.attrs["href"]));                                
    
            self._Loaded=True;  
    
    def __init__(self,BaseURL="http://traduttorianonimi.weebly.com/",ShowsListFile=None,fastway=False):
        self.fastway=fastway
        self.ShowsListFile=ShowsListFile;
        
        if (self.ShowsListFile==None):
            self.fastway=False;
        
        self.BaseURL=BaseURL;
        self.ShowsList=SearchableDict()
        self.UpdateShowsList();
        
    def _WriteShowsListFile(self):
        if (self.ShowsListFile==None):
            log.error("ShowsListFile is None nothing to do.");
            return False;
        if (self.ShowsList in (dict(),None)):
            log.error("ShowsList is void ({}) nothing to do.");
            return False;
        log.info("Updating Showslist file...");
        log.info("Local Showlists file exits."if os.path.isfile(self.ShowsListFile) else "Local Showlists file doesn't exits.")
        try:
            f=open(self.ShowsListFile,"w")
            f.write(json.dumps({name:val.url for name,val in  self.ShowsList.items()}));
            log.info("Local file Updated");
            return True;
        except Exception as exc:
            try:f.close();
            except:pass;
            raise exc;
        
    def _GrabShowsListFromFile(self):
        try:
            f=open(self.ShowsListFile,"r")
            data=f.read();
            f.close();
            self.ShowsList=SearchableDict({name:self.Show(ShowName=name,url=url,BaseURL=self.BaseURL) for name,url in json.loads(data).items()})
            return self.ShowsList
        except Exception as exc:
            try:f.close();
            except:pass;
            raise exc;
        
        
    def _GrabShowsListFromWebsite(self):
        r=RetriveURL(self.BaseURL);
        if (r!=None):
            html=r.content;
            self.parser=BeautifulSoup(html,"html.parser");
            self.ShowsList=SearchableDict();
            for show in self.parser.find("p",{"class":"blog-category-list"}).findAll("a"):
                if (show.text not in ("All","Film")):
                    self.ShowsList[show.text]=TraduttoriAnonimi.Show(ShowName=show.text,url=urlparse.urljoin(self.BaseURL,show.attrs["href"])+"/",BaseURL=self.BaseURL)
        return self.ShowsList;
    
    def UpdateShowsList(self,forceupdate=None):
        if (forceupdate==None):
            forceupdate=not self.fastway
            
        if (forceupdate):
            log.info("forceupdate FLAG is Active.")
            
        if (self.ShowsListFile==None):
            log.info("ShowListFile is None, so it's Disabled")
        else:
            log.info("Local Showlists file exits."if os.path.isfile(self.ShowsListFile) else "Local Showlists file doesn't exits.")
        if (forceupdate==False and os.path.isfile(self.ShowsListFile)):
            log.info("Tring to use local file....")
            try:
                self._GrabShowsListFromFile()
            except:
                log.error(traceback.format_exc)
                log.error("Showslist may be corrupted, will be recreated");
                log.debug("deleting corrupted file")
                os.remove(self.ShowsListFile)
                return self.UpdateShowsList(forceupdate=True)
        else:
            log.info("Tring to get showslist file from website....")
            try:
                self._GrabShowsListFromWebsite()
                self._WriteShowsListFile();
            except Exception as exc:
                log.error("Showslist can't be retrived");
                raise exc;

        return self.ShowsList;
    
    def GetShow(self,ShowName):
        try:
            return self.ShowsList[ShowName]
        except:
            return None;
    
    def SearchSubtitles(self,ShowName,Season,Episode):
        bests=[];
        results=self.ShowsList[ShowName];
        if (results!=None):
            for result in results:
                obj=result["Object"];
                obj.Load()
                if Season in obj.Seasons:
                    if (Episode in obj.Seasons[Season]):
                        for suburl in obj.Seasons[Season][Episode]:
                            bests.append({"Name":os.path.basename(suburl),"URL":suburl});
        return bests;
            
            

