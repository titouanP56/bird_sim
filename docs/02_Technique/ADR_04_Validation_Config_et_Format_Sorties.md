---
tags:
  - ibm
  - adr
  - config
  - data
  - validation
type: adr
status: accepted
date: 2026-11-21
---

# ADR-04 — Validation des Configurations et Format des Sorties

> Cette fiche explique comment on sécurise la lecture des fichiers `bonelli.yaml` et `alpilles.yaml` pour éviter les erreurs silencieuses, et quel format de fichier on choisit pour enregistrer les résultats des simulations.

> **Liens internes :** [[jalon_2_architecture_technique]] | [[ODD_Agent_Variables_Etat_et_Parametres]] | [[ODD_Env_Grilles_et_Parametres_Alpilles]] | [[Cibles_Validation_GPS]]

---

## 1. Contexte et Contraintes

Le modèle repose sur plusieurs dizaines de paramètres biologiques et environnementaux, dont certains sont encore provisoires (`[À CALIBRER]`). Une simple faute de frappe sur une clé YAML ou une erreur de signe (ex : probabilité négative ou supérieure à $1$) peut fausser toute une simulation sans faire planter le programme.

En sortie, une simulation annuelle à $\Delta t = 5\text{ min}$ génère plus de $100\,000$ lignes par oiseau qu'il faudra ensuite analyser pour les comparer aux statistiques de [[Cibles_Validation_GPS]].

---

## 2. Options Envisagées

**Pour la configuration :**
* **Option 1 — Dictionnaire brut (`pyyaml` seul) :** Rapide, mais aucune vérification des types ni des bornes au démarrage.
* **Option 2 — `Pydantic v2` + `PyYAML` :** Valide automatiquement chaque champ, son type et ses bornes dès le lancement du programme, avec des messages d'erreur clairs.

**Pour les fichiers de sortie :**
* **Option A — `CSV` uniquement :** Universel et lisible au bloc-notes, mais lourd sur le disque et lent à relire pour des centaines de milliers de lignes.
* **Option B — `Parquet` (format principal) + `CSV` (optionnel) :** Format binaire compressé ultra-rapide avec `pandas`/`pyarrow`, tout en gardant un export `CSV` possible pour des petits tests de débogage.

---

## 3. Décision Retenue

1. **Configuration validée par `Pydantic v2` :**
   * Tous les paramètres de `bonelli.yaml` et `alpilles.yaml` sont chargés dans des modèles typés (`SpeciesConfig`, `EnvironmentConfig`, `SimulationConfig`).
   * **Convention `[À CALIBRER]` :** Aucune chaîne de texte `"[À CALIBRER]"` ne doit remplacer un nombre dans un fichier YAML. On inscrit toujours une valeur numérique provisoire cohérente suivie du commentaire `# [À CALIBRER]` en fin de ligne.
2. **Sorties au format `Parquet` (avec option `CSV`) :**
   * Les trajectoires détaillées (position, altitude, état, mode de vol, énergie, jabot) et les bilans journaliers ($\tau_{\text{flight}}$, $R_{\text{day}}$, $St_{\text{day}}$) sont exportés en `.parquet` pour alimenter directement les scripts d'analyse et la comparaison avec [[Cibles_Validation_GPS]].

---

## 4. Conséquences

* **Avantages :** Détection immédiate au lancement de toute erreur de paramétrage (*fail-fast*), fichiers de résultats $5$ à $10$ fois plus légers qu'en CSV, et lecture quasi instantanée pour tracer les graphiques de validation.
* **Point de vigilance :** Toute nouvelle variable ajoutée dans un fichier YAML devra aussi être déclarée dans le schéma Pydantic correspondant (`src/bonelli_ibm/core/config.py`).