import xarray as xr
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import os
import yaml

def load_config(config_path):
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config

def track_typhoon(file_path, start_lat, start_lon, search_radius_deg=5.0):
    """
    Tracks a typhoon starting from a known location.
    
    Args:
        file_path: Path to the NetCDF file.
        start_lat: Initial latitude of the typhoon center.
        start_lon: Initial longitude of the typhoon center.
        search_radius_deg: Radius in degrees to search for the new minimum pressure center around the previous position.
    """
    ds = xr.open_dataset(file_path)
    
    mslp = ds['mean_sea_level_pressure']
    times = ds['time'].values
    
    # Initialize tracking variables with the starting point
    current_lat = start_lat
    current_lon = start_lon
    
    track_data = []
    
    for t in times:
        # Define the search box around the current position
        lat_min = current_lat - search_radius_deg
        lat_max = current_lat + search_radius_deg
        lon_min = current_lon - search_radius_deg
        lon_max = current_lon + search_radius_deg
        
        # Handle longitude wrapping if necessary (0-360 or -180 to 180)
        # Assuming data is 0-360 based on previous output inspection
        # Simple clamping for now, can be improved for dateline crossing
        
        # Select data within the search box for the current time step
        # Note: slice order depends on data storage. Usually latitude is descending (90 to -90)
        # We use sorted slice to be safe or check data. 
        # xarray .sel(latitude=slice(a, b)) selects inclusive range. 
        # If lat is 90..-90, we need slice(max, min). If -90..90, slice(min, max).
        # Let's check the latitude order first or just use min/max variables carefully.
        
        # To be robust, we can just select by value range which xarray handles well if we pass slice correctly
        # Assuming latitude is descending (90 -> -90) based on standard global models
        lat_slice = slice(max(lat_min, lat_max), min(lat_min, lat_max)) 
        if ds.latitude[0] < ds.latitude[-1]: # Ascending
             lat_slice = slice(min(lat_min, lat_max), max(lat_min, lat_max))
        
        # Longitude is usually 0-360 ascending
        lon_slice = slice(lon_min, lon_max)
        
        local_mslp = mslp.sel(time=t, latitude=lat_slice, longitude=lon_slice)
        
        if local_mslp.size == 0:
            print(f"Warning: No data found in search radius at {t}. Stopping tracking.")
            break
            
        # Find the minimum in this local area
        min_idx = local_mslp.argmin(dim=['latitude', 'longitude'])
        
        # Update current position
        new_lat = local_mslp.latitude[min_idx['latitude']].item()
        new_lon = local_mslp.longitude[min_idx['longitude']].item()
        min_pressure = local_mslp.min().item()
        
        track_data.append({
            'time': t,
            'latitude': new_lat,
            'longitude': new_lon,
            'min_pressure': min_pressure
        })
        
        # Update for next iteration
        current_lat = new_lat
        current_lon = new_lon
    
    df = pd.DataFrame(track_data)
    return df

def plot_track(df, output_plot='typhoon_track.png'):
    plt.figure(figsize=(10, 6))
    plt.plot(df['longitude'], df['latitude'], 'b-o', markersize=4, label='Typhoon Track')
    
    # Mark start and end
    plt.plot(df['longitude'].iloc[0], df['latitude'].iloc[0], 'g^', markersize=10, label='Start')
    plt.plot(df['longitude'].iloc[-1], df['latitude'].iloc[-1], 'rx', markersize=10, label='End')
    
    plt.title('Typhoon Track (Local Minimum Search)')
    plt.xlabel('Longitude')
    plt.ylabel('Latitude')
    plt.grid(True)
    plt.legend()
    
    # Add annotations
    step = max(1, len(df) // 10)
    for i in range(0, len(df), step):
        time_str = pd.to_datetime(df['time'].iloc[i]).strftime('%m-%d %Hh')
        plt.annotate(time_str, (df['longitude'].iloc[i], df['latitude'].iloc[i]), 
                     textcoords="offset points", xytext=(0,10), ha='center', fontsize=8)

    plt.savefig(output_plot)
    print(f"Plot saved to {output_plot}")

def get_output_paths(input_file_path, base_output_dir='/mnt/cty/qiu/Pangu-Weather-ReadyToGo/figure_csv'):
    """
    Generates output paths for CSV and PNG based on the input file path structure.
    Example Input: .../2018-10-01-06-00to_v22018-10-06-06-00/combined_surface_timeseries.nc
    Example Output Dir: .../figure_csv/2018-10-01-06-00to_v22018-10-06-06-00/
    Example Output Files: 2018-10-01-06-00to_v22018-10-06-06-00.csv, .png
    """
    # Extract the parent directory name of the input file
    parent_dir_name = os.path.basename(os.path.dirname(input_file_path))
    
    # Construct the specific output directory
    output_dir = os.path.join(base_output_dir, parent_dir_name)
    
    # Create directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Construct file names
    csv_name = f"{parent_dir_name}.csv"
    plot_name = f"{parent_dir_name}.png"
    
    output_csv_path = os.path.join(output_dir, csv_name)
    output_plot_path = os.path.join(output_dir, plot_name)
    
    return output_csv_path, output_plot_path

if __name__ == "__main__":
    # Load configuration
    config_path = '/mnt/cty/qiu/Pangu-Weather-ReadyToGo/8_9_track.yaml'
    
    try:
        print(f"Loading configuration from {config_path}...")
        config = load_config(config_path)
        
        file_path = config['input_file']
        START_LAT = config['start_lat']
        START_LON = config['start_lon']
        SEARCH_RADIUS = config.get('search_radius_deg', 3.0)
        base_output_dir = config.get('output_base_dir', '/mnt/cty/qiu/Pangu-Weather-ReadyToGo/figure_csv')
        
        print(f"Input File: {file_path}")
        print(f"Start Position: ({START_LAT}, {START_LON})")
        print(f"Search Radius: {SEARCH_RADIUS} deg")
        
        # Get dynamic output paths
        output_csv, output_plot = get_output_paths(file_path, base_output_dir)
        print(f"Output directory prepared: {os.path.dirname(output_csv)}")
        
        print(f"Tracking typhoon starting from Lat: {START_LAT}, Lon: {START_LON}...")
        df_track = track_typhoon(file_path, START_LAT, START_LON, SEARCH_RADIUS)
        
        print("Typhoon Track (Top 10 rows):")
        print(df_track.head(10))
        
        df_track.to_csv(output_csv, index=False)
        print(f"\nFull track saved to: {output_csv}")
        
        plot_track(df_track, output_plot)
        
    except Exception as e:
        print(f"An error occurred: {e}")
