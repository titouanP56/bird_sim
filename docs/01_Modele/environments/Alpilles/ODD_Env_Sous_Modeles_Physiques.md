---
tags:
  - ibm
  - odd
  - bonelli
  - environment
  - physics
  - aerology
  - equations
type: odd-spec
status: draft
---

# ODD Environnement — Sous-Modèles Physiques et Écologiques

Cette note formalise l'ensemble des équations mathématiques déterministes et stochastiques du module environnemental : ascendance orographique ($w_{\text{oro}}$), convection thermique et coupure Mistral ($w_{\text{th}}$), phénologie du couvert ($D_{\text{CLC}}$, `shrub_cover_20m`) et rencontre de proies (`sample_prey_encounter`).

> **Liens internes :** [[ODD_Env_Grilles_et_Parametres_Alpilles]] | [[ODD_Env_Dynamique_et_Planification]] | [[Interface_Requise_Environnement]]

---

## 1. Sous-Modèle d'Ascendance Orographique ($w_{\text{oro}}$)

### 1.1. Profil Vertical du Vent Horizontal (Théorie de Monin-Obukhov)
Au-dessus d'un couvert de rugosité aérodynamique $z_0$ ($\text{m}$) et de hauteur de déplacement nul $d_0$ ($\text{m}$), le profil vertical de la vitesse du vent horizontal $U(z)$ ($\text{m}\cdot\text{s}^{-1}$) à la hauteur $z = h_{\text{AGL}}$ est régi par :

$$U(z) = \frac{u_*}{\kappa} \ln\left(\frac{z - d_0}{z_0}\right) \tag{1}$$

avec $\kappa = 0.4$ la constante de von Kármán et $u_* = \sqrt{\tau_0 / \rho}$ ($\text{m}\cdot\text{s}^{-1}$) la vitesse de friction. En atmosphère stratifiée, le cisaillement vertical est modulé par la fonction universelle de stabilité $\phi_m(z/L)$ :

$$\frac{dU}{dz} = \frac{u_*}{\kappa \, z} \phi_m\left(\frac{z}{L}\right) \tag{2}$$

### 1.2. Soulèvement Cinématique sur Pente
La vitesse verticale orographique $w_{\text{oro}}$ ($\text{m}\cdot\text{s}^{-1}$) résulte de la déflexion mécanique du vecteur vent horizontal $\vec{V}_h = (u, v)$ (module $V_h = \sqrt{u^2 + v^2}$, direction météorologique d'origine $\theta_{\text{wind}}$) par la topographie locale de pente $\beta_{\text{slope}}$ ($\text{rad}$) et d'exposition $\alpha_{\text{aspect}}$ ($\text{rad}$) :

$$w_{\text{oro}}(x, y, z, t) = V_h(x, y, z, t) \cdot \sin\big(\beta_{\text{slope}}(x, y)\big) \cdot \cos\big(\theta_{\text{wind}}(x, y, t) - \alpha_{\text{aspect}}(x, y)\big) \cdot f_{\text{att}}(h_{\text{AGL}}) \tag{3}$$

où :
* Équivalent vectoriel en surface : $w_{\text{oro},0} = \vec{V}_h \cdot \nabla z_{\text{terrain}} = u \frac{\partial z_{\text{terrain}}}{\partial x} + v \frac{\partial z_{\text{terrain}}}{\partial y}$.
* Fonction d'atténuation verticale avec la hauteur au-dessus du sol $h_{\text{AGL}} = z - z_{\text{terrain}}$ : $f_{\text{att}}(h_{\text{AGL}}) =$ `[À CALIBRER]`.
* Critère de blocage / régime d'écoulement de pente via le nombre de Richardson $Ri$ : `[À CALIBRER]`.

---

## 2. Sous-Modèle de Convection Thermique ($w_{\text{th}}$) et Coupure Mistral

### 2.1. Bilan d'Énergie de Surface et Flux Cinématiques (Allen, 2006)
À partir du rayonnement net de surface $Q_S$ ($\text{W}\cdot\text{m}^{-2}$), le flux de chaleur dans le sol $Q_G$ ($\text{W}\cdot\text{m}^{-2}$) et le flux de chaleur sensible $Q_H$ ($\text{W}\cdot\text{m}^{-2}$) sont obtenus via le rapport de Bowen $\beta$ (sans unité) :

$$Q_G = 0.1 \, Q_S \tag{4}$$

$$Q_H = \frac{\beta \, (Q_S - Q_G)}{1 + \beta} \tag{5}$$

*(Note : la paramétrisation alternative de $Q_S$ à partir de l'albédo $\alpha$ et de l'état hydrique $\mu$ des faciès est balisée `[À CALIBRER]`)*.

Le flux cinématique de chaleur sensible $Q_0$ ($\text{K}\cdot\text{m}\cdot\text{s}^{-1}$) et le flux cinématique de température potentielle virtuelle $Q_{0v}$ ($\text{K}\cdot\text{m}\cdot\text{s}^{-1}$) s'écrivent :

$$Q_0 = \frac{Q_H}{\rho \, c_p} \tag{6}$$

$$Q_{0v} = Q_0 \, (1 + 0.61 \, w_s) \tag{7}$$

avec $\rho = 1.210\text{ kg}\cdot\text{m}^{-3}$, $c_p = 1004.67\text{ J}\cdot\text{kg}^{-1}\cdot\text{K}^{-1}$, et le rapport de mélange $w_s$ ($\text{g}\cdot\text{kg}^{-1}$) calculé depuis la température de surface $T_s$ ($^\circ\text{C}$), l'humidité relative $rh$ ($\%$) et la pression $p$ ($\text{mb}$) :

$$e_s = 6.112 \exp\left(\frac{17.67 \, T_s}{T_s + 243.5}\right), \quad e_v = \frac{rh \cdot e_s}{100}, \quad w_s = \frac{0.622 \, e_v}{p - e_v} \tag{8}$$

### 2.2. Échelle de Vitesse Convective $w^*$, Longueur de Monin-Obukhov $L$ et Coupure Mistral
L'échelle de vitesse convective de Deardorff $w^*$ ($\text{m}\cdot\text{s}^{-1}$) dans une couche de mélange d'épaisseur $z_i$ ($\text{m}$) est soumise à la **règle stricte de coupure par cisaillement du Mistral** à $25\text{ nœuds}$ ($12.87\text{ m}\cdot\text{s}^{-1}$) :

$$w^* = \begin{cases} \left( \dfrac{g}{\theta_0} \, Q_{0v} \, z_i \right)^{1/3} & \text{si } Q_{0v} > 0 \text{ et } V_{\text{surface}} \le 12.87\text{ m}\cdot\text{s}^{-1} \\ 0 & \text{si } Q_{0v} \le 0 \text{ ou } V_{\text{surface}} > 12.87\text{ m}\cdot\text{s}^{-1} \end{cases} \tag{9}$$

où $g = 9.81\text{ m}\cdot\text{s}^{-2}$ et $\theta_0$ ($\text{K}$) est la température potentielle de surface moyenne diurne. La compétition entre convection thermique et cisaillement mécanique est mesurée par la longueur de Monin-Obukhov $L$ ($\text{m}$) et le rapport $-z_i / L$ :

$$L = -\frac{T_0 \, u_*^3}{\kappa \, g \, Q_0} \tag{10}$$

L'écart-type de la vitesse verticale turbulente $\sigma_w$ ($\text{m}\cdot\text{s}^{-1}$) est donné par :

$$\sigma_w = \begin{cases} 1.3 \, u_* & \text{pour } z \le 0.1 \, z_i \\ 1.3 \left( u_*^3 + u_f^3 \right)^{1/3} & \text{pour } 0.1 \, z_i < z \le z_i \end{cases}, \quad \text{avec } u_f = \left(\frac{g}{T_0} Q_0 z\right)^{1/3} \tag{11}$$

### 2.3. Profil Radial et Vertical 3D des Thermiques (Allen, 2006)
Pour un thermique centré en $(x_t, y_t)$, à la distance horizontale $r = \sqrt{(x - x_t)^2 + (y - y_t)^2}$ et à l'altitude normalisée $\hat{z} = h_{\text{AGL}} / z_i \in [0, 1]$ :

* **Rayon extérieur $r_2(\hat{z})$ et rayon du cœur $r_1(\hat{z})$ :** `[À CALIBRER]` *(Équations 11–18 d'Allen [2006] absentes des extraits ; modulées par le facteur stochastique `rgain`)*.
* **Vitesse maximale au cœur $w_{\text{peak}}(\hat{z})$ :** proportionnelle à $w^* \cdot \text{wgain} \cdot \phi_w(\hat{z})$ avec $\phi_w(\hat{z}) =$ `[À CALIBRER]`.
* **Profil radial trapézoïdal $w_{\text{th}}(r, \hat{z})$ :**

$$w_{\text{th}}(r, \hat{z}) = \begin{cases} w_{\text{peak}}(\hat{z}) + w_e & \text{si } r \le r_1(\hat{z}) \\ w_{\text{trap}}(r, r_1, r_2, w_{\text{peak}}, w_D) + w_e & \text{si } r_1(\hat{z}) < r \le r_2(\hat{z}) \\ w_e & \text{si } r > r_2(\hat{z}) \end{cases} \tag{12}$$

où $w_D \le 0$ est la vitesse de subsidence de l'anneau périphérique (`[À CALIBRER]`) et $w_e \le 0$ est la subsidence environnementale de conservation de masse.

### 2.4. Vitesse Verticale Totale Exposée (`w_uplift`)
La vitesse verticale nette fournie à `RaptorAgent` est la somme linéaire des composantes orographique et convective :

$$w_{\text{uplift}}(x, y, z, t) = w_{\text{oro}}(x, y, z, t) + w_{\text{th}}(x, y, z, t) \tag{13}$$

---

## 3. Phénologie du Couvert Végétal ($D_{\text{CLC}}$ et `shrub_cover_20m`)

### 3.1. Croissance par Degrés-Jours et Télédétection (`NDVI`)
L'évolution journalière de la strate herbacée et arbustive est pilotée par l'accumulation thermique de degrés-jours (`GDD`) et/ou par les séries temporelles `NDVI(x, y, J)` interpolées linéairement :

$$\text{GDD}(J) = \sum_{k=1}^{J} \max\big(0, \, T_{\text{mean}}(k) - T_{\text{base}}\big), \quad T_{\text{base}} = [\text{À CALIBRER}] \tag{14}$$

### 3.2. Recouvrement Arbustif Local (`shrub_cover_20m`) et Classe d'Ouverture
Sur un voisinage circulaire $\mathcal{B}_{20}(x, y)$ de rayon $R = 20\text{ m}$ centré sur la cellule $(x, y)$ :

$$\text{shrub\_cover\_20m}(x, y, J) = \frac{100}{|\mathcal{B}_{20}|} \sum_{(u, v) \in \mathcal{B}_{20}(x, y)} C_{\text{shrub}}(u, v, J) \in [0, 100] \tag{15}$$

où $C_{\text{shrub}}(u, v, J) \in [0, 1]$ est la fraction de couvert arbustif/arboré modulée saisonnièrement (`[À CALIBRER]`). La classe binaire d'ouverture du milieu pour le GLMM d'attaque vaut :

$$\text{openness\_class}(x, y, J) = \begin{cases} \text{OPEN} & \text{si } 0\% \le \text{shrub\_cover\_20m}(x, y, J) \le 69\% \\ \text{CLOSED} & \text{si } \text{shrub\_cover\_20m}(x, y, J) \ge 70\% \end{cases} \tag{16}$$

### 3.3. Indice de Détectabilité des Proies ($D_{\text{CLC}}$)
L'indice `prey_detectability` $D_{\text{CLC}}(x, y, J) \in \{0, 0.25, 0.5, 0.75, 1.0\}$ associe à chaque faciès OSO Theia son accessibilité trophique (un patch est qualifié de bon spot de chasse si $D_{\text{CLC}} \ge 0.50$) :

$$D_{\text{CLC}}(x, y, J) = \begin{cases} 0 & \text{si } \text{shrub\_cover\_20m}(x, y, J) \ge 70\% \text{ (fermeture canopée)} \\ D_{\text{base}}\big(\text{faciès}(x, y)\big) \cdot \phi_{\text{pheno}}(J) & \text{sinon} \end{cases} \tag{17}$$

avec $\phi_{\text{pheno}}(J) =$ `[À CALIBRER]` (modulation saisonnière de la hauteur herbacée).

---

## 4. Modèle Stochastique de Rencontre de Proies (`sample_prey_encounter`)

Lorsqu'un agent est en état `FORAGING_SEARCH` sur la cellule $(x, y)$ au pas de temps $\Delta t = 5\text{ min}$ (jour julien $J$, heure solaire $h$), la rencontre de proie est modélisée par un processus de Poisson inhomogène.

### 4.1. Biomasse Accessible Instantanée et Taux de Rencontre $\lambda_{\text{prey}}$
Pour chaque guilde sauvage $s \in \{\text{Lapin}, \text{Perdrix}, \text{Lézard}, \text{Avifaune}\}$ (toute source cynégétique exclue) :

1. **Biomasse saisonnière de la maille $1\text{ km}$ :** $\text{KBI}(x, y, \text{saison}(J))$ ($\text{g}\cdot\text{km}^{-1}$), ventilée par guilde selon la fraction $p_s(\text{faciès}, \text{saison}) =$ `[À CALIBRER]`.
2. **Modulation circadienne et phénologique :**
   $$A_{\text{eff}}(s, J, h) = A_{\text{circ}}(s, \text{saison}(J), h) \cdot \mathbb{I}_{\text{actif}}(s, J) \in [0, 1] \tag{18}$$
   où $\mathbb{I}_{\text{actif}}(s, J) = 0$ pour *Timon lepidus* durant sa période d'hivernation (`[À CALIBRER]`) et $1$ sinon, et $A_{\text{circ}}$ encode le rythme bimodal estival ou unimodal hivernal.
3. **Taux instantané de rencontre $\lambda_s(x, y, t)$ ($\text{rencontres}\cdot\text{s}^{-1}$) :**
   $$\lambda_s(x, y, t) = c_{\text{det}} \cdot D_{\text{CLC}}(x, y, J) \cdot \left(\frac{p_s \cdot \text{KBI}(x, y, \text{saison}(J))}{m_s \cdot G_s}\right) \cdot A_{\text{eff}}(s, J, h) \tag{19}$$
   où $m_s$ ($\text{g}$) est la masse corporelle unitaire, $G_s \in [1, 50]$ la taille moyenne du groupe social, et $c_{\text{det}} =$ `[À CALIBRER]` le facteur de conversion d'échelle entre l'indice kilométrique `KBI` et le taux de détection sur $\Delta t$.

### 4.2. Tirage de l'Événement (`prey_event`)
Le taux total de rencontre sur la cellule vaut $\Lambda(x, y, t) = \sum_{s} \lambda_s(x, y, t)$. La probabilité de détecter au moins une proie durant le pas de temps $\Delta t = 300\text{ s}$ est :

$$P_{\text{encounter}}(x, y, t) = 1 - \exp\big(-\Lambda(x, y, t) \cdot \Delta t\big) \tag{20}$$

* **Tirage de détection :** $u_1 \sim \mathcal{U}(0, 1)$. Si $u_1 > P_{\text{encounter}}$, retour `{"detected": False}`.
* **Tirage de la guilde et des attributs (si $u_1 \le P_{\text{encounter}}$) :**
  * Sélection multinomiale de la guilde $s^*$ avec probabilité $\mathbb{P}(S = s) = \lambda_s / \Lambda$.
  * Tirage de la taille du groupe $G \sim \mathcal{P}_{\text{groupe}}(s^*) \in [1, 50]$ (`[À CALIBRER]`).
  * Assignation de la position initiale : `"SOIL"` (Lapin, Perdrix, Lézard) ou `"AIR"` (Avifaune secondaire).