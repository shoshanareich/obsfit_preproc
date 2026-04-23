import numpy as np
import xarray as xr
from scipy.ndimage import gaussian_filter

def nan_gaussian_filter(image, sigma=2, eps=1e-16, mode='reflect', half_width=2):
    """
    NaN-aware Gaussian filter.
    
    Returns:
        VV : filtered values (without normalization)
        WW : filtered weights
        filtered : VV / WW (final normalized result)
    """
    # mask of valid points
    mask = np.isfinite(image).astype(float)

    # replace NaNs with 0 for convolution
    V = np.nan_to_num(image, nan=0.0)

    truncate = half_width/sigma

    # Gaussian filter
    VV = gaussian_filter(V, sigma=sigma, mode=mode, truncate=truncate)
    WW = gaussian_filter(mask, sigma=sigma, mode=mode, truncate=truncate)

    # avoid division by zero
    filtered = VV / (WW + eps)
    filtered[WW == 0] = np.nan

    return VV, WW, filtered

def data_uncertainty(data, sigma_instr=0.02, sigma=2, half_width=2, mode='reflect', eps=1e-16):
    """
    Compute total uncertainty (instrument + representation) after nan-aware Gaussian smoothing.
    
    data: xarray.DataArray or 2D numpy array
    Returns: xarray.DataArray of total sigma
    """

    # Apply nan-aware Gaussian filter
    VV, WW, filtered = nan_gaussian_filter(data.values, sigma=sigma, half_width=half_width, mode=mode, eps=eps)

    # Instrument error propagation
    # WW contains sum of weights, VV was weighted sum of values
    sigma_instr_smoothed = sigma_instr / (WW + eps)**0.5
    sigma_instr_smoothed[WW==0] = np.nan  # propagate NaN where no valid points

    # Representation error: weighted variance in neighborhood
    mask = np.isfinite(data.values)
    diff2 = np.where(mask, (data.values - filtered)**2, 0.0)
    # Smooth the squared differences using same Gaussian
    VV_diff2, WW_diff2, rep_var = nan_gaussian_filter(diff2, sigma=sigma, half_width=half_width, mode=mode, eps=eps)
    sigma_rep = np.sqrt(rep_var)

    # Total uncertainty
    sigma_total = np.sqrt(sigma_instr_smoothed**2 + sigma_rep**2)

    # Wrap back into xarray if input was xarray
    if isinstance(data, xr.DataArray):
        sigma_total = xr.DataArray(sigma_total, dims=data.dims, coords=data.coords)

    return sigma_total, sigma_instr_smoothed, sigma_rep, filtered
