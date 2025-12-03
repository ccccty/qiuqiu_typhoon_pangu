import os
import xarray as xr
from datetime import datetime
import glob

# --- Configuration ---
# The directory containing the individual .nc files
input_dir = "/mnt/cty/qiu/Pangu-Weather-ReadyToGo/outputs/2018-10-01-06-00to_v22018-10-06-06-00"

# Which type of files to process: 'upper' or 'surface'
file_type_to_process = 'surface' # Change to 'surface' if needed

# The name for the final combined NetCDF file
output_filename = f"combined_{file_type_to_process}_timeseries.nc"
output_filepath = os.path.join(input_dir, output_filename)

print(f"Input directory: {input_dir}")
print(f"Will process '{file_type_to_process}' files.")

# --- Script Logic ---

# 1. Find all the relevant .nc files and sort them chronologically
search_pattern = os.path.join(input_dir, f"output_{file_type_to_process}_*.nc")
file_paths = sorted(glob.glob(search_pattern))

if not file_paths:
    print(f"Error: No '{file_type_to_process}' .nc files found in the directory.")
    exit()

print(f"Found {len(file_paths)} files to combine.")

# 2. Define a preprocessing function to add the time coordinate from the filename
def add_time_coordinate(ds):
    # Extract the filename from the full path
    filename = os.path.basename(ds.encoding['source'])
    # Expected format: output_upper_YYYY-MM-DD-HH-MM.nc
    time_str = filename.replace(f"output_{file_type_to_process}_", "").replace(".nc", "")
    
    try:
        # Convert the string to a datetime object
        dt_object = datetime.strptime(time_str, "%Y-%m-%d-%H-%M")
        # Expand the dataset with a new 'time' dimension
        return ds.expand_dims(time=[dt_object])
    except ValueError:
        print(f"Warning: Could not parse time from filename: {filename}. Skipping.")
        return None

# 3. Open all datasets, apply the preprocessing function, and concatenate them
print("Opening and preprocessing datasets...")
datasets = [add_time_coordinate(xr.open_dataset(fp)) for fp in file_paths]
# Filter out any datasets that failed preprocessing
valid_datasets = [ds for ds in datasets if ds is not None]

if not valid_datasets:
    print("Error: No valid datasets could be processed.")
    exit()

print("Combining datasets along the 'time' dimension...")
combined_ds = xr.concat(valid_datasets, dim="time")

# 4. Save the combined dataset to a new NetCDF file
print(f"Saving combined file to: {output_filepath}")
combined_ds.to_netcdf(output_filepath)

print("\nDone! Your time-series file is ready.")
print(f"You can now open '{output_filepath}' in Panoply.")