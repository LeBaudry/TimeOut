from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime, timedelta
import databases
import sqlalchemy
import json

# Configuration de l'API FastAPI
app = FastAPI()

# Modèles Pydantic pour les requêtes et les réponses
class BadgeageRequest(BaseModel):
    id_employe: int  # ajusté pour correspondre à la base de données

class BadgeageResponse(BaseModel):
    id_pointage: int
    id_employe: int  # ajusté pour correspondre à la base de données
    date_heure: datetime  # ajusté pour correspondre à la base de données
    type_pointage: int  # ajusté pour correspondre à la base de données (supposant que la valeur 'entrée' est 1 et 'sortie' est 0)

# Connexion à la base de données MariaDB
DATABASE_URL = "mysql://sam:250498@localhost/timout"
database = databases.Database(DATABASE_URL)
metadata = sqlalchemy.MetaData()

# Définition des tables avec les colonnes ajustées pour correspondre aux captures d'écran fournies
employes = sqlalchemy.Table(
    "employe", metadata,  # Le nom de la table doit correspondre à la base de données
    sqlalchemy.Column("id_employe", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("nom", sqlalchemy.String(255)),
    sqlalchemy.Column("prenom", sqlalchemy.String(255)),
    sqlalchemy.Column("numero_tel", sqlalchemy.String(20)),
    sqlalchemy.Column("email", sqlalchemy.String(255)),
    sqlalchemy.Column("adresse", sqlalchemy.String(255)),
    sqlalchemy.Column("ville", sqlalchemy.String(255)),
    sqlalchemy.Column("code_postal", sqlalchemy.String(10)),
)

badges = sqlalchemy.Table(
    "badge", metadata,  # Le nom de la table doit correspondre à la base de données
    sqlalchemy.Column("id_badge", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("id_employe", sqlalchemy.Integer, sqlalchemy.ForeignKey("employe.id_employe")),
    sqlalchemy.Column("code_badge", sqlalchemy.String(50)),
)

pointages = sqlalchemy.Table(
    "pointages", metadata,  # Le nom de la table doit correspondre à la base de données
    sqlalchemy.Column("id_pointage", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("id_badge", sqlalchemy.Integer, sqlalchemy.ForeignKey("badge.id_badge")),
    sqlalchemy.Column("date_heure", sqlalchemy.TIMESTAMP),  # ajusté pour correspondre à la base de données
    sqlalchemy.Column("type_pointage", sqlalchemy.Integer),  # ajusté pour correspondre à la base de données
)


@app.on_event("startup")
async def startup():
    await database.connect()

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
    
    # Récupération de tous les pointages pour cet employé à cette date
    query = pointages.select().where(
        (badges.c.id_employe == id_employe) &
        (sqlalchemy.func.date(pointages.c.date_heure) == date_obj.date())
    ).order_by(pointages.c.date_heure)
    pointages_employe = await database.fetch_all(query)

    # Calcul du temps total de travail
    temps_total = timedelta(0)
    dernier_pointage = None

    for pointage in pointages_employe:
        if dernier_pointage and pointage.type_pointage == 1:
            temps_total += pointage.date_heure - dernier_pointage.date_heure

        dernier_pointage = pointage if pointage.type_pointage == 0 else None

    # Ajustement pour la pause de midi
    if temps_total < timedelta(hours=8):  # Supposons une journée de travail de 8h
        temps_de_pause = timedelta(hours=1) - (temps_total - timedelta(hours=7))
        temps_total -= temps_de_pause

    # Calcul des heures supplémentaires si nécessaire
    heures_supplementaires = max(temps_total - timedelta(hours=8), timedelta(0))

    return {
        "id_employe": id_employe,
        "Date": date,
        "Temps_Travail": str(temps_total),
        "Heures_Supplementaires": str(heures_supplementaires)
    }

# Fonction auxiliaire pour générer un rapport d'horaires
@app.get("/generer-rapport/{id_employe}/{date_debut}/{date_fin}")
async def generer_rapport(id_employe: int, date_debut: str, date_fin: str):
    date_debut_obj = datetime.strptime(date_debut, "%Y-%m-%d")
    date_fin_obj = datetime.strptime(date_fin, "%Y-%m-%d")
    jour_courant = date_debut_obj
    rapport = []

    while jour_courant <= date_fin_obj:
        temps_travail = await calculer_temps_travail(id_employe, jour_courant.strftime("%Y-%m-%d"))
        rapport.append({
            "Date": jour_courant.strftime("%Y-%m-%d"),
            "Temps_Travail": temps_travail["Temps_Travail"],
            "Heures_Supplementaires": temps_travail["Heures_Supplementaires"]
        })
        jour_courant += timedelta(days=1)

    return json.dumps(rapport, ensure_ascii=False)