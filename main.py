from fastapi import FastAPI, HTTPException, Form, Depends
import mysql.connector
from pydantic import BaseModel
from datetime import datetime, timedelta
import databases
from sqlalchemy import Table, Column, Integer, String, TIMESTAMP, ForeignKey, create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
import json
import sqlalchemy



# Configuration de l'API FastAPI
app = FastAPI()

Base = declarative_base()

# Connexion à la base de données MariaDB
DATABASE_URL = "mysql://axel:sam@10.191.14.111:3306/timeOut"
engine = create_engine(DATABASE_URL)
metadata = MetaData(bind=engine)


database = databases.Database(DATABASE_URL, backend="mysql")
# Ajoutez la configuration de la base de données
db_config = {
    "host": "10.191.14.111",
    "user": "axel",
    "password": "sam",
    "database": "timeOut"
}






# Modèles Pydantic pour les requêtes et les réponses
class BadgeageRequest(BaseModel):
    id_employe: int  # ajusté pour correspondre à la base de données

class EmployeResponse(BaseModel):
    nom: str
    prenom: str
    dernier_pointage: datetime
    type_pointage: str

class BadgeageResponse(BaseModel):
    id_pointage: int
    id_employe: int  # ajusté pour correspondre à la base de données
    date_heure: datetime  # ajusté pour correspondre à la base de données
    type_pointage: int  # ajusté pour correspondre à la base de données (supposant que la valeur 'entrée' est 1 et 'sortie' est 0)


# Définition des tables avec les colonnes ajustées pour correspondre aux captures d'écran fournies
# Définition des tables avec les colonnes ajustées pour correspondre aux captures d'écran fournies
employes = Table(
    "employe", metadata,  # Le nom de la table doit correspondre à la base de données
    Column("id_employe", Integer, primary_key=True),
    Column("nom", String(255)),
    Column("prenom", String(255)),
    Column("numero_tel", String(20)),
    Column("email", String(255)),
    Column("adresse", String(255)),
    Column("ville", String(255)),
    Column("code_postal", String(10)),
)

badges = Table(
    "badge", metadata,  # Le nom de la table doit correspondre à la base de données
    Column("id_badge", Integer, primary_key=True),
    Column("code_badge", String(50)),
    Column("id_employe", Integer, ForeignKey("employe.id_employe")),
)

pointages = Table(
    "pointages", metadata,  # Le nom de la table doit correspondre à la base de données
    Column("id_pointage", Integer, primary_key=True),
    Column("id_badge", Integer, ForeignKey("badge.id_badge")),
    Column("date_heure", TIMESTAMP),  # ajusté pour correspondre à la base de données
    Column("type_pointage", Integer),  # ajusté pour correspondre à la base de données
)


def get_db():
    connection = mysql.connector.connect(**db_config)
    yield connection
    connection.close()

# ...

@app.on_event("startup")
async def startup():
    await database.connect()
    # Utilisez plutôt engine ici
    metadata.create_all(bind=engine)


@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()


# Fonction auxiliaire pour déterminer le type de badgeage
async def determinerTypeBadgeage(id_badge: int) -> int:
    query = pointages.select().where(pointages.c.id_badge == id_badge).order_by(sqlalchemy.desc(pointages.c.date_heure))
    dernier_pointage = await database.fetch_one(query)
    if not dernier_pointage:
        return 0
    return 1 if dernier_pointage.type_pointage == 0 else 0

# Route pour le badgeage manuel
@app.post("/badgeage-manuel/", response_model=BadgeageResponse)
async def badgeage_manuel(request: BadgeageRequest):
    query = badges.select().where(badges.c.id_employe == request.id_employe)
    badge = await database.fetch_one(query)
    if not badge:
        raise HTTPException(status_code=404, detail="Badge non trouvé")
    id_badge = badge.id_badge
    type_pointage = await determinerTypeBadgeage(id_badge)
    date_heure = datetime.now()
    query = pointages.insert().values(id_badge=id_badge, date_heure=date_heure, type_pointage=type_pointage)
    id_pointage = await database.execute(query)
    return {"id_pointage": id_pointage, "id_employe": request.id_employe, "date_heure": date_heure, "type_pointage": type_pointage}

# Fonction auxiliaire pour calculer le temps de travail pour un employé à une date donnée
@app.get("/calculer-temps-travail/{id_employe}/{date}")
async def calculer_temps_travail(id_employe: int, date: str):
    date_obj = datetime.strptime(date, "%Y-%m-%d")
    
    query = pointages.select().where(
        (badges.c.id_employe == id_employe) &
        (sqlalchemy.func.date(pointages.c.date_heure) == date_obj.date())
    ).order_by(pointages.c.date_heure.asc())
    pointages_employe = await database.fetch_all(query)

    temps_total = timedelta(0)
    temps_pause = timedelta(0)
    dernier_pointage_entree = None

    for pointage in pointages_employe:
        if pointage["type_pointage"] == 1:  # Entrée
            dernier_pointage_entree = pointage["date_heure"]
        elif pointage["type_pointage"] == 0 and dernier_pointage_entree:  # Sortie
            intervalle = pointage["date_heure"] - dernier_pointage_entree
            temps_total += intervalle
            dernier_pointage_entree = None  # Réinitialiser pour la prochaine période de travail

    # Calcul de la pause
    if len(pointages_employe) > 2:
        temps_pause = pointages_employe[2]["date_heure"] - pointages_employe[1]["date_heure"]

    # Calcul des heures supplémentaires
    heures_supplementaires = max(temps_total - timedelta(hours=8), timedelta(0))

    return {
        "id_employe": id_employe,
        "Date": date,
        "Temps_Travail": str(temps_total),
        "Temps_Pause": str(temps_pause),
        "Heures_Supplementaires": str(heures_supplementaires)
    }

# Fonction auxiliaire pour générer un rapport d'horaires
@app.get("/generer-rapport/{id_employe}/{date_debut}/{date_fin}")
async def generer_rapport(id_employe: int, date_debut: str, date_fin: str):
    date_debut_obj = datetime.strptime(date_debut, "%Y-%m-%d")
    date_fin_obj = datetime.strptime(date_fin, "%Y-%m-%d")
    jour_courant = date_debut_obj
    rapport = []
    total_temps_travail = timedelta(0)
    total_heures_supplementaires = timedelta(0)

    while jour_courant <= date_fin_obj:
        temps_travail_jour = await calculer_temps_travail(id_employe, jour_courant.strftime("%Y-%m-%d"))
        temps_travail = datetime.strptime(temps_travail_jour["Temps_Travail"], "%H:%M:%S")
        heures_supplementaires = datetime.strptime(temps_travail_jour["Heures_Supplementaires"], "%H:%M:%S")

        total_temps_travail += timedelta(hours=temps_travail.hour, minutes=temps_travail.minute, seconds=temps_travail.second)
        total_heures_supplementaires += timedelta(hours=heures_supplementaires.hour, minutes=heures_supplementaires.minute, seconds=heures_supplementaires.second)

        rapport.append({
            "Date": jour_courant.strftime("%Y-%m-%d"),
            "Temps_Travail": temps_travail_jour["Temps_Travail"],
            "Heures_Supplementaires": temps_travail_jour["Heures_Supplementaires"]
        })
        jour_courant += timedelta(days=1)

    rapport.append({
        "Total_Temps_Travail": str(total_temps_travail),
        "Total_Heures_Supplementaires": str(total_heures_supplementaires)
    })

    return json.dumps(rapport, ensure_ascii=False)

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.post("/login")
def login(email: str = Form(...), password: str = Form(...), db: mysql.connector.connection.MySQLConnection = Depends(get_db)):
    try:
        # Exécuter la requête SQL
        query = "SELECT id_employe, type_employe FROM employe WHERE email = %s AND password = %s"
        cursor = db.cursor()
        cursor.execute(query, (email, password))
        result = cursor.fetchone()

        # Vérifier si les informations de connexion sont valides
        if result:
            id_employe, type_employe = result
            return {"id_employe": id_employe, "type_employe": type_employe}
        else:
            raise HTTPException(status_code=401, detail="Identifiants invalides")

    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"Erreur MySQL: {err}")
    finally:
        cursor.close()

