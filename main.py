import math 
from M5 import *
import time
import machine
import network
from hardware import *
from Secrets import WIFI_SSID, WIFI_PASSWORD, LAT_DOM, LON_DOM, RAYON_PLANE
import requests as requests
import _thread as th
# URL permettant le contrôle des calculs angle & distance https://www.sunearthtools.com/fr/tools/distance.php


def get_airport_name(code):
    global airport_name
    
    if code=="":
        return "N/A"
    
    if code in airport_name:
        return airport_name[code]
    else:
        #on va chercher le vol
        headers = {
        #"accept-encoding": "gzip, br",
        "accept-language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "cache-control": "max-age=0",
        "origin": "https://www.flightradar24.com",
        "referer": "https://www.flightradar24.com/",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "user-agent": "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36"}

        URL='https://www.flightradar24.com/airports/traffic-stats/?airport='+code
        reponse=requests.get(URL,headers=headers).json()

        airport_name[code]=reponse['details']['name']
        #print(airport_name)
        return reponse['details']['name']

def bound_calculation(lat,lon,rayon):
    # https://www.sunearthtools.com/fr/tools/distance.php
    # To determine the destination point, knowing the starting point the direction θ and the distance d, we use the following formula:
    # latB = asin( sin( latA) * cos( d / R ) + cos( latA ) * sin( d / R ) * cos( θ ))
    # lonB = lonA + atan2(sin( θ ) * sin( d / R ) * cos( latA ), cos( d / R ) − sin( latA ) * sin( latB ))
    
    R = 6378137 # rayon terrestre
    angle=0 # lat min
    lat_max = math.asin(math.sin(math.radians(lat)) * math.cos( rayon / R ) + math.cos( math.radians(lat) ) * math.sin( rayon / R ) * math.cos( angle ))
    angle=180 # lat max
    lat_min = math.asin(math.sin(math.radians(lat)) * math.cos( rayon / R ) + math.cos( math.radians(lat) ) * math.sin( rayon / R ) * math.cos( angle ))
    
    angle=math.radians(90)
    lon_max = math.radians(lon) + math.atan2(math.sin(angle)*math.sin(rayon/R)*math.cos(math.radians(lat)), math.cos(rayon / R )-(math.sin(math.radians(lat)) * math.sin( math.radians(lat))))
    
    angle=math.radians(270)
    lon_min = math.radians(lon) + math.atan2(math.sin(angle)*math.sin(rayon/R)*math.cos(math.radians(lat)), math.cos(rayon / R )-(math.sin(math.radians(lat)) * math.sin( math.radians(lat))))
    
    return math.degrees(lat_min),math.degrees(lat_max),math.degrees(lon_min),math.degrees(lon_max)

def distanceGPS(latA, longA, latB, longB):
    """Retourne la distance en mètres entre les 2 points A et B connus grâce à
       leurs coordonnées GPS (en radians).
    """
    # Rayon de la terre en mètres (sphère IAG-GRS80)
    RT = 6378137
    # angle en radians entre les 2 points
    S = math.acos(math.sin(math.radians(latA))*math.sin(math.radians(latB)) + math.cos(math.radians(latA))*math.cos(math.radians(latB))*math.cos(abs(math.radians(longB)-math.radians(longA))))
    # distance entre les 2 points, comptée sur un arc de grand cercle
    return S*RT

def angle_bearing(latA,longA,latB,longB): # cap de A vers B
    latA=math.radians(latA)
    longA=math.radians(longA)
    latB=math.radians(latB)
    longB=math.radians(longB)

    longDelta = longB - longA

    y = math.sin(longDelta) * math.cos(latB);
    x = math.cos(latA)*math.sin(latB) - math.sin(latA)*math.cos(latB)*math.cos(longDelta);
    Angle = math.degrees(math.atan2(y, x));
    if Angle<0:
      Angle+=360

    return Angle

def refresh_data(lat_min,lat_max,lon_min,lon_max):
    global tab_data
    # stock dans un tableau les valeurs souhaitées dans l'ordre des modes

    headers = {
            #"accept-encoding": "gzip, br",
            "accept-language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "cache-control": "max-age=0",
            "origin": "https://www.flightradar24.com",
            "referer": "https://www.flightradar24.com/",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "user-agent": "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36"}
    
    # refresh
    URL='https://data-cloud.flightradar24.com/zones/fcgi/feed.js?faa=1&satellite=1&mlat=1&flarm=1&adsb=1&gnd=0&air=1&vehicles=1&estimated=1&maxage=14400&gliders=1&stats=1&limit=5000&bounds='+str(lat_max)+'%2C'+str(lat_min)+'%2C'+str(lon_min)+'%2C'+str(lon_max)+'3'#2.7253206372680023'
    reponse=requests.get(URL,headers=headers).json()
    
    # parse du résultat
    tab_data=[]
    for cle,valeur in reponse.items():
        if cle!="full_count" and cle!="version" and cle!="stats":
            dist = distanceGPS(valeur[1],valeur[2], LAT_DOM, LON_DOM)
            angle=angle_bearing(LAT_DOM, LON_DOM,valeur[1],valeur[2])
            if dist<20000:
                #print("CallSign:",valeur[16], "Registration:",valeur[9],"Vol:",valeur[13], "Lat:",valeur[1],"Lon:",valeur[2],"Alt:",valeur[4],"Cap:",valeur[3],"Distance:",dist, "Angle tracé",angle )

                tab_point=[]
                tab_point.append(valeur[16]) #Callsign
                tab_point.append(valeur[1]) #Lat
                tab_point.append(valeur[2]) #Lon
                tab_point.append(valeur[3]) #Cap
                tab_point.append(angle) #Angle tracé
                tab_point.append(dist) # Distance
                tab_point.append(int(valeur[4]*0.3048))# Altitude mis en m
                tab_point.append(int(valeur[5]*1.852))# Vitesse mise en kmh
                tab_point.append(valeur[9]) #Registration
                tab_point.append(valeur[13]) #Flight Number
                tab_point.append(valeur[11]) #Origin
                tab_point.append(valeur[12]) #Dest
                tab_point.append(valeur[8]) #Aircraft type
                tab_data.append(tab_point)
                #print(tab_point)
    #print(tab_data)

def txt_mode(item): #['Callsign','Coord','Cap','Distance','Alt','Speed','Registration','Flight number','Origine','Destination','Aircraft','None']
    global mode
    if mode==0:
        return item[0]
    elif mode==1:
        return str(round(item[1],2))+':'+str(round(item[2],2))
    elif mode==2:
        return str(int(item[3]))+"°"
    elif mode==3:
        return str(int(item[5]))+'m'
    elif mode==4:
        return str(round(item[6],2))+'m' #à mettre en m
    elif mode==5:
        return str(round(item[7],2))+'km/h' # speed
    elif mode==6:
        return item[8]
    elif mode==7:
        return item[9]
    elif mode==8:
        return get_airport_name(item[10]) #origine
    elif mode==9:
        return get_airport_name(item[11]) #destination
    elif mode==10:
        return item[12] #Aircraft
    elif mode==11:
        return "" #None
    else:
        return "N/A"

def th_button():
    global continuer,mode,tab_mode
    rotary = Rotary()
    r_count=0
    M5.update() # pour virer le long click de lancement
    while continuer:
        if M5.Touch.getCount()>0 and M5.Touch.getDetail()[4]==True:
            print("Touched")
            time.sleep_ms(200) # pour ne pas capter plusieurs fois le touch
        rot_temp=rotary.get_rotary_value()
        if rot_temp<r_count:
            mode-=1
            if mode<0:
                mode=len(tab_mode)-1
            r_count=rot_temp
            print("Mode",mode,'-',tab_mode[mode])
        elif rot_temp>r_count:        
            mode+=1
            if mode>len(tab_mode)-1:
                mode=0
            r_count=rot_temp
            print("Mode",mode,'-',tab_mode[mode])
        elif BtnA.wasSingleClicked():
            print("Clic")
            #continuer=False
            
        time.sleep_ms(10)
        M5.update()

def draw_plane(x,y,cap):
    size=5
    cap=90-cap #0° Nord correspond à 90° et on tourne dans l'autre sens
    
    #pointe de l'avion
    x1=x+math.cos(math.radians(cap))*size
    y1=y-math.sin(math.radians(cap))*size
    
    #coin bas gauche
    x2=x+math.cos(math.radians(cap+90+45))*size
    y2=y-math.sin(math.radians(cap+90+45))*size
    
    #coin bas droit
    x3=x+math.cos(math.radians(cap-90-45))*size
    y3=y-math.sin(math.radians(cap-90-45))*size    
    
    Lcd.fillTriangle(x0=int(x1),y0=int(y1),x1=int(x2),y1=int(y2),x2=int(x3),y2=int(y3),color=0xff0000)
    Lcd.fillTriangle(x0=int(x),y0=int(y),x1=int(x2),y1=int(y2),x2=int(x3),y2=int(y3),color=0x000000) # pour faire en noir le triangle interne
    
    return

def launch():
    global continuer, tab_data,mode,tab_mode,airport_name
    continuer = True
    rayon=110
    machine.freq(240000000)
    tab_data=[]
    th.start_new_thread(th_button,())
    
    tab_mode=['Callsign','Coord','Cap','Distance','Alt','Speed','Registration','Flight number','Origine','Destination','Aircraft','']
    mode=0

    airport_name={'CDG':'Paris Charles de Gaulle Airport','LBG':'Paris Le Bourget Airport','ORY':'Paris Orly Airport'}

    # connexion wifi
    wlan = network.WLAN(network.STA_IF) # create station interface

    if wlan.isconnected():
        wlan.disconnect()

    wlan.active(True)       # activate the interface
    #wlan.scan()             # scan for access points
    #print(wlan.isconnected())      # check if the station is connected to an AP
    wlan.connect(WIFI_SSID, WIFI_PASSWORD) # connect to an AP
    #print(wlan.ifconfig())         # get the interface's IP/netmask/gw/DNS addresses

    #print(wlan.isconnected())
    #print("Local time before synchronization：%s" %str(time.localtime()))
    while not wlan.isconnected():
     time.sleep_ms(100)    

    lat_min,lat_max,lon_min,lon_max=bound_calculation(LAT_DOM,LON_DOM,RAYON_PLANE)

    while continuer:
        
        refresh_data(lat_min,lat_max,lon_min,lon_max)
  
        Lcd.clear()        

        # le radar, tracé après pour être par dessus
        Lcd.fillCircle(x=120,y=120,r=2,color=0x00ff00) # centre
        Lcd.drawCircle(x=120,y=120,r=110,color=0x00ff00)
        Lcd.drawCircle(x=120,y=120,r=83,color=0x00ff00)
        Lcd.drawCircle(x=120,y=120,r=55,color=0x00ff00)
        Lcd.drawCircle(x=120,y=120,r=27,color=0x00ff00)

        # les quartier
        Lcd.drawLine(x0=120,y0=10,x1=120,y1=230,color=0x00aa00)
        Lcd.drawLine(x0=10,y0=120,x1=230,y1=120,color=0x00aa00)

        # Le mode
        Lcd.setTextColor(0x555555)
        Lcd.drawCenterString(text=tab_mode[mode],x=120,y=180)
        Lcd.setTextColor(0xffffff)

        #affichage des points
        for item in tab_data:
            #print(item)
            # pour tracer le point,  faire angle=90-angle (différence entre l'angle géométrique et l'angle du cap par rapport au nord). Nord = 90° trigo, et ça tourne dans l'autre sens
            angle_trace=90-item[4]
            x=120+math.cos(math.radians(angle_trace))*(item[5]*rayon/20000)
            y=120-math.sin(math.radians(angle_trace))*(item[5]*rayon/20000)
            draw_plane(x,y,item[3])
            #libellé
            Lcd.setFont(Lcd.FONTS.EFontCN24)
            Lcd.setTextSize(0.6)
            Lcd.drawString(text=txt_mode(item),x=int(x)+5,y=int(y)+5)
            

        time.sleep_ms(2000)


    wlan.disconnect()
    Lcd.clear()

if __name__ == '__main__':
    launch()

