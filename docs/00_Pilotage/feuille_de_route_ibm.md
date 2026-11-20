# Feuille de route Architecture : Simulation IBM/ABM

**Contexte :** Modélisation dynamique de l'Aigle de Bonelli dans le massif des Alpilles.

**Principe directeur :** Séparation stricte entre le **moteur de simulation**, les **données environnementales** et les **comportements des espèces** (architecture modulaire).

## Jalon 1 : Spécification Conceptuelle (Protocole ODD)

Details dans [[jalon_1_specifications_odd]].

Avant d'écrire la moindre ligne de code, figer les règles métier et le périmètre scientifique.

* **Définition des échelles :** Résolution spatiale (ex. grille de 50m x 50m ou vecteur) et pas de temps (ex. heure, jour, saison).

* **Inventaire des entités :** Lister les variables d'état des agents (âge, sexe, énergie, statut reproducteur) et de l'environnement (topographie, falaises, occupation du sol).

* **Diagrammes de flux :** Schématiser le cycle de vie et la boucle de décision d'un pas de temps.

* **Critère de validation :** Document de spécification (type protocole ODD) validé, sans ambiguïté sur les interactions agent-environnement.

## Jalon 2 : Architecture & Contrats d'Interface (Le « Squelette »)

Figer l'organisation du code et les règles de communication entre modules avant de coder la biologie ou le terrain.

* **Décisions techniques (ADR) :** Trancher les choix d'ingénierie (taille de grille, pas de temps $\Delta t$) et créer l'arborescence des dossiers (`core/`, `agents/`, `environment/`, `configs/`).

* **Contrats d'interface (`Protocol`) :** Définir les méthodes standardisées d'échange (`agent.step()`, `env.get_local_context()`). Le moteur orchestre les tours sans jamais lire ou modifier directement les variables internes d'un agent ou d'une carte.

* **Gestionnaire de configuration :** Préparer le chargement des paramètres externes depuis des fichiers `YAML`.

* **Critère de validation :** Faire tourner une boucle à blanc pendant 100 tours avec un agent « bouchon » (qui avance tout droit) dans un environnement vide (valeurs constantes), sans erreur.

## Jalon 3 : Moteur Temporel & Environnement Isolé (Le « Monde »)

Construire l'horloge de la simulation et toute la physique des Alpilles, toujours sans l'intelligence artificielle de l'aigle.

* **Ordonnanceur (Scheduler) :** Coder la boucle principale qui fait avancer le temps, met à jour la météo et synchronise les tours.

* **Couches physiques des Alpilles :** Charger les données SIG (relief MNT, occupation du sol) et coder les calculs environnementaux (ascendances aérologiques, cartes de proies, dérangement) derrière l'interface définie au Jalon 2.

* **Critère de validation :** Générer des cartes de contrôle (ex. vérifier que le vent sur les crêtes crée bien des ascendances) et valider que l'environnement répond correctement seul, avant d'y placer le moindre oiseau.

## Jalon 4 : Implémentation du Module "Aigle de Bonelli"

Coder la logique biologique sous forme de briques comportementales réutilisables.

* **Architecture par composants (ou Stratégies) :** Découper les comportements en modules indépendants (Déplacement, Chasse/Énergie, Territorialité, Reproduction, Dispersion).

* **Paramétrage biologique :** Injection des traits d'histoire de vie (taux de mortalité, rayon de chasse, besoins énergétiques) depuis un fichier dédié `bonelli.yaml`.

* **Critère de validation :** Simulation fonctionnelle d'un couple d'aigles sur les Alpilles montrant un budget énergétique cohérent et une utilisation réaliste de l'espace.

## Jalon 5 : Observabilité, Logs & Découplage I/O

Séparer le calcul de la simulation de l'enregistrement des résultats et de l'affichage.

* **Pattern Observateur (Event Bus) :** Le moteur émet des événements (`AgentMoved`, `PreyCaptured`, `ChickFledged`) sans savoir qui les écoute.

* **Export de données :** Enregistrement asynchrone des métriques (trajectoires, dynamique des populations) vers des formats analytiques (CSV, Parquet, GeoPackage).

* **Visualisation (Optionnel/Déporté) :** Interface graphique ou script de rendu cartographique lisant les sorties du moteur.

* **Critère de validation :** Possibilité de lancer la simulation en mode "Headless" (sans interface graphique, haute performance) sur serveur tout en générant des rapports exploitables.

## Jalon 6 : Vérification, Calibration & Validation (V&V)

S'assurer que le code fait ce qu'il est censé faire et reflète la réalité écologique.

* **Tests unitaires & d'intégration :** Vérifier isolément chaque brique (ex. un agent sans énergie meurt, un agent ne traverse pas une barrière infranchissable).

* **Analyse de sensibilité :** Identifier les paramètres qui influencent le plus les résultats.

* **Validation empirique :** Comparer les domaines vitaux et le succès reproducteur simulés aux données de terrain historiques des Alpilles.

* **Critère de validation :** Les métriques émergentes de la simulation correspondent aux ordres de grandeur observés par les ornithologues sur le massif.

## Jalon 7 : Preuve de Modularité (Test d'Extensibilité)

Valider l'exigence architecturale principale avant d'industrialiser.

* **Ajout d'une 2ème espèce :** Intégrer une espèce interagissante (ex. une proie dynamique comme le Lapin de garenne/Perdrix rouge, ou un concurrent comme l'Aigle royal) via un nouveau fichier de config et de nouveaux composants.

* **Ajout d'un 2ème environnement :** Charger un autre massif (ex. Luberon ou Gorges de l'Ardèche).

* **Critère de validation :** Aucune modification du code source des **Jalons 2 et 3 (Squelette & Moteur)** n'a été nécessaire pour intégrer cette nouvelle espèce et ce nouveau territoire.