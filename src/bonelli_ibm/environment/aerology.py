"""Pure atmospheric physics submodels: orographic uplift, thermal convection, and Mistral cutoff."""

from __future__ import annotations


def compute_wind_profile(
    z_agl_m: float,
    u_star_ms: float,
    z0_m: float,
    d0_m: float,
    kappa: float = 0.4,
) -> float:
    """Compute horizontal wind speed ``U(z)`` (m/s) via the logarithmic Monin-Obukhov profile.

    Implements ``U(z) = (u_* / kappa) * ln((z - d_0) / z_0)`` for ``z > d_0 + z_0``.

    Args:
        z_agl_m: Height above ground level ``h_AGL`` in meters.
        u_star_ms: Friction velocity ``u_*`` in m/s.
        z0_m: Aerodynamic roughness length ``z_0`` in meters.
        d0_m: Zero-plane displacement height ``d_0`` in meters.
        kappa: von Karman constant (default ``0.4``).

    Returns:
        Horizontal wind speed ``U(z)`` in m/s.
    """
    raise NotImplementedError


def compute_orographic_uplift(
    wind_speed_ms: float,
    wind_dir_rad: float,
    slope_rad: float,
    aspect_rad: float,
    z_agl_m: float,
    attenuation_scale_m: float = 200.0,
) -> float:
    """Compute mechanical orographic vertical velocity ``w_oro`` (m/s).

    Implements:
        ``w_oro = V_h * sin(beta_slope) * cos(theta_wind - alpha_aspect) * f_att(h_AGL)``

    Args:
        wind_speed_ms: Horizontal wind speed ``V_h`` at ``z_agl_m`` in m/s.
        wind_dir_rad: Meteorological wind origin direction ``theta_wind`` in radians.
        slope_rad: Terrain slope ``beta_slope`` in radians.
        aspect_rad: Terrain aspect ``alpha_aspect`` in radians.
        z_agl_m: Height above ground level ``h_AGL`` in meters.
        attenuation_scale_m: Vertical attenuation e-folding height scale in meters.

    Returns:
        Orographic vertical velocity ``w_oro`` in m/s.
    """
    raise NotImplementedError


def compute_mixing_ratio(
    temp_surface_c: float,
    relative_humidity_pct: float,
    pressure_hpa: float,
) -> float:
    """Compute water-vapor mixing ratio ``w_s`` in **kg/kg** using the 0.622 factor.

    Implements:
        ``e_s = 6.112 * exp(17.67 * T_s / (T_s + 243.5))``
        ``e_v = (rh / 100.0) * e_s``
        ``w_s = 0.622 * e_v / (p - e_v)``

    Important:
        With the molecular weight ratio ``0.622``, ``w_s`` is dimensionless
        (**kg/kg**, not g/kg), which is directly compatible with the virtual
        heat-flux formula ``Q_0v = Q_0 * (1 + 0.61 * w_s)``.

    Args:
        temp_surface_c: Surface air temperature ``T_s`` in degrees Celsius.
        relative_humidity_pct: Relative humidity ``rh`` in percent ``[0, 100]``.
        pressure_hpa: Surface atmospheric pressure ``p`` in hPa (mb).

    Returns:
        Water-vapor mixing ratio ``w_s`` in **kg/kg**.
    """
    raise NotImplementedError


def compute_surface_heat_fluxes(
    net_radiation_wm2: float,
    bowen_ratio: float,
    mixing_ratio_kg_kg: float,
    air_density_kg_m3: float = 1.210,
    specific_heat_j_kg_k: float = 1004.67,
) -> tuple[float, float, float, float]:
    """Compute surface energy balance and kinematic heat fluxes (Allen, 2006).

    Implements:
        ``Q_G = 0.1 * Q_S``
        ``Q_H = beta * (Q_S - Q_G) / (1 + beta)``
        ``Q_0 = Q_H / (rho * c_p)``
        ``Q_0v = Q_0 * (1 + 0.61 * w_s)``

    Args:
        net_radiation_wm2: Net surface radiation ``Q_S`` in W/m^2.
        bowen_ratio: Dimensionless Bowen ratio ``beta > 0``.
        mixing_ratio_kg_kg: Water-vapor mixing ratio ``w_s`` in **kg/kg**.
        air_density_kg_m3: Reference air density ``rho`` (default ``1.210`` kg/m^3).
        specific_heat_j_kg_k: Specific heat of dry air ``c_p`` (default ``1004.67`` J/(kg*K)).

    Returns:
        Tuple ``(Q_G, Q_H, Q_0, Q_0v)`` in ``(W/m^2, W/m^2, K*m/s, K*m/s)``.
    """
    raise NotImplementedError


def compute_convective_velocity_scale(
    q0v_k_ms: float,
    theta0_k: float,
    pbl_height_zi_m: float,
    surface_wind_speed_ms: float,
    mistral_cutoff_ms: float = 12.87,
    gravity_ms2: float = 9.81,
) -> float:
    """Compute Deardorff convective velocity scale ``w*`` (m/s) with Mistral cutoff.

    Applies the strict wind-shear thermal cutoff at ``12.87 m/s`` (25 knots,
    Allen 2006): returns ``0.0`` whenever ``Q_0v <= 0`` or
    ``surface_wind_speed_ms > mistral_cutoff_ms``.

    Args:
        q0v_k_ms: Virtual kinematic heat flux ``Q_0v`` in K*m/s.
        theta0_k: Mean diurnal surface potential temperature ``theta_0`` in K.
        pbl_height_zi_m: Convective boundary-layer depth ``z_i`` in meters.
        surface_wind_speed_ms: Surface horizontal wind speed in m/s.
        mistral_cutoff_ms: Mistral shear cutoff threshold (default ``12.87`` m/s).
        gravity_ms2: Gravitational acceleration ``g`` (default ``9.81`` m/s^2).

    Returns:
        Convective velocity scale ``w*`` in m/s (``>= 0.0``).
    """
    raise NotImplementedError


def compute_monin_obukhov_length(
    temp_k: float,
    u_star_ms: float,
    q0_k_ms: float,
    kappa: float = 0.4,
    gravity_ms2: float = 9.81,
) -> float:
    """Compute the Monin-Obukhov stability length ``L`` (m).

    Implements ``L = -(T_0 * u_*^3) / (kappa * g * Q_0)``.

    Args:
        temp_k: Reference air temperature ``T_0`` in K.
        u_star_ms: Friction velocity ``u_*`` in m/s.
        q0_k_ms: Kinematic sensible heat flux ``Q_0`` in K*m/s.
        kappa: von Karman constant (default ``0.4``).
        gravity_ms2: Gravitational acceleration ``g`` (default ``9.81`` m/s^2).

    Returns:
        Monin-Obukhov length ``L`` in meters.
    """
    raise NotImplementedError


def compute_turbulent_vertical_velocity_std(
    z_agl_m: float,
    pbl_height_zi_m: float,
    u_star_ms: float,
    q0_k_ms: float,
    temp_k: float,
    gravity_ms2: float = 9.81,
) -> float:
    """Compute vertical turbulent velocity standard deviation ``sigma_w`` (m/s).

    Args:
        z_agl_m: Height above ground level ``z`` in meters.
        pbl_height_zi_m: Boundary-layer depth ``z_i`` in meters.
        u_star_ms: Friction velocity ``u_*`` in m/s.
        q0_k_ms: Kinematic sensible heat flux ``Q_0`` in K*m/s.
        temp_k: Reference air temperature ``T_0`` in K.
        gravity_ms2: Gravitational acceleration ``g`` (default ``9.81`` m/s^2).

    Returns:
        Standard deviation ``sigma_w`` in m/s.
    """
    raise NotImplementedError


def compute_3d_thermal_uplift(
    radial_dist_m: float,
    z_agl_m: float,
    pbl_height_zi_m: float,
    w_star_ms: float,
    w_env_subsidence_ms: float,
    r1_m: float,
    r2_m: float,
    w_ring_downdraft_ms: float = 0.0,
    w_gain: float = 1.0,
) -> float:
    """Compute v2 trapezoidal 3D thermal vertical velocity ``w_th(r, z_hat)`` (m/s).

    Active when ``features.use_3d_thermals == True`` (Allen, 2006).

    Args:
        radial_dist_m: Horizontal distance ``r`` to the thermal center in meters.
        z_agl_m: Height above ground level in meters.
        pbl_height_zi_m: Boundary-layer depth ``z_i`` in meters.
        w_star_ms: Deardorff convective velocity scale ``w*`` in m/s.
        w_env_subsidence_ms: Mass-conserving environmental subsidence ``w_e <= 0`` (m/s).
        r1_m: Thermal core radius ``r_1(z_hat)`` in meters.
        r2_m: Thermal outer radius ``r_2(z_hat)`` in meters.
        w_ring_downdraft_ms: Outer ring subsidence ``w_D <= 0`` in m/s.
        w_gain: Stochastic thermal strength gain factor.

    Returns:
        Thermal vertical air velocity ``w_th`` in m/s.
    """
    raise NotImplementedError


def compute_total_uplift(w_oro_ms: float, w_th_ms: float) -> float:
    """Combine orographic and thermal vertical velocities into ``w_uplift`` (m/s).

    Args:
        w_oro_ms: Orographic vertical velocity ``w_oro`` in m/s.
        w_th_ms: Convective thermal vertical velocity ``w_th`` in m/s.

    Returns:
        Net vertical air velocity ``w_uplift = w_oro + w_th`` in m/s.
    """
    raise NotImplementedError
