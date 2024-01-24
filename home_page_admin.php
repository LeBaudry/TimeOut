<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>TimeOut</title>
    <link rel="stylesheet" href="page_admin.css">
</head>
<body>
    <header>
        
    </header>
    <main>
        <h1>TimeOut</h1>
    <h2>Votre plateforme centralisée : employés consultez vos heures, administrateurs gérez-les en un clic!</h2>
    <form id="from_connection" action="authentification.php" method="post">
            <label class="lbl_from_index" id="margin" for="email">Adresse E-mail :</label><br><br>
            <input class="inpt_from_index" placeholder="Adresse e-mail" type="email" id="email" name="email"
                required><br><br>
    
            <label class="lbl_from_index" for="password">Mots de passe </label><br><br>
            <input class="inpt_from_index" placeholder="Mots de passe" type="password" id="password" name="password" required><br><br>
    
            <input type="submit" class="button_index" value="Se Connecter">
        </form>
    </main>

</body>
</html>