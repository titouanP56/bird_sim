---
tags:
  - ibm
  - odd
  - bonelli
  - alpilles
  - environment
  - gis
  - parameters
type: odd-spec
status: draft
---

# ODD Environnement — Grilles Spatiales et Paramètres des Alpilles

Cette note définit l'architecture géomatique multi-résolution du massif des Alpilles en projection Lambert-93 (`EPSG:2154`) ainsi que le fichier de configuration centralisé `alpilles.yaml`[cite: 1, 2]. Elle garantit une représentation strictement biophysique du territoire, sans aucune composante anthropique ni infrastructure humaine.

> **Liens internes :** [[ODD_Env_Dynamique_et_Planification]] | [[ODD_Env_Sous_Modeles_Physiques]] | [[Interface_Requise_Environnement]]

---

## 1. Structure Générique des Couches Spatiales

### 1.1. Système de Référence et Grille Maîtresse
* **Projection plane métrique :** RGF93 / Lambert-93 (`EPSG:2154`)[cite: 1, 2].
* **Grille maîtresse (`10 m × 10 m`) :** Alignée sur le produit d'occupation du sol OSO Theia[cite: 1, 2]. Toute requête spatiale continue $(x, y)$ de `RaptorAgent` est indexée dans ce référentiel commun via `rasterio` et `xarray`.
* **Convention de calage des pixels (`GTRasterTypeGeoKey`) :** Vérification obligatoire du tag `AREA_OR_POINT` avant tout calcul de gradient. Les rasters `RasterPixelIsArea` (coordonnée au coin supérieur gauche) sont décalés d'un demi-pixel ($\Delta x / 2$) lors de l'alignement avec les grilles `RasterPixelIsPoint` (coordonnée au centre géométrique) pour éviter tout biais de superposition.

### 1.2. Stratégie de Superposition Multi-Résolutions

| Couche / Variable | Résolution native | Type de donnée | Méthode de rééchantillonnage / alignement | Référence |
| :--- | :---: | :--- | :--- | :--- |
| **MNT (`RGE ALTI`)** : $z_{\text{terrain}}$, pente $\beta_{\text{slope}}$, exposition $\alpha_{\text{aspect}}$, rugosité | $5 \times 5\text{ m}$ | Continue | Interpolation **bilinéaire** vers grille $10\text{ m}$ (gradients calculés sur noyau $3 \times 3$ à $5\text{ m}$ avant rééchantillonnage) | [[ODD_Env_Sous_Modeles_Physiques]] |
| **Occupation du sol (`OSO Theia`)** & Masque eau (`WBM`) | $10 \times 10\text{ m}$ | Catégorielle | **Plus proche voisin** (*Nearest Neighbor*) strict pour préserver les identifiants discrets des 6 faciès[cite: 1, 2] | [[ODD_Env_Sous_Modeles_Physiques]] |
| **Couvert arbustif local** (`shrub_cover_20m`) | Rayon $20\text{ m}$ | Continue ($\%$) | Convolution circulaire (rayon $2\text{ pixels}$ sur grille $10\text{ m}$) | [[ODD_Env_Sous_Modeles_Physiques]] |
| **Biomasse trophique** (`kbi_biomass`) | $1 \times 1\text{ km}$ | Continue | **Plus proche voisin** par maille UTM ou interpolation bilinéaire lissée selon saison (`Br`, `Pfdp`, `NBr`) | [[ODD_Env_Sous_Modeles_Physiques]] |
| **Forçages météo** (`SAFRAN` / Station Salon-de-Provence) | $8 \times 8\text{ km}$ / Ponctuelle | Continue | Interpolation **bilinéaire** ou **pondération inverse à la distance (IWD)** | [[ODD_Env_Dynamique_et_Planification]] |

---

## 2. Configuration Complète du Territoire (`alpilles.yaml`)

```yaml
# ==============================================================================
# CONFIGURATION ENVIRONNEMENTALE DU MASSIF DES ALPILLES (alpilles.yaml)
# Modèle Individu-Centré (ABM) - Aquila fasciata - Règle stricte : ZÉRO HUMAIN
# ==============================================================================

spatial_reference:
  crs: "EPSG:2154"
  master_grid_resolution_m: 10.0
  dem_native_resolution_m: 5.0
  extent:
    bbox: "[À CALIBRER]"              # [xmin, ymin, xmax, ymax] en m (EPSG:2154)
    length_ew_km: "[À CALIBRER]"      # Extension Est-Ouest (km)
    width_ns_km: "[À CALIBRER]"       # Extension Nord-Sud (km)
    karst_unit_ha: "[À CALIBRER]"     # Superficie entité karstique (ha)
    natura2000_ha: "[À CALIBRER]"     # Superficie ZPS / ZSC (ha)

topography:
  elevation_m_ngf:
    piedmont_min: "[À CALIBRER]"
    combes_range: "[À CALIBRER]"
    summit_max: "[À CALIBRER]"        # Tour des Opies
  structural_compartments:
    flanc_nord:
      dominant_aspect: "N"
      slope_deg: "[À CALIBRER]"
      substrate: "[À CALIBRER]"
      albedo: "[À CALIBRER]"
    cretes_calcaires:
      dominant_aspect: "E-W"
      slope_deg: "[À CALIBRER]"
      substrate: "Calcaires durs massifs (faciès urgonien / jurassique)"
      albedo: "[À CALIBRER]"
    falaises_escarpements:
      dominant_aspect: "[À CALIBRER]"
      slope_deg: "[À CALIBRER]"
      substrate: "Calcaires compacts fracturés / karstifiés"
      albedo: "[À CALIBRER]"
    cuestas_crets:
      dominant_aspect: "E-W"
      slope_deg: "[À CALIBRER]"
      substrate: "Alternance calcaires durs / niveaux marno-calcaires"
      albedo: "[À CALIBRER]"
    combes_anticlinales:
      dominant_aspect: "E-W"
      slope_deg: "[À CALIBRER]"
      substrate: "Marnes, argiles de décalcification, colluvions"
      albedo: "[À CALIBRER]"
    piemonts_meridionaux:
      dominant_aspect: "S"
      slope_deg: "[À CALIBRER]"
      substrate: "Éboulis cryoclastiques, sols meubles caillouteux"
      albedo: "[À CALIBRER]"

# ------------------------------------------------------------------------------
# 6 FACIÈS ÉCOLOGIQUES (OSO Theia 10 m / Natura 2000)
# Convention structurelle : OPEN si couvert [1%, 69%], CLOSED si couvert >= 70%
# ------------------------------------------------------------------------------
habitats:
  1_falaises_dalles_rocheuses:
    oso_code: "[À CALIBRER]"
    albedo: "[À CALIBRER]"
    roughness_z0_m: "[À CALIBRER]"
    displacement_d0_m: 0.0
    hydric_state_mu: "[À CALIBRER]"
    bowen_ratio_beta: 5.0             # Réf. semi-aride (Allen, 2006)
    shrub_canopy_cover_pct: "[À CALIBRER]"
    openness_class: "OPEN"
    prey_detectability_d_clc: 1.0
    perch_availability_ha: "[À CALIBRER]"  # Très élevée (vires, corniches)
  2_pelouses_seches_substeppiques:
    oso_code: "[À CALIBRER]"
    albedo: "[À CALIBRER]"
    roughness_z0_m: "[À CALIBRER]"
    displacement_d0_m: 0.07           # Réf. herbe basse (Monteith & Unsworth, 1990)
    hydric_state_mu: "[À CALIBRER]"
    bowen_ratio_beta: "[À CALIBRER]"
    shrub_canopy_cover_pct: "[À CALIBRER]"
    openness_class: "OPEN"
    prey_detectability_d_clc: 1.0
    perch_availability_ha: "[À CALIBRER]"  # Faible à nulle
  3_garrigues_basses_moyennes:
    oso_code: "[À CALIBRER]"
    albedo: "[À CALIBRER]"
    roughness_z0_m: "[À CALIBRER]"
    displacement_d0_m: "[À CALIBRER]"
    hydric_state_mu: "[À CALIBRER]"
    bowen_ratio_beta: "[À CALIBRER]"
    shrub_canopy_cover_pct: "[À CALIBRER]"
    openness_class: "OPEN"
    prey_detectability_d_clc: 0.75
    perch_availability_ha: "[À CALIBRER]"  # Faible à modérée
  4_pinedes_chenaies:
    oso_code: "[À CALIBRER]"
    albedo: "[À CALIBRER]"
    roughness_z0_m: "[À CALIBRER]"
    displacement_d0_m: "[À CALIBRER]" # < 20 m feuillus, < 30 m conifères
    hydric_state_mu: "[À CALIBRER]"
    bowen_ratio_beta: "[À CALIBRER]"
    shrub_canopy_cover_pct: "[À CALIBRER]"
    openness_class: "CLOSED"
    prey_detectability_d_clc: 0.0
    perch_availability_ha: "[À CALIBRER]"  # Élevée (houppiers Pinus/Quercus)
  5_agrosystemes_extensifs:
    oso_code: "[À CALIBRER]"
    albedo: "[À CALIBRER]"
    roughness_z0_m: "[À CALIBRER]"
    displacement_d0_m: "[À CALIBRER]" # < 3 m cultures, < 4 m vergers
    hydric_state_mu: "[À CALIBRER]"
    bowen_ratio_beta: "[À CALIBRER]"
    shrub_canopy_cover_pct: "[À CALIBRER]"
    openness_class: "OPEN"
    prey_detectability_d_clc: 0.50
    perch_availability_ha: "[À CALIBRER]"  # Modérée (haies, arbres isolés)
  6_prairies_humides_marais:
    oso_code: "[À CALIBRER]"
    albedo: "[À CALIBRER]"
    roughness_z0_m: "[À CALIBRER]"
    displacement_d0_m: 0.66
    hydric_state_mu: "[À CALIBRER]"
    bowen_ratio_beta: "[À CALIBRER]"
    shrub_canopy_cover_pct: "[À CALIBRER]"
    openness_class: "OPEN"
    prey_detectability_d_clc: 0.75
    perch_availability_ha: "[À CALIBRER]"  # Faible

  vegetation_dynamics:
    progressive_closure_rate_pct_yr: "[À CALIBRER]"
    closure_threshold_pct: 70.0
    natural_fire_return_period_yr: "[À CALIBRER]"
    post_fire_canopy_cover_pct: "[À CALIBRER]"
    post_fire_albedo: "[À CALIBRER]"

# ------------------------------------------------------------------------------
# CLIMATOLOGIE & RÉGIMES DE MISTRAL (Station Salon-de-Provence & Radars UHF)
# ------------------------------------------------------------------------------
climatology:
  reference_station: "Salon-de-Provence"
  monthly_normals:
    # Format : [T_mean_C, T_min_C, T_max_C, rainfall_mm, wind_speed_ms, wind_dir_deg, gust_days_ge_16ms]
    jan: ["[À CALIBRER]", "[À CALIBRER]", "[À CALIBRER]", "[À CALIBRER]", "[À CALIBRER]", "[À CALIBRER]", "[À CALIBRER]"]
    feb: ["[À CALIBRER]", "[À CALIBRER]", "[À CALIBRER]", "[À CALIBRER]", "[À CALIBRER]", "[À CALIBRER]", "[À CALIBRER]"]
    mar: ["[À CALIBRER]", "[À CALIBRER]", "[À CALIBRER]", "[À CALIBRER]", "[À CALIBRER]", "[À CALIBRER]", "[À CALIBRER]"]
    apr: ["[À CALIBRER]", "[À CALIBRER]", "[À CALIBRER]", "[À CALIBRER]", "[À CALIBRER]", "[À CALIBRER]", "[À CALIBRER]"]
    may: ["[À CALIBRER]", "[À CALIBRER]", "[À CALIBRER]", "[À CALIBRER]", "[À CALIBRER]", "[À CALIBRER]", "[À CALIBRER]"]
    jun: ["[À CALIBRER]", "[À CALIBRER]", "[À CALIBRER]", "[À CALIBRER]", "[À CALIBRER]", "[À CALIBRER]", "[À CALIBRER]"]
    jul: ["[À CALIBRER]", "[À CALIBRER]", "[À CALIBRER]", "[À CALIBRER]", "[À CALIBRER]", "[À CALIBRER]", "[À CALIBRER]"]
    aug: ["[À CALIBRER]", "[À CALIBRER]", "[À CALIBRER]", "[À CALIBRER]", "[À CALIBRER]", "[À CALIBRER]", "[À CALIBRER]"]
    sep: ["[À CALIBRER]", "[À CALIBRER]", "[À CALIBRER]", "[À CALIBRER]", "[À CALIBRER]", "[À CALIBRER]", "[À CALIBRER]"]
    oct: ["[À CALIBRER]", "[À CALIBRER]", "[À CALIBRER]", "[À CALIBRER]", "[À CALIBRER]", "[À CALIBRER]", "[À CALIBRER]"]
    nov: ["[À CALIBRER]", "[À CALIBRER]", "[À CALIBRER]", "[À CALIBRER]", "[À CALIBRER]", "[À CALIBRER]", "[À CALIBRER]"]
    dec: ["[À CALIBRER]", "[À CALIBRER]", "[À CALIBRER]", "[À CALIBRER]", "[À CALIBRER]", "[À CALIBRER]", "[À CALIBRER]"]

  mistral_regime:
    direction_sector_deg: "[À CALIBRER]"       # Secteur N-NW
    established_speed_threshold_ms: "[À CALIBRER]"
    thermal_cutoff_speed_ms: 12.87             # 25 noeuds (Allen, 2006)
    min_duration_h: "[À CALIBRER]"
    annual_frequency_days: "[À CALIBRER]"
    seasonal_frequency_pct:
      winter: "[À CALIBRER]"
      spring: "[À CALIBRER]"
      summer: "[À CALIBRER]"
      autumn: "[À CALIBRER]"
    established_mean_speed_ms: "[À CALIBRER]"
    gust_max_speed_ms: "[À CALIBRER]"
    pbl_height_zi_mistral_m: "[À CALIBRER]"
    pbl_height_zi_convective_m: "[À CALIBRER]"

# ------------------------------------------------------------------------------
# RESSOURCES TROPHIQUES (Populations sauvages uniquement - Zéro lâcher)
# ------------------------------------------------------------------------------
prey_guilds:
  kbi_seasonal_range_g_km:
    breeding_mar: "[À CALIBRER]"
    post_fledging_jun: "[À CALIBRER]"
    non_breeding_nov: "[À CALIBRER]"
    home_range_baseline: [285.0, 678.0]

  oryctolagus_cuniculus:              # Lapin de garenne
    mean_body_mass_g: 900.0
    group_size_G: "[À CALIBRER]"
    initial_position: "SOIL"
    preferred_habitats: [2, 3, 5]
    spatial_density_ind_ha: "[À CALIBRER]"
    epizootic_mortality_pct: "[À CALIBRER]"    # Myxomatose / VHD
    circadian_activity:
      summer: "crepuscular_nocturnal_bimodal"
      winter: "crepuscular_diurnal_extended"
      hourly_weights_summer: "[À CALIBRER]"
      hourly_weights_winter: "[À CALIBRER]"

  alectoris_rufa:                     # Perdrix rouge (sauvage uniquement)
    mean_body_mass_g: 420.0
    group_size_G: "[À CALIBRER]"
    initial_position: "SOIL"
    preferred_habitats: [2, 3, 5]
    spatial_density_ind_ha: "[À CALIBRER]"
    circadian_activity:
      summer: "diurnal_bimodal"
      winter: "diurnal_unimodal"
      hourly_weights_summer: "[À CALIBRER]"
      hourly_weights_winter: "[À CALIBRER]"

  timon_lepidus:                      # Lézard ocellé
    mean_body_mass_g: "[À CALIBRER]"
    group_size_G: 1
    initial_position: "SOIL"
    preferred_habitats: [1, 3]
    spatial_density_ind_ha: "[À CALIBRER]"
    hibernation_start_julian_day: "[À CALIBRER]"
    hibernation_end_julian_day: "[À CALIBRER]"
    circadian_activity:
      summer: "diurnal_heliophilic_bimodal"
      winter: "null_hibernation"
      hourly_weights_summer: "[À CALIBRER]"
      hourly_weights_winter: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

  secondary_avifauna:                 # Corvidés (642.5 g), Pigeons (400 g), Passereaux
    mean_body_mass_g: 642.5
    group_size_G: "[À CALIBRER]"
    initial_position: "AIR"
    preferred_habitats: [2, 3, 5, 6]
    spatial_density_ind_ha: "[À CALIBRER]"
    circadian_activity:
      summer: "diurnal_bimodal"
      winter: "diurnal_unimodal"
      hourly_weights_summer: "[À CALIBRER]"
      hourly_weights_winter: "[À CALIBRER]"