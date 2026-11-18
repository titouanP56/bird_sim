---
tags:
  - ibm
  - odd
  - raptor
  - bonelli
  - state-variables
  - parameters
type: odd-spec
status: draft
---

# Spécification ODD : Variables d'État et Paramètres (`RaptorAgent`)

> **Liens internes :** [[ODD_Agent_Cycle_Comportemental]] | [[ODD_Agent_Sous_Modeles_Biophysiques]] | [[Interface_Requise_Environnement]]

Cette fiche recense les données qui décrivent un aigle à chaque instant (position, énergie, activité) ainsi que ses constantes biologiques (morphologie, vol, chasse, territoire). Les valeurs chiffrées sont tirées d'études scientifiques sur l'Aigle de Bonelli, complétées par des ordres de grandeur provisoires (`[À CALIBRER]`) à affiner par la suite.

## 1. Mécanique Générique : Variables d'État de l'Agent (Code Python)

Ces attributs définissent l'état interne instantané d'une instance de `RaptorAgent` au pas de temps $t$.

| Variable (Attribut Python) |      Symbole      | Type                     |            Unité             | Domaine / Description                                                                                                                     |
| :------------------------- | :---------------: | :----------------------- | :--------------------------: | :---------------------------------------------------------------------------------------------------------------------------------------- |
| `agent_id`                 |       $id$        | `int`                    |              -               | Identifiant unique de l'individu.                                                                                                         |
| `territory_id`             |    $id_{terr}$    | `int`                    |              -               | Identifiant du territoire occupé.                                                                                                         |
| `sex`                      |        $S$        | `Enum`                   |              -               | `{MALE, FEMALE}`. Détermine le dimorphisme sexuel inversé et la spécialisation des rôles parentaux.                                       |
| `age`                      |        $A$        | `int`                    |       $\text{années}$        | Âge absolu de l'individu. Maturité sexuelle entre $2$ et $5\text{ ans}$.                                                                  |
| `experience`               |       $Exp$       | `int`                    |       $\text{années}$        | Nombre d'années de présence sur le site de reproduction depuis le recrutement ($Exp \in [0, 15]$).                                        |
| `is_new_recruit`           |     $R_{new}$     | `bool`                   |              -               | `True` si $Exp == 0$ (nouveau recruté sur le territoire cette année), `False` sinon.                                                      |
| `breeding_status`          |    $B_{stat}$     | `bool`                   |              -               | `True` si le couple se reproduit l'année en cours, `False` sinon.                                                                         |
| `breeding_phase`           |      $\Phi$       | `Enum`                   |              -               | `{NON_BREEDING, PRE_BREEDING, INCUBATION, REARING, POST_FLEDGING}`.                                                                       |
| `pos`                      |    $(x, y, z)$    | `tuple[float]`           |          $\text{m}$          | Coordonnées spatiales 3D en projection métrique (ex: Lambert-93, $z$ en $\text{m asl}$).                                                  |
| `velocity`                 |     $\vec{v}$     | `tuple[float]`           | $\text{m}\cdot\text{s}^{-1}$ | Vecteur vitesse 3D courant. Si $\Vert{}\vec{v}\Vert{} > v_{flight\_thresh}$, l'agent est considéré en vol.                                |
| `behavioral_state`         |     $\Sigma$      | `Enum`                   |              -               | État courant dans la FSM : `{ROOSTING, NEST_ATTENDANCE, TRANSIT_SOARING, FORAGING_SEARCH, HUNTING_ATTACK, FEEDING, TERRITORIAL_DEFENSE}`. |
| `flight_mode`              |   $M_{flight}$    | `Enum`                   |              -               | `{NONE, PERCHED, SOARING_GLIDING, FLAPPING}`.                                                                                             |
| `energy_reserve`           |        $E$        | `float`                  |         $\text{kJ}$          | Réserves énergétiques corporelles assimilées `[À CALIBRER]`.                                                                              |
| `crop_mass`                |        $C$        | `float`                  |          $\text{g}$          | Masse de nourriture stockée dans le jabot en attente de digestion ou de régurgitation/livraison au nid `[À CALIBRER]`.                    |
| `nest_pos`                 | $(x_n, y_n, z_n)$ | `tuple[float]`           |          $\text{m}$          | Coordonnées du nid actif (choisi parmi $2\text{--}3$ nids alternatifs du territoire).                                                     |
| `daily_time_in_flight`     |  $\tau_{flight}$  | `float`                  |           $[0, 1]$           | Proportion cumulée du temps diurne passée en vol ($\Vert{}\vec{v}\Vert{} > 3\text{ m}\cdot\text{s}^{-1}$) sur la journée courante.        |
| `daily_distance`           |     $L_{day}$     | `float`                  |          $\text{m}$          | Somme des longueurs de pas parcourues depuis le réveil.                                                                                   |
| `daily_range`              |     $R_{day}$     | `float`                  |          $\text{m}$          | Distance médiane entre les positions du jour et la première position au réveil (dortoir).                                                 |
| `daily_straightness`       |    $St_{day}$     | `float`                  |           $[0, 1]$           | Indice de rectitude $D / L_{day}$, où $D$ est la distance euclidienne entre le premier et le dernier point du jour.                       |
| `daily_odba`               |   $ODBA_{day}$    | `float`                  |             $g$              | Somme journalière de l'*Overall Dynamic Body Acceleration* sur les 3 axes (proxy de dépense énergétique).                                 |
| `spatial_memory`           |   $\mathbf{M}$    | `dict[(int,int), float]` |              -               | Carte cognitive associant aux cellules $(i, j)$ du domaine vital une attractivité mémorisée fonction de $Exp$.                            |

---

## 2. Paramètres Spécifiques à l'Espèce : Configuration `bonelli.yaml`

Paramètres quantitatifs extraits des sources pour *Aquila fasciata* (et valeurs `[À CALIBRER]` lorsque absentes du corpus fourni).

```yaml
species_name: "Aquila fasciata"

# 1. MORPHOLOGIE & DIMORPHISME (Sources: Viollat et al. 2024, Morollón et al. 2022, Martínez-Miranzo et al. 2019)
morphology:
  body_mass_range_g: [1600.0, 2400.0] # (tags de 45-50g = 1.66% à 2.86% de la masse, moy 2.25%)
  body_mass_male_mean_g: 1850.0       # [À CALIBRER] (Mâle plus léger, dimorphisme inversé)
  body_mass_female_mean_g: 2250.0     # [À CALIBRER] (Femelle plus lourde, coûts de vol battu supérieurs)
  wing_span_m: 1.65                   # [À CALIBRER]
  wing_area_m2: 0.40                  # [À CALIBRER]

# 2. CINÉMATIQUE & SEUILS DE VOL (Sources: Viollat et al. 2024)
kinematics:
  flight_speed_threshold_ms: 3.0      # Seuil GPS discriminant le vol du repos/perché
  cruise_speed_soaring_ms: 12.0       # [À CALIBRER] Vitesse moyenne en vol plané/thermique
  cruise_speed_flapping_ms: 10.0      # [À CALIBRER] Vitesse moyenne en vol battu
  stoop_attack_speed_ms: 25.0         # [À CALIBRER] Vitesse de piqué lors d'une attaque
  min_sink_rate_ms: 0.85              # [À CALIBRER] Taux de chute minimal en air calme
  optimal_wind_speed_ms: 5.0          # Vent optimal maximisant la proportion de vol et la portée
  wind_speed_optimal_band_ms: [2.5, 7.5] # Plage favorable au vol (hors de cette plage, vol réduit)

# 3. MÉTABOLISME & ÉNERGÉTIQUE (Sources: López-López et al. 2022, Martínez-Miranzo et al. 2019)
energetics:
  bmr_male_kj_day: 650.0              # [À CALIBRER] Métabolisme basal mâle
  bmr_female_kj_day: 780.0            # [À CALIBRER] Métabolisme basal femelle
  cost_perched_mult_bmr: 1.5          # [À CALIBRER] Multiplicateur BMR au repos/perché
  cost_soaring_mult_bmr: 2.2          # [À CALIBRER] Vol plané/orographique peu coûteux
  cost_flapping_mult_bmr: 11.0        # [À CALIBRER] Vol battu très coûteux (surtout femelles)
  odba_to_kj_coeff: 35.0              # [À CALIBRER] Facteur de conversion ODBA (g/jour) -> kJ/jour
  max_crop_capacity_g: 450.0          # [À CALIBRER] Capacité maximale du jabot
  assimilation_efficiency: 0.78       # [À CALIBRER] Rendement d'assimilation digestive
  energy_density_prey_kj_g: 7.5       # [À CALIBRER] Densité énergétique moyenne de la biomasse fraîche
  prey_standard_masses_g:             # Biomasse relative par type de proie
    rabbit_Oryctolagus_cuniculus: 900.0         #
    corvid_Corvidae_avg: 642.5                  #
    partridge_Alectoris_rufa: 420.0             #
    pigeon_Columba_spp: 400.0                   

# 4. CHASSE & PERCEPTION (Sources: Martínez et al. 2014, López-López et al. 2022)
foraging:
  prey_detection_radius_m: 350.0      # [À CALIBRER] Rayon de détection visuelle
  vegetation_assessment_radius_m: 20.0 # Rayon autour de la proie pour évaluer l'ouverture de l'habitat
  open_habitat_cover_max_pct: 69.0    # Habitat ouvert si couvert arbustif/arboré <= 69% (fermé si >= 70%)
  favorable_hunting_spot_thresh: 0.50 # Seuil d'indice de détectabilité CLC définissant un bon spot de chasse
  baseline_attack_success_prob: 0.282 # Taux de succès global observé sur 110 attaques (28.2%)
  glmm_attack_intercept: -0.93        # [À CALIBRER] Intercept logit calibré sur moyennes
  glmm_attack_beta_group_size: -0.170 # Effet de la taille du groupe de proies (SE = 0.065)
  glmm_attack_beta_open_hab: 2.449    # Effet habitat ouvert vs fermé (SE = 1.047)
  glmm_attack_beta_prey_air: -1.452   # Effet proie en vol vs au sol (SE = 0.507)
  glmm_attack_beta_surprise: 1.132    # Effet attaque par surprise vs non-surprise (SE = 0.468)

# 5. SPATIALITÉ, NIDIFICATION & DÉRANGEMENT (Sources: Viollat et al. 2024, Morollón et al. 2022, López-López et al. 2022)
spatial_and_disturbance:
  home_range_k95_mean_km2: 54.84      # Kernel 95% moyen (± 20.78 km² en Espagne; ~70 km² en France)
  home_range_k75_mean_km2: 24.30      # Kernel 75% moyen (± 10.18 km², zone d'alimentation/repos)
  home_range_k50_mean_km2: 11.17      # Kernel 50% moyen (± 4.90 km², zone nucléaire incluant le nid)
  max_neighbor_overlap_pct: 4.18      # Chevauchement territorial inter-voisin toléré (± 3.06%)
  nests_per_territory: [2, 3]         # Nombre typique de nids alternatifs par territoire
  nest_buffer_radius_m: 25.0          # Rayon de détection d'une visite/présence au nid
  nest_excursion_min_time_s: 600.0    # Seuil temporel (10 min) hors de 25m pour clore une visite au nid
  flight_initiation_distance_m: 250.0 # [À CALIBRER] Distance de fuite en chasse/perché face à un humain