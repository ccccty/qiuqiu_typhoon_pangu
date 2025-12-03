import xarray as xr

file_path = '/mnt/cty/qiu/Pangu-Weather-ReadyToGo/outputs/2018-10-01-06-00to_v22018-10-06-06-00/combined_surface_timeseries.nc'

try:
    ds = xr.open_dataset(file_path)
    print("Dataset Information:")
    print(ds)
    print("\nData Variables:")
    for var in ds.data_vars:
        print(f"- {var}: {ds[var].dims}, {ds[var].shape}")
    
    if 'mean_sea_level_pressure' in ds:
        print("\n'mean_sea_level_pressure' details:")
        print(ds['mean_sea_level_pressure'])
    else:
        print("\n'mean_sea_level_pressure' variable not found.")

except Exception as e:
    print(f"Error reading file: {e}")
