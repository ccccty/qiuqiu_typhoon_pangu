import xarray as xr

file_path = '/mnt/cty/qiu/Pangu-Weather-ReadyToGo/Latitude and longitude/2018-10-01-06-00to_v22018-10-06-06-00/10N50N_90E_160E/combined_surface_10N50N_90E_160E.nc'

try:
    ds = xr.open_dataset(file_path)
    print(f"Checking file: {file_path}")
    print("Variables in dataset:")
    print(ds.data_vars)
    
    # Check for wind components
    if 'u_component_of_wind_10m' in ds and 'v_component_of_wind_10m' in ds:
        print("\nWind components found:")
        print(ds['u_component_of_wind_10m'])
    else:
        print("\nWind components (10m) NOT found.")

except Exception as e:
    print(f"Error: {e}")
