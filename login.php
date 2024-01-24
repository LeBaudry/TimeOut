<?php
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    // Récupérer les données du formulaire
    $email = $_POST['email'];
    $password = $_POST['password'];

    // URL de l'API pour l'authentification
    $apiUrl = 'http://10.191.14.111:8000/login';

    // Données à envoyer à l'API
    $postData = array(
        'email' => $email,
        'password' => $password
    );

    // Configuration de la requête cURL
    $ch = curl_init($apiUrl);
    curl_setopt($ch, CURLOPT_POST, 1);
    curl_setopt($ch, CURLOPT_POSTFIELDS, $postData);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);

    // Exécution de la requête
    $response = curl_exec($ch);
    curl_setopt($ch, CURLOPT_VERBOSE, 1);
    $response = curl_exec($ch);
    $info = curl_getinfo($ch);
    print_r($info);

    // Gérer la réponse de l'API
    if ($response === false) {
        // Gérer les erreurs cURL
        echo 'Erreur lors de la connexion à l\'API: ' . curl_error($ch);
    } else {
        // La réponse est une chaîne JSON, vous pouvez la décoder si nécessaire
        $jsonData = json_decode($response, true);

        // Vérifier si l'authentification a réussi
        if (isset($jsonData['id_employe']) && isset($jsonData['type_employe'])) {
            echo 'Connexion réussie. ID Employé: ' . $jsonData['id_employe'] . ', Type Employé: ' . $jsonData['type_employe'];
        } else {
            echo 'Identifiants invalides';
        }
        
        // Vérifier le type d'employé et rediriger en conséquence
        if ($jsonData['type_employe'] === 'normal') {
            header("Location: home_page_employe.php");
            exit();
        } elseif ($jsonData['type_employe'] === 'admin') {
            header("Location: home_page_admin.php");
            exit();
        } else {
            echo 'Type d\'employé non reconnu';
        }
    }

    // Fermer la session cURL
    curl_close($ch);
}
?>
