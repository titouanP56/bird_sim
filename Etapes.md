# Feuille de Route — Simulation Écologique & Comportementale (Aigle de Bonelli)

Ce document structure le développement incrémental du moteur de simulation orienté agents (IBM). Chaque étape s'appuie sur l'architecture modulaire existante (`configs/`, `environment/`, `agents/`, `engine/`, `visualization/`)[cite: 1, 2].

---

## Étape 1 : Intégrer le pas de temps et le déplacement de base
*Objectif : Mettre en place l'horloge globale de la simulation et faire évoluer un premier individu sur la grille spatiale[cite: 3].*

- [ ] **1.1. Moteur temporel (`src/engine/simulation.py`)**[cite: 3]
  - Implémenter la boucle principale avec `1 Tick = 1 Jour` et un calendrier annuel (jours `1` à `365`, gestion des saisons).
  - Définir un budget d'actions journalier par agent (`daily_steps`, ex: 5 à 8 déplacements par jour).
- [ ] **1.2. Configuration de l'espèce (`configs/species/bonelli.yaml`)**
  - Paramétrer le rayon de perception visuelle (`vision_radius`), les préférences alimentaires par espèce de proie et la pénalité de visibilité liée à la végétation[cite: 1, 2].
- [ ] **1.3. Entité Agent & Perception (`src/agents/bird.py` & `behaviors/movement.py`)**
  - Créer la classe `Eagle` (position `(y, x)`, âge, mémoire à court terme des dernières cases visitées).
  - Coder le scan spatial circulaire autour de l'aigle et le calcul de la carte d'attractivité des proies : $A(y,x) = (1 - V(y,x))^\beta \times \sum \text{pref}_p \cdot D_p(y,x)$[cite: 1, 2].
- [ ] **1.4. Suivi et Visualisation (`collector.py` & `dashboard.py`)**
  - Enregistrer la trajectoire complète et la grille de fréquentation (`occupancy_grid`)[cite: 2].
  - Afficher le parcours sur 30 jours et générer une animation temporelle jour par jour[cite: 2].

---

## Étape 2 : Intégrer un aigle qui chasse et gère son énergie
*Objectif : Introduire le métabolisme, la prise de décision de chasse et l'interaction dynamique avec la biomasse[cite: 3].*

- [ ] **2.1. Budget énergétique et Métabolisme (`src/agents/bird.py`)**
  - Ajouter la jauge `energy` (bornée entre `0` et `max_energy`) et les seuils critiques (`hunger_threshold`, `starvation_threshold`).
  - Appliquer la perte énergétique journalière : métabolisme basal (`basal_daily_cost`) + coût de chaque déplacement.
  - Gérer la condition de mortalité par inanition si `energy <= 0`.
- [ ] **2.2. Mécanique de chasse (`src/agents/behaviors/foraging.py`)**[cite: 3]
  - Évaluer la rentabilité d'une attaque sur la case courante (espérance de gain vs coût d'attaque `hunt_attempt_cost`).
  - Calculer la probabilité de capture selon la densité de la proie, la fermeture de la végétation (`VegetationLayer`) et l'efficacité intrinsèque du chasseur[cite: 1, 2].
- [ ] **2.3. Dynamique des proies (`src/environment/layers.py`)**
  - Décrémenter la biomasse dans `PreyLayer` lorsqu'une chasse réussit[cite: 2].
  - Implémenter une fonction de régénération périodique (croissance logistique des populations de lapins, perdrix, pigeons et lézards au printemps)[cite: 1, 2].

---

## Étape 3 : Intégrer l'installation territoriale et le couple
*Objectif : Permettre l'établissement d'un domaine vital fixe autour d'un site de nidification et la formation d'une paire[cite: 3].*

- [ ] **3.1. Sélection de l'aire de nidification (`src/agents/behaviors/social.py`)**
  - Permettre à un aigle adulte rassasié de chercher une case `Falaise` (`topography == 3`) entourée d'un potentiel trophique suffisant[cite: 1, 2].
  - Fixer les coordonnées du nid (`nest_position`) et passer l'état de l'agent de `Errant` à `Territorial`.
- [ ] **3.2. Force de rappel au nid (Central-Place Foraging)**
  - Modifier la fonction d'utilité de déplacement pour inclure une pénalité d'éloignement au nid (`nest_tether`), forçant l'aigle à chasser en étoile autour de son aire.
- [ ] **3.3. Rencontre et Appariement**[cite: 3]
  - Introduire le sexe des agents (`M` / `F`)[cite: 3].
  - Lorsqu'un individu adulte solitaire de sexe opposé traverse le territoire d'un résident célibataire, former un couple stable (`partner_id`) partageant le même `nest_position`[cite: 3].

---

## Étape 4 : Intégrer l'accouplement et le cycle de reproduction annuel
*Objectif : Synchroniser le comportement du couple sur le calendrier biologique pour produire de nouveaux individus[cite: 3].*

- [ ] **4.1. Calendrier phénologique (`src/agents/behaviors/reproduction.py`)**[cite: 3]
  - Déclencher les phases reproductives selon le jour de l'année (`day_of_year`)[cite: 3] :
    - *Janvier - Février :* Parades nuptiales et recharge des nids (forte présence sur la falaise)[cite: 1, 3].
    - *Février - Mars :* Ponte (1 à 2 œufs si l'énergie des parents dépasse `min_energy_to_breed`) et couvaison[cite: 3].
    - *Avril - Juin :* Élevage des poussins au nid.
    - *Juillet - Août :* Envol et émancipation.
- [ ] **4.2. Partage des tâches parentales et Nourrissage**
  - Pendant l'incubation et le début de l'élevage, contraindre l'un des parents à rester au nid pendant que le partenaire assure le ravitaillement[cite: 3].
  - Ajouter une demande énergétique journalière supplémentaire pour la nichée (`chick_daily_energy_demand`). Si le couple ne ramène pas assez de proies sur une période prolongée, la nichée échoue.
- [ ] **4.3. Recrutement et Dispersion juvénile**
  - À la fin de l'été, instancier les jeunes survivants comme nouveaux agents autonomes à l'état `Juvenile / Errant`, contraints de quitter le territoire parental.

---

## Étape 5 : Intégrer de nouveaux individus et la bataille territoriale
*Objectif : Simuler la compétition intra-spécifique, la défense du domaine vital et la régulation de la population par l'espace[cite: 3].*

- [ ] **5.1. Carte des territoires et Détection d'intrusion (`src/agents/behaviors/social.py`)**
  - Définir un rayon de défense (`territory_radius`) autour de chaque nid actif[cite: 3].
  - Permettre aux individus errants de percevoir (et généralement d'éviter via `intruder_avoidance`) les territoires déjà occupés.
- [ ] **5.2. Résolution des conflits ("Bataille territoriale")**[cite: 3]
  - Si un intrus pénètre dans le rayon défendu et est détecté par le propriétaire, déclencher une interaction agonistique[cite: 3].
  - Calculer l'issue du combat via une fonction probabiliste asymétrique (bonus d'agressivité pour le résident, prise en compte du niveau d'énergie et de l'âge)[cite: 3].
- [ ] **5.3. Conséquences démographiques**
  - *Victoire du résident :* Fuite forcée de l'intrus hors du territoire + perte énergétique pour les deux protagonistes[cite: 3].
  - *Victoire de l'intrus (rare, si le résident est affaibli/âgé) :* Éviction du propriétaire et prise de possession du territoire et du nid[cite: 3].

---

## Étape 6 : Détailler la météo dynamique et ses impacts écologiques
*Objectif : Faire varier les conditions atmosphériques jour par jour pour influencer la physique du vol et l'activité des proies[cite: 3].*

- [ ] **6.1. Générateur météorologique journalier (`src/environment/weather.py`)**[cite: 3]
  - Simuler à chaque tick les variables globales et saisonnières : **Température** ($T$), **Vitesse et direction du vent** ($\vec{W}$), et **Précipitations** (Pluie)[cite: 3].
- [ ] **6.2. Génération des courants ascendants (`UpdraftLayer`)**[cite: 3]
  - **Ascendances thermiques :** Proportionnelles à la température/ensoleillement et modulées par la nature du sol (les falaises rocheuses et plateaux calcaires chauffent plus vite que les forêts denses)[cite: 1, 2, 3].
  - **Ascendances orographiques (dynamiques) :** Calculées par le produit scalaire entre le vecteur vent $\vec{W}$ et le gradient topographique $\nabla z$ (`np.gradient(elevation)`) : les versants exposés face au vent génèrent une forte portance[cite: 2, 3].
- [ ] **6.3. Réaction comportementale des proies et contrainte de pluie**[cite: 3]
  - **Activité des proies :** Rendre la disponibilité des proies dynamique selon la météo (ex: les lézards ocellés sont invisibles par temps froid ou pluvieux ; les lapins et perdrix réduisent leurs sorties sous forte pluie ou vent violent)[cite: 1, 3].
  - **Pénalité de pluie :** Augmenter drastiquement le coût énergétique du vol et réduire le rayon de vision (`vision_radius`) lors des jours de pluie, incitant l'aigle à rester perché (journée de jeûne forcé)[cite: 3].

---

## Étape 7 : Détailler la biomécanique et les dynamiques de vol (Altitude & Plané)
*Objectif : Ajouter la dimension verticale (énergie potentielle d'altitude) pour modéliser le compromis entre vol battu et vol plané[cite: 3].*

- [ ] **7.1. Gestion de l'altitude de l'agent ($z_{\text{agent}}$)**
  - Ajouter un attribut d'altitude (ou de réserve d'énergie potentielle) à l'aigle à chaque sous-étape de déplacement.
- [ ] **7.2. Prise d'ascendance et Gain d'altitude**[cite: 3]
  - Lorsque l'aigle survole une falaise, une crête ventée ou une cellule à fort courant thermique (`UpdraftLayer` élevé), il gagne de l'altitude quasi gratuitement (vol à voile / spirale thermique)[cite: 3].
- [ ] **7.3. Transition Crête $\to$ Plaine par vol plané (Finesse aérodynamique)**[cite: 3]
  - Tant que l'aigle dispose d'un excédent d'altitude par rapport au relief sous-jacent ($z_{\text{agent}} > z_{\text{sol}}$), il peut traverser et prospecter les plaines ou plateaux avoisinants en **vol plané**[cite: 1, 2, 3].
  - À chaque case parcourue en plané, son altitude diminue selon son taux de chute (finesse de l'aigle), mais sa dépense calorique (`step_flight_cost`) est quasi nulle[cite: 3].
  - S'il est au ras du sol en plaine sans thermique ($z_{\text{agent}} \approx z_{\text{sol}}$), il est contraint d'utiliser le **vol battu**, beaucoup plus coûteux en énergie[cite: 3].