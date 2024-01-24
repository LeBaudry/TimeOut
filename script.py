import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522
import mysql.connector
from datetime import datetime
import time

# Désactiver les avertissements GPIO
GPIO.setwarnings(False)

# Initialiser le lecteur RFID
reader = SimpleMFRC522()

# Configuration de la connexion à la base de données
db_config = {
    "host": "192.168.1.62",
    "user": "axel",
    "password": "sam",
    "database": "timeOut"
}

# Fonction pour récupérer l'ID du badge à partir de la base de données
def get_badge_id(code_badge):
    try:
        # Se connecter à la base de données
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()

        # Exécuter la requête SQL
        query = "SELECT id_badge FROM badge WHERE code_badge = %s"
        cursor.execute(query, (code_badge,))
        result = cursor.fetchone()

        # Fermer la connexion à la base de données
        cursor.close()
        connection.close()

        # Retourner l'ID du badge s'il existe, sinon None
        return result[0] if result else None

    except mysql.connector.Error as err:
        print(f"Erreur MySQL: {err}")
        return None


def get_pointage_type(id_badge):
    try:
        # Se connecter à la base de données
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()

        # Exécuter la requête SQL
        query = "SELECT type_pointage FROM pointage WHERE id_badge = %s ORDER BY date_heure DESC LIMIT 1"
        cursor.execute(query, (id_badge,))
        result = cursor.fetchone()

        # Fermer la connexion à la base de données
        cursor.close()
        connection.close()

        # Retourner le type_pointage s'il existe, sinon None
        return result[0] if result else None

    except mysql.connector.Error as err:
        print(f"Erreur MySQL: {err}")
        return None



# Fonction pour insérer un nouveau pointage dans la base de données
def insert_pointage(id_badge, date_heure, type_pointage):
    try:
        # Se connecter à la base de données
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()

        # Exécuter la requête SQL d'insertion
        query = "INSERT INTO pointage (id_badge, date_heure, type_pointage) VALUES (%s, %s, %s)"
        cursor.execute(query, (id_badge, date_heure, type_pointage))

        # Valider la transaction
        connection.commit()

        # Fermer la connexion à la base de données
        cursor.close()
        connection.close()

    except mysql.connector.Error as err:
        print(f"Erreur MySQL: {err}")


def get_current_datetime():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")



try:
    while True:
        # Attendre la détection d'un badge
        print("Attente d'un badge...")
        id, code_badge = reader.read()
        code_badge = id
        # Afficher l'ID du badge
        print("Badge détecté avec l'ID :", id)

        # Afficher le code_badge du badge
        if code_badge:
            print("Code du badge :", code_badge)

            # Récupérer l'ID du badge depuis la base de données
            badge_id = get_badge_id(code_badge)
            if badge_id is not None:
                print("ID du badge dans la base de données :", badge_id)

                # Récupérer le type_pointage depuis la base de données
                type_pointage = get_pointage_type(badge_id)

                # Afficher le type_pointage
                print("Type de pointage récupéré :", type_pointage)

                # Modifier type_pointage_badge en fonction des résultats
                if type_pointage == 1:
                    type_pointage_badge = False
                elif type_pointage == 0:
                    type_pointage_badge = True
                else:
                    type_pointage_badge = True  # Aucun pointage existant, mettre à True

                # Afficher type_pointage_badge
                print("Nouvelle valeur de type_pointage_badge :", type_pointage_badge)
                # Obtenir la date et l'heure actuelles au format compatible avec le timestamp de MariaDB
                date_heure = get_current_datetime()

                # Insérer le nouveau pointage dans la base de données
                insert_pointage(badge_id, date_heure, type_pointage_badge)

            else:
                print("Aucun ID trouvé dans la base de données pour ce code_badge.")


        # Attendre 10 secondes avant de lire le prochain badge
        time.sleep(10)


except KeyboardInterrupt:
    print("Arrêt du script. Nettoyage en cours...")
    GPIO.cleanup()
    print("Nettoyage terminé. Au revoir!")

