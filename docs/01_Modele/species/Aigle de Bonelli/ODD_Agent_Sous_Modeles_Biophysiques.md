---
tags:
  - ibm
  - odd
  - raptor
  - bonelli
  - biophysics
  - energetics
  - movement
type: odd-spec
status: draft
---

# Spécification ODD : Sous-Modèles Biophysiques

>**Liens internes :** [[ODD_Agent_Variables_Etat_et_Parametres]] | [[ODD_Agent_Cycle_Comportemental]] | [[ODD_Agent_Sous_Modeles_Biophysiques]] | [[Interface_Requise_Environnement]] | [[Cibles_Validation_GPS]]

Cette fiche rassemble les règles mathématiques qui calculent l'énergie dépensée en vol, les chances de capturer une proie et la digestion. Elle explique aussi comment l'aigle choisit sa prochaine direction selon le vent, sa mémoire des zones de chasse, la distance au nid et le dérangement humain.

## 1. Sous-Modèle de Bilan Énergétique et Reproduction

### 1.1. Dépense Énergétique Instantanée ($\Delta E_{out}$)

La dépense énergétique sur un pas de temps $\Delta t$ dépend du mode de locomotion $M_{flight}$, de la masse corporelle $M_{body}(S)$ (plus élevée chez la femelle, rendant le vol battu plus coûteux pour elle) et des conditions aérologiques :

$$\Delta E_{out}(\Delta t) = BMR(S) \cdot \frac{\Delta t}{86400} \cdot \left[ (1 - f_{flight}) \cdot c_{perch} + f_{flight} \cdot \left( (1 - \alpha_{flap}) \cdot c_{soar} + \alpha_{flap} \cdot c_{flap}(S) \right) \right] + E_{thermo}(T_t)$$

Où :
- $f_{flight} \in \{0, 1\}$ vaut $1$ si $\Vert\vec{v}\Vert > 3\text{ m}\cdot\text{s}^{-1}$, $0$ sinon.
- $\alpha_{flap} \in [0, 1]$ est la fraction du vol effectuée en vol battu (`FLAPPING`), déterminée par le déficit de portance thermique et orographique ($w_{uplift}$) et par la météo :
  $$\alpha_{flap} = \text{clip}\left( 1 - \frac{w_{uplift}(x, y, t)}{w_{sink\_min}} + \gamma_{rain} \cdot Rain_t + \gamma_{wind} \cdot \mathbb{I}(W_t \notin [2.5, 7.5]), \, 0, \, 1 \right)$$
- Les fortes pluies et les vents hors de la plage optimale $[2.5, 7.5]\text{ m}\cdot\text{s}^{-1}$ contraignent le vol plané et augmentent le recours au vol battu coûteux. Les mâles, plus légers, tolèrent une proportion plus élevée de vol battu que les femelles.
- **Proxy accélérométrique (ODBA) :** Pour le calibrage direct sur les données de biologging, la dépense journalière est liée linéairement à la distance parcourue $L_{day}$ et négativement au temps de résidence au nid ($\beta_{ODBA\_res} = -24.986, p < 0.001$) et au nombre de visites au nid ($\beta_{ODBA\_rev} = -0.076, p < 0.001$).

### 1.2. Capture de Proie (Modèle Logistique GLMM de Succès d'Attaque)

Lorsqu'une attaque est déclenchée ($\Sigma = \text{HUNTING\_ATTACK}$), la probabilité de succès $P_{succ}$ (moyenne empirique globale $= 0.282$) suit le meilleur modèle GLMM ($\text{AICc weight} = 0.71$) identifié par Martínez et al. (2014) :

$$\text{logit}(P_{succ}) = \beta_0 + \beta_{group} \cdot G + \beta_{hab} \cdot \mathbb{I}_{open} + \beta_{loc} \cdot \mathbb{I}_{air} + \beta_{mode} \cdot \mathbb{I}_{surprise}$$

Avec les coefficients paramétrés pour l'Aigle de Bonelli :
- $\beta_{group} = -0.170 \text{ (SE } 0.065\text{)}$ : diminution du succès avec la taille du groupe de proies $G \in [1, 50]$ (effets de vigilance et de confusion).
- $\beta_{hab} = +2.449 \text{ (SE } 1.047\text{)}$ : $\mathbb{I}_{open} = 1$ si le couvert arbustif dans un rayon de $20\text{ m}$ autour de la proie est compris entre $1\%$ et $69\%$ ($0$ si $\ge 70\%$, habitat fermé).
- $\beta_{loc} = -1.452 \text{ (SE } 0.507\text{)}$ : $\mathbb{I}_{air} = 1$ si la proie est attaquée en plein vol ($0$ si au sol).
- $\beta_{mode} = +1.132 \text{ (SE } 0.468\text{)}$ : $\mathbb{I}_{surprise} = 1$ si l'attaque est menée par surprise en utilisant le relief ou depuis un perchoir ($0$ sinon).

### 1.3. Assimilation Énergétique ($\Delta E_{in}$)

En cas de succès ($u \sim \mathcal{U}(0,1) \le P_{succ}$), la biomasse capturée $m_{prey} \in \{900, 642.5, 420, 400\}\text{ g}$ (selon l'espèce capturée : lapin, corvidé, perdrix rouge, pigeon) est ajoutée au jabot $C$. L'assimilation vers les réserves $E$ s'effectue au taux digestif $r_{dig}\text{ (g}\cdot\text{s}^{-1}\text{)}$ `[À CALIBRER]` :

$$\Delta m_{dig} = \min(C, r_{dig} \cdot \Delta t), \quad C_{t+\Delta t} = C_t - \Delta m_{dig}, \quad \Delta E_{in} = \Delta m_{dig} \cdot \epsilon_{assim} \cdot e_{prey}$$

### 1.4. Démographie et Succès Reproducteur (Couplage Mouvement $\rightarrow$ Fitness)

En fin de saison, la performance reproductrice du couple dépend du statut de recrutement ($R_{new}$), de la température maximale en élevage ($T_{max, rearing}$) et de la proportion de temps en vol du mâle en élevage ($\bar{\tau}_{flight, M, rearing}$) :

- **Probabilité de ponte ($P_{breed}$, moyenne $0.85$) :** Vaut $0.95$ sans nouveau recrutement, chute à $0.85$ si nouveau mâle ($\beta = -1.13$), $0.71$ si nouvelle femelle ($\beta = -1.98$), et $0.46$ si les deux partenaires sont nouvellement recrutés ($\beta = -3.03$).
- **Succès d'éclosion ($P_{hatch}$, moyenne $0.82$) :** Réduit par le recrutement d'un nouveau mâle ($\beta = -1.62$) ou d'une nouvelle femelle ($\beta = -0.98, p=0.05$).
- **Succès d'envol ($P_{fledge}$, moyenne $0.90$) :** Réduit par une nouvelle femelle ($\beta = -1.29, p=0.05$) et par de fortes températures maximales durant l'élevage ($\beta_{Tmax} = -0.48 [-0.94, -0.01]$), causant un stress thermique/mortalité directe des poussins non thermorégulés ou une pénurie de proies.
- **Productivité ($N_{fledge} \in \{0, 1, 2\}$, moyenne $0.99\text{ jeune/couple}$) :** Corrélée négativement à la proportion de temps passé en vol par le mâle durant la phase d'élevage ($\bar{\tau}_{flight, M, rearing}$), qui reflète un territoire pauvre en ressources ou une faible efficacité de chasse individuelle.

---

## 2. Mécanique de Déplacement, Météo et Expérience

### 2.1. Fonction de Sélection de Pas (Step-Selection Function - SSF)

À chaque pas de déplacement en vol, la probabilité $P(c' \mid c)$ que l'agent choisisse la cellule candidate $c'$ parmi les cellules accessibles à distance $d(c, c') \le v_{cruise} \cdot \Delta t$ est donnée par un noyau Softmax :

$$P(c' \mid c) = \frac{\exp(U(c'))}{\sum_{k \in \mathcal{N}(c)} \exp(U(k))}$$

Le score d'utilité locale $U(c')$ combine 5 composantes mécanistes :

$$U(c') = w_{up} \cdot \tilde{w}_{uplift}(c') + w_{hunt} \cdot \left[ (1 - \lambda_{Exp}) \cdot H_{apparent}(c') + \lambda_{Exp} \cdot \mathbf{M}(c') \right] - w_{cpf} \cdot d(c', \vec{p}_{nest}) - w_{terr} \cdot I_{neighbor}(c')$$

1. **Gradient d'ascendance ($\tilde{w}_{uplift}$) :** Favorise les cellules offrant une portance thermique ou orographique permettant le vol plané à faible coût.
2. **Attractivité de chasse et Stabilité Trophique ($H_{apparent}$ et mémoire $\mathbf{M}$) :**
   - L'attractivité immédiate dépend du produit de la détectabilité CORINE Land Cover $D_{CLC}(c') \in \{0, 0.25, 0.50, 0.75, 1.0\}$ (maximale dans les garrigues basses, prairies et cultures sèches où le couvert $< 70\%$) et de la stabilité temporelle de la biomasse $KBI(c')$ (*Trophic Stability Hypothesis* : l'Aigle de Bonelli sélectionne son domaine vital pour la régularité inter-saisonnière de la biomasse plutôt que pour des pics imprévisibles, maintenant un KBI interne régulier entre $285$ et $678\text{ g}\cdot\text{km}^{-1}$).
   - Le poids de la mémoire spatiale $\lambda_{Exp} = 1 - \exp(-k_{mem} \cdot Exp)$ croît avec l'expérience : un oiseau expérimenté cible directement les patchs à haut rendement connus, réduisant sa distance de recherche.
1. **Contrainte de Central Place Forager ($d(c', \vec{p}_{nest})$) :** Pénalise l'éloignement au nid, particulièrement forte chez la femelle en `INCUBATION` et `REARING`, et relâchée en `NON_BREEDING` (où l'utilisation des noyaux $K_{75\%}$ et $K_{50\%}$ varie significativement, bien que les limites globales $K_{95\%}$ restent stables toute l'année). $d(c', \vec{p}_{nest})$ doit être exprimé en kilomètres pour rester au même ordre de grandeur que les autres termes de l'équation. 
2. **Exclusion Territoriale ($I_{neighbor}$) :** Pénalité forte si la cellule appartient au $K_{95\%}$ d'un couple voisin, limitant le chevauchement à $\le 4.18\%$.