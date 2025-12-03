import xarray as xr
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import os
import yaml

def load_config(config_path):
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config

def get_intensity_category(wind_speed_ms):
    """
    Determines the typhoon intensity category based on wind speed (m/s).
    Standard: CMA (China Meteorological Administration) - 2-minute mean wind speed is standard, 
    but we are using model instantaneous/hourly data which is close enough for estimation.
    
    Ranges:
    - Tropical Depression (TD): 10.8 - 17.1 m/s
    - Tropical Storm (TS): 17.2 - 24.4 m/s
    - Severe Tropical Storm (STS): 24.5 - 32.6 m/s
    - Typhoon (TY): 32.7 - 41.4 m/s
    - Severe Typhoon (STY): 41.5 - 50.9 m/s
    - Super Typhoon (SuperTY): >= 51.0 m/s
    """
    if wind_speed_ms < 10.8:
        return "Low Pressure (<10.8)", "gray"
    elif 10.8 <= wind_speed_ms <= 17.1:
        return "Tropical Depression (TD)", "skyblue"
    elif 17.2 <= wind_speed_ms <= 24.4:
        return "Tropical Storm (TS)", "blue"
    elif 24.5 <= wind_speed_ms <= 32.6:
        return "Severe Tropical Storm (STS)", "green"
    elif 32.7 <= wind_speed_ms <= 41.4:
        return "Typhoon (TY)", "yellow"
    elif 41.5 <= wind_speed_ms <= 50.9:
        return "Severe Typhoon (STY)", "orange"
    else:
        return "Super Typhoon (SuperTY)", "red"

def plot_intensity_track(df, output_plot):
    """
    Plots the typhoon track with points colored by intensity.
    """
    plt.figure(figsize=(12, 8))
    
    # Plot the connecting line
    plt.plot(df['longitude'], df['latitude'], 'k-', linewidth=1, alpha=0.5, label='Track Path')
    
    # Define categories for legend
    categories = [
        ("Tropical Depression (TD)", "skyblue"),
        ("Tropical Storm (TS)", "blue"),
        ("Severe Tropical Storm (STS)", "green"),
        ("Typhoon (TY)", "yellow"),
        ("Severe Typhoon (STY)", "orange"),
        ("Super Typhoon (SuperTY)", "red")
    ]
    
    # Plot points for each category
    for cat_name, color in categories:
        subset = df[df['intensity_category'] == cat_name]
        if not subset.empty:
            plt.scatter(subset['longitude'], subset['latitude'], c=color, s=50, label=cat_name, zorder=5, edgecolors='k', linewidth=0.5)
            
    # Plot Low Pressure points if any
    subset_lp = df[df['intensity_category'] == "Low Pressure (<10.8)"]
    if not subset_lp.empty:
         plt.scatter(subset_lp['longitude'], subset_lp['latitude'], c='gray', s=30, label="Low Pressure", zorder=5)

    # Mark Start and End
    plt.plot(df['longitude'].iloc[0], df['latitude'].iloc[0], 'g^', markersize=12, label='Start', zorder=10)
    plt.plot(df['longitude'].iloc[-1], df['latitude'].iloc[-1], 'rx', markersize=12, label='End', zorder=10)
    
    plt.title('Typhoon Track & Intensity (CMA Standard)')
    plt.xlabel('Longitude')
    plt.ylabel('Latitude')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend(loc='best')
    
    # Add date annotations
    step = max(1, len(df) // 10)
    for i in range(0, len(df), step):
        time_str = pd.to_datetime(df['time'].iloc[i]).strftime('%m-%d %Hh')
        plt.annotate(time_str, (df['longitude'].iloc[i], df['latitude'].iloc[i]), 
                     textcoords="offset points", xytext=(0,10), ha='center', fontsize=8,
                     bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="none", alpha=0.7))

    plt.savefig(output_plot, dpi=300, bbox_inches='tight')
    print(f"Intensity track plot saved to {output_plot}")

def calculate_intensity(file_path, track_csv_path=None, start_lat=17.0, start_lon=134.0, search_radius_deg=3.0, correction_factor=1.4):
    """
    Calculates typhoon intensity based on maximum wind speed near the center.
    
    Args:
        correction_factor: Wind speed multiplier (default 1.4). 
                           Global models (0.25 deg) often underestimate peak wind speeds in the eye wall 
                           due to smoothing and resolution limits. 
                           A factor of 1.3-1.5 is often used to estimate realistic gusts/1-min sustained winds.
    """
    ds = xr.open_dataset(file_path)
    
    # Ensure we have wind data
    if 'u_component_of_wind_10m' not in ds or 'v_component_of_wind_10m' not in ds:
        raise ValueError("Wind components (10m) not found in dataset.")
        
    # Calculate wind speed magnitude
    # speed = sqrt(u^2 + v^2)
    wind_speed = np.sqrt(ds['u_component_of_wind_10m']**2 + ds['v_component_of_wind_10m']**2)
    
    mslp = ds['mean_sea_level_pressure']
    times = ds['time'].values
    
    # We can either re-track or use existing track. Let's re-track for consistency with this specific file logic
    # reusing the simple tracking logic from before
    
    current_lat = start_lat
    current_lon = start_lon
    tracking_radius = 5.0 # For finding the center
    
    results = []
    
    print(f"Processing {len(times)} time steps...")
    
    for t in times:
        # --- 1. Find Center (Minimum Pressure) ---
        lat_min = current_lat - tracking_radius
        lat_max = current_lat + tracking_radius
        lon_min = current_lon - tracking_radius
        lon_max = current_lon + tracking_radius
        
        # Correct slice direction for latitude
        lat_slice = slice(max(lat_min, lat_max), min(lat_min, lat_max)) 
        if ds.latitude[0] < ds.latitude[-1]: 
             lat_slice = slice(min(lat_min, lat_max), max(lat_min, lat_max))
        lon_slice = slice(lon_min, lon_max)
        
        local_mslp = mslp.sel(time=t, latitude=lat_slice, longitude=lon_slice)
        
        if local_mslp.size == 0:
            break
            
        min_idx = local_mslp.argmin(dim=['latitude', 'longitude'])
        center_lat = local_mslp.latitude[min_idx['latitude']].item()
        center_lon = local_mslp.longitude[min_idx['longitude']].item()
        min_p = local_mslp.min().item()
        
        # Update current pos for next step
        current_lat = center_lat
        current_lon = center_lon
        
        # --- 2. Calculate Max Wind Speed in "Eye Wall" Region ---
        # 搜索最大风速逻辑：
        # 以找到的台风最低气压中心 (center_lat, center_lon) 为圆心
        # 在 search_radius_deg (默认3度) 的矩形范围内搜索
        # 目标是找到该范围内 10米风速 (sqrt(u^2 + v^2)) 的最大值
        # 这个最大值代表了“近中心最大持续风速”，用于判断台风强度
        
        w_lat_min = center_lat - search_radius_deg
        w_lat_max = center_lat + search_radius_deg
        w_lon_min = center_lon - search_radius_deg
        w_lon_max = center_lon + search_radius_deg
        
        w_lat_slice = slice(max(w_lat_min, w_lat_max), min(w_lat_min, w_lat_max))
        if ds.latitude[0] < ds.latitude[-1]:
            w_lat_slice = slice(min(w_lat_min, w_lat_max), max(w_lat_min, w_lat_max))
        w_lon_slice = slice(w_lon_min, w_lon_max)
        
        local_wind = wind_speed.sel(time=t, latitude=w_lat_slice, longitude=w_lon_slice)
        
        # Debug info: Print location of max wind relative to center
        if local_wind.size > 0:
            raw_max_wind = local_wind.max().item()
            
            # --- Apply Correction Factor ---
            # 由于模型分辨率限制 (0.25度约为25km)，无法解析出台风眼墙极窄区域内的极端风速。
            # 模型输出的是网格平均风速，通常显著低于实测的近中心最大风速。
            # 因此引入修正系数 (correction_factor)，将模型风速转换为估算的真实强度。
            max_wind = raw_max_wind * correction_factor
            
            # Optional: print debug info
            # max_wind_idx = local_wind.argmax(dim=['latitude', 'longitude'])
            # ...
        else:
            max_wind = 0.0
            
        intensity_cat, intensity_color = get_intensity_category(max_wind)
        
        results.append({
            'time': t,
            'latitude': center_lat,
            'longitude': center_lon,
            'min_pressure_pa': min_p,
            'max_wind_speed_ms': max_wind,
            'intensity_category': intensity_cat,
            'intensity_color': intensity_color
        })
        
    df = pd.DataFrame(results)
    return df

if __name__ == "__main__":
    # Load configuration
    config_path = '/mnt/cty/qiu/Pangu-Weather-ReadyToGo/11_wind.yaml'
    
    try:
        print(f"Loading configuration from {config_path}...")
        config = load_config(config_path)
        
        input_file = config['input_file']
        START_LAT = config['start_lat']
        START_LON = config['start_lon']
        SEARCH_RADIUS = config.get('search_radius_deg', 3.0)
        CORRECTION_FACTOR = config.get('correction_factor', 1.4)
        base_output_dir = config.get('output_base_dir', '/mnt/cty/qiu/Pangu-Weather-ReadyToGo/figure_csv')
        
        print(f"Input File: {input_file}")
        print(f"Start Position: ({START_LAT}, {START_LON})")
        print(f"Search Radius: {SEARCH_RADIUS} deg")
        print(f"Correction Factor: {CORRECTION_FACTOR}")
        
        print("Calculating typhoon intensity...")
        df_result = calculate_intensity(input_file, start_lat=START_LAT, start_lon=START_LON, 
                                      search_radius_deg=SEARCH_RADIUS, correction_factor=CORRECTION_FACTOR)
        
        print("\nTyphoon Intensity Report (Top 10):")
        print(df_result[['time', 'latitude', 'longitude', 'min_pressure_pa', 'max_wind_speed_ms', 'intensity_category']].head(10))
        
        # Save to CSV in the structured directory
        # Structure: .../figure_csv/<experiment_name>/...
        # Parse experiment name from path
        # Use basename logic like in tracking scripts
        experiment_name = os.path.basename(os.path.dirname(input_file))
        
        output_dir = os.path.join(base_output_dir, experiment_name)
        os.makedirs(output_dir, exist_ok=True)
        
        output_csv = os.path.join(output_dir, f"{experiment_name}_intensity.csv")
        df_result.to_csv(output_csv, index=False)
        print(f"\nFull intensity report saved to: {output_csv}")
        
        output_plot = os.path.join(output_dir, f"{experiment_name}_intensity_track.png")
        plot_intensity_track(df_result, output_plot)
        
    except Exception as e:
        print(f"An error occurred: {e}")
