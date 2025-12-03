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

def verify_track_step(file_path, time_step, center_lat, center_lon, search_radius_deg=5.0, output_plot='verification.png'):
    """
    Visualizes the pressure field around the tracked center at a specific time step.
    """
    ds = xr.open_dataset(file_path)
    mslp = ds['mean_sea_level_pressure']
    
    # Define search box
    lat_min = center_lat - search_radius_deg
    lat_max = center_lat + search_radius_deg
    lon_min = center_lon - search_radius_deg
    lon_max = center_lon + search_radius_deg
    
    # Select data
    lat_slice = slice(max(lat_min, lat_max), min(lat_min, lat_max)) 
    if ds.latitude[0] < ds.latitude[-1]: 
         lat_slice = slice(min(lat_min, lat_max), max(lat_min, lat_max))
    lon_slice = slice(lon_min, lon_max)
    
    local_mslp = mslp.sel(time=time_step, latitude=lat_slice, longitude=lon_slice)
    
    # Plot
    plt.figure(figsize=(8, 6))
    local_mslp.plot(cmap='jet_r') # Reversed jet colormap so low pressure is red/hot or distinct
    plt.plot(center_lon, center_lat, 'wx', markersize=12, markeredgewidth=2, label='Tracked Center')
    plt.title(f'Pressure Field Verification at {time_step}\nTracked Center: ({center_lat:.2f}N, {center_lon:.2f}E)')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig(output_plot)
    plt.close() # Close the plot to free memory
    print(f"Verification plot saved to {output_plot}")

def get_output_dir(input_file_path, base_output_dir='/mnt/cty/qiu/Pangu-Weather-ReadyToGo/figure_csv'):
    """
    Generates the verification output directory.
    """
    # Extract the parent directory name of the input file (e.g., 10N50N_90E_160E...)
    # In this case, the path is .../2018-10-01.../10N50N_90E_160E/combined...
    # We want to use the immediate parent folder name to match 8_track_typhoon.py logic
    
    parent_dir_name = os.path.basename(os.path.dirname(input_file_path))
    
    output_dir = os.path.join(base_output_dir, parent_dir_name, 'verification_plots')
    os.makedirs(output_dir, exist_ok=True)
    return output_dir

if __name__ == "__main__":
    # Load configuration
    config_path = '/mnt/cty/qiu/Pangu-Weather-ReadyToGo/8_9_track.yaml'
    
    # Since the file starts with a digit, we need to use importlib
    import importlib
    track_typhoon_module = importlib.import_module("8_track_typhoon")
    track_typhoon = track_typhoon_module.track_typhoon
    
    try:
        print(f"Loading configuration from {config_path}...")
        config = load_config(config_path)
        
        file_path = config['input_file']
        START_LAT = config['start_lat']
        START_LON = config['start_lon']
        SEARCH_RADIUS = config.get('search_radius_deg', 3.0)
        base_output_dir = config.get('output_base_dir', '/mnt/cty/qiu/Pangu-Weather-ReadyToGo/figure_csv')
        
        print("Re-running tracking on the specific file to ensure accuracy...")
        df_track = track_typhoon(file_path, START_LAT, START_LON, SEARCH_RADIUS)
        
        output_dir = get_output_dir(file_path, base_output_dir)
        print(f"Output directory: {output_dir}")
        
        # Select ~10 evenly spaced indices
        num_plots = 10
        if len(df_track) <= num_plots:
            indices = range(len(df_track))
        else:
            indices = np.linspace(0, len(df_track) - 1, num_plots, dtype=int)
        
        for idx in indices:
            row = df_track.iloc[idx]
            time_str = str(row['time'])
            lat = row['latitude']
            lon = row['longitude']
            
            # Create a safe filename from timestamp
            safe_time_str = time_str.replace(':', '-').replace(' ', '_')
            plot_filename = f"verify_{safe_time_str}.png"
            output_plot_path = os.path.join(output_dir, plot_filename)
            
            verify_track_step(file_path, row['time'], lat, lon, output_plot=output_plot_path)
            
        print(f"\nAll verification plots saved to: {output_dir}")
        
    except Exception as e:
        print(f"An error occurred: {e}")
