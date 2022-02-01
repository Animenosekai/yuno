# j'importe les modules que je vais utiliser par la suite
import datetime
import typing  # typing contient des objets pour indiquer à l'éditeur de texte/code quels sont les types de variable

import requests  # requests est un module qui doit être téléchargé avec pip


class WeatherAppError(Exception):  # je créer un object d'erreur qui est custom pour le script que je suis entrain d'écrire (pour pouvoir vérifier dans les try...except plus tard si l'erreur vient de ce script)
    pass


class RequestError(WeatherAppError):  # je créer un object d'erreur, qui est hérité de WeatherAppError, comme ça il va être capturé par un try...except WeatherAppError mais aussi par try...except RequestError (ça rend le code plus lisible et robuste)
    def __init__(self, code: int, *args: object) -> None:
        self.code = code
        super().__init__(*args)


class LocationNotFound(WeatherAppError):  # pareil pour la localisation
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


# c'est juste un type de variable qui ne peux contenir que quelques "strings" (pour éviter que ce soit trop global, pour savoir que tel attribut ne peut avoir que certaines valeurs)
WeatherStateType = typing.Literal["sn", "sl", "h", "t", "hr", "lr", "s", "hc", "lc", "c"]


# ce sont les différentes valeurs encore une fois, mais on pourra utiliser comme ça: data.state == WeatherState.SNOW pour savoir si il neige (ça rend le code plus lisible)
# on remarque que c'est une classe/un object spécial, et ces attributs (autres que ceux de base qui sont assignés à tous les objets) seront SNOW, SLEET, HAIL, THUNDERSTORM, etc.
# tu peux par ailleurs regarder les différents attributs d'un objet en utilisant la fonction intégrée dir(objet), ici ça serait dir(WeatherState) par exemple, ou si tu utilises translatepy, t = Translate() ; dir(t) pour voir toutes les fonctions de "t" (qui sont toutes les fonctions initialisées en faisant Translate())
class WeatherState:
    SNOW = "sn"
    SLEET = "sl"
    HAIL = "h"
    THUNDERSTORM = "t"
    HEAVY_RAIN = "hr"
    LIGHT_RAIN = "lr"
    SHOWERS = "s"
    HEAVY_CLOUD = "hc"
    LIGHT_CLOUD = "lc"
    CLEAR = "c"

# Location est un objet qui contient les informations sur une localisation


class Location:
    def __init__(self, data: dict = None) -> None:
        # si data est None ou un dictionaire vide, alors data == {} (un dictionnaire vide)
        data = data or {}  # ceci marche parce que quelque chose de vide, ou None est égal à "False" quand tu le check avec un if...else
        # .get permet de récupérer une valeur dans un dictionnaire, et si elle n'existe pas, on renvoie une valeur par défaut
        self.name = data.get("title", "")
        self.type = data.get("location_type", "")
        self.id = data.get("woeid", None)
        # ici je fais ce qui s'appelle du "unpacking" ou "destructuring" (unpacking est une méthode qui permet de décomposer une liste en plusieurs variables)
        # .split est une fonction d'un string qui permet de séparer un string en plusieurs strings, ici on sépare la latitude et la longitude par une virgule
        self.latitude, self.longitude = data.get("latt_long", "0,0").split(",")
        # par exemple premiere_variable, deuxieme_variable = [1, 2]
        # premiere_variable == 1
        # deuxieme_variable == 2

    # __repr__ est une fonction spéciale qui permet de "représenter" un objet par un string, c'est ce qui est affiché quand tu fais print(objet)
    def __repr__(self) -> str:
        return f"Location({self.name})"  # self est un paramètre spécial qui est l'objet actuel, l'état actuel de l'objet


class WeatherData:
    def __init__(self, data: dict) -> None:
        data = data if data else {}  # pareil que tout à l'heure quand j'ai dit que {} ou None est égal à False dans if...else
        self._id = data.get("id", -1)
        self.state: WeatherStateType = data.get("weather_state_abbr", "")
        self.state_name = data.get("weather_state_name", "")
        self.temperature = data.get("the_temp", 0)
        self.humidity = data.get("humidity", 0)
        self.wind_speed = data.get("wind_speed", 0)
        self.wind_direction = data.get("wind_direction", "N/A")
        self.air_pressure = data.get("air_pressure", 0)
        self.visibility = data.get("visibility", 0)
        # datetime est une classe du module datetime qui représente une date et une heure (d'où le nom) et .strptime est une fonction qui permet de convertir un string formatté dans un certain format (à retrouver sur https://strftime.org) en datetime
        # "%Y-%m-%d" est le format de la date soit année-mois-jour, et "0000-00-00" est la valeur par défaut si la date n'est pas trouvée
        self.date = datetime.datetime.strptime(data.get("applicable_date", "0000-00-00"), "%Y-%m-%d")


# fonction qui va chercher une localisation, qui prend "query" (un string) en paramètre et qui renvoie une liste de Location
def search_location(query: str) -> list[Location]:
    # on fait une requête à l'API pour récupérer les informations sur la localisation
    response = requests.get(f"https://www.metaweather.com/api/location/search/?query={query}")
    # si le satut de la réponse est supérieur à 400, c'est qu'il y a eu une erreur (voir https://www.w3.org/Protocols/rfc2616/rfc2616-sec10.html pour la spécification exacte) mais sinon il y a des sites qui résume le bail simplement (https://developer.mozilla.org/en-US/docs/Web/HTTP/Status, https://httpstatuses.com, etc.)
    if response.status_code >= 400:
        # il y a une erreur donc je "raise" une erreur, j'arrête le code là et je dis à tout le monde qu'il y a une erreur (c'est ce qui est "catch" par le try...except)
        raise RequestError(response.status_code, "An error occured while getting the location code")
    data = response.json()  # je convertis les données en JSON (https://developer.mozilla.org/en-US/docs/Learn/JavaScript/Objects/JSON)
    # je renvoie une liste en convertissant toutes les données de la liste renvoyée par le serveur de metaweather en objets "Location" (que j'ai défini plus haut)
    # Quand je fais Location(qqchose) qqchose va être passé dans le __init__ de Location définie plus haut, et ça va "instatiate" (créer) un nouvel objet
    return [Location(location) for location in data]

# weather est une fonction qui va chercher les informations sur la météo d'une localisation, qui prend "location" (une ville par exemple) en paramètre et qui renvoie une liste de WeatherData


def weather(location: str) -> list[WeatherData]:
    search_results = search_location(location)  # je cherche les différents résultats de recherche de la ville/pays/etc. avec la fonction précédente
    if len(search_results) == 0:  # si j'ai 0 résultats, alors je crée une erreur, pour avertir tout le monde qu'il y a un problème
        raise LocationNotFound(f"We couldn't find the given location ({location})")
    # sinon je fais une requête à l'API pour récupérer les informations sur la météo de la ville/pays/etc.
    response = requests.get(f"https://www.metaweather.com/api/location/{search_results[0].id}/")
    if response.status_code >= 400:  # si il y a une erreur (comme vu en haut)
        # alors dire qu'il y a une erreur
        raise RequestError(response.status_code, f"An error occured while getting the weather information for {search_results[0].name}")
    # sinon je créé une liste d'objet WeatherData avec les données de météo renvoyées
    return [WeatherData(weather) for weather in response.json()["consolidated_weather"]]


# fonction très simple qui permet de pas avoir à taper tout le temps le même code pour print avec des espaces devant
# *args est un paramètre particulier qui permet de prendre tout ce qui est passé en paramètre sans nom et de le mettre dans une liste
# exemple: indent(1, "a", "b", "c") va avoir args == [1, "a", "b", "c"]
def indent(*args) -> str:
    # ' ' * 4 est une string avec 4 espaces, et ' '.join([str(arg) for arg in args]) ça va "joindre" tous les éléments de la liste dans un seul string, éléments séparés par un espace
    print(f"{' ' * 4}{' '.join([str(arg) for arg in args])}")


while True:  # la condition est toujours vraie puisque True renvoie True (logique), donc c'est une boucle infinie
    print("What is the location you want to know the weather for?")  # je demande quelle localisation je veux connaitre
    location = input("> ")  # je demande à l'utilisateur de taper son choix
    print("This is the forecast for the next 5 days:")
    try:  # j'essaye (pour pas tout faire planter si il y a une erreur)
        for data in weather(location):  # pour chaque donnée de météo, je l'affiche
            # strftime permet de formatter la date, ici on veut le nom du jour, le mois et le jour (ça convertit un objet datetime en string avec le format donné)
            print("For", data.date.strftime("%A %B %-d"))
            # ça c'est les attributs de l'objet WeatherData (avec un éditeur comme VS Code, il peut te suggérer des propositions d'attributs grâce à ce qu'on a déinit plus haut)
            indent("State:", data.state_name)
            indent("Temperature:", round(data.temperature, 2), "°C")  # j'arrondis la température à 2 chiffres après la virgule
            indent("Humidity:", round(data.humidity, 2), "%")
            indent("Wind speed:", round(data.wind_speed), "mph")
            indent("Wind direction:", round(data.wind_direction), "°")
            indent("Air pressure:", round(data.air_pressure), "mbar")
            indent("Visibility:", round(data.visibility, 2), "miles\n")  # \n est un retour à la ligne
    except LocationNotFound as err:  # je "catch" l'erreur LocationNotFound (qui est une erreur que j'ai créée) et je la stocke dans la variable "err"
        print("An error occured while searching for the location")
        print(err)  # err est "l'exception", l'objet d'erreur qui a été "catch", qui a été capturée
    except WeatherAppError:
        print("An error occured while getting the weather data")
    except Exception:  # Exception est l'exception / l'erreur générale (qui n'est pas une erreur que j'ai créée)
        print("An unknown error occured")

    # ici ça va revenir au début de la boucle
