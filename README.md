# Pangu-Weather 天气预报流程

本文档详细介绍了使用盘古气象模型（Pangu-Weather）进行天气预报的完整操作流程，从准备初始数据到最终生成可供分析的时间序列文件。

## 项目概述

本流程利用 ECMWF 的 ERA5 再分析数据作为初始场，通过盘古气象模型进行迭代推理，最终生成一个包含多个时间步长的 NetCDF 格式的预报文件。

## 环境准备

在运行任何脚本之前，请确保已安装所有必需的 Python 库。

### 下载的参数
1. 地面参数 (Surface variables):

这些是地表或接近地表的参数。

- mean_sea_level_pressure : 平均海平面气压 (msl)
- 10m_u_component_of_wind : 10 米高空 U-分量风 (u10) - 东西方向的风速
- 10m_v_component_of_wind : 10 米高空 V-分量风 (v10) - 南北方向的风速
- 2m_temperature : 2 米高空温度 (t2m)
2. 高空参数 (Upper-air variables):

这些是不同气压层（从 1000hPa 到 50hPa 共 13 层）的参数。

- geopotential : 位势高度 (z)
- specific_humidity : 比湿度 (q)
- temperature : 温度 (t)
- u_component_of_wind : U-分量风 (u)
- v_component_of_wind : V-分量风 (v)


```bash
# 安装核心依赖
pip install numpy onnx onnxruntime cdsapi netCDF4 xarray

# 如果您需要使用 GPU 进行推理，请确保安装了 onnxruntime-gpu
# pip install onnxruntime-gpu
```

此外，您需要一个有效的 `cdsapi` 密钥。请在您的主目录下创建 `.cdsapirc` 文件，并填入您的 UID 和 API Key。
url: https://cds.climate.copernicus.eu/api
key: dd996bff-8b8b-496c-aa47-21d3109be062


## 完整执行流程

请严格按照以下顺序执行脚本。

---

### 步骤 1: 准备初始数据 (`1_data_prepare.py`)

**作用:**
此脚本负责从哥白尼气候数据中心（CDS）下载指定日期的 ERA5 再分析数据，并将其转换为模型推理所需的 `.npy` 格式。

**操作:**
1.  打开 `1_data_prepare.py` 文件。
2.  根据您的需求，修改 `date_time` 变量来设定预报的**起始时间**。
3.  运行脚本:
    ```bash
    python 1_data_prepare.py
    ```

**输出:**
脚本会创建一个新的目录，例如 `forecasts/1997-08-16-02-00/`，其中包含：
*   `surface.nc`, `upper.nc`: 从 CDS 下载的原始 NetCDF 数据。
*   `input_surface.npy`, `input_upper.npy`: 转换后供模型使用的初始场数据。

---
- Dimensions (维度) :

- valid_time: 1 : 只有一个有效时间点。
- pressure_level: 13 : 垂直方向有13个气压层。
- latitude: 721 : 纬度有721个格点。
- longitude: 1440 : 经度有1440个格点。
- Coordinates (坐标) :

- valid_time : 明确标示了这个唯一的时间点是 1997-08-16T02:00:00 。
- pressure_level : 列出了13个气压层的高度值（单位：百帕）。
- latitude , longitude : 经纬度格点的具体数值。
- Data variables (数据变量) :
这些是这个初始时刻的物理量：

- z : 位势高度 (Geopotential)
- q : 比湿 (Specific humidity)
- t : 温度 (Temperature)
- u : U风分量 (东-西方向风速)
- v : V风分量 (南-北方向风速)
- Attributes (属性) :

- GRIB_centre: ecmf : 说明原始数据来自 ecmf ，即欧洲中期天气预报中心 (European Centre for Medium-Range Weather Forecasts)。
- history : 记录了该文件是如何被创建的（通过 cfgrib 工具从 GRIB 格式转换而来）。
### 步骤 2: 运行模型推理 (`2_inference.py`)

**作用:**
这是核心步骤。该脚本加载步骤1中生成的初始场数据，并使用盘古模型进行循环迭代，预测未来的天气状况。

**操作:**
1.  打开 `2_inference.py` 文件。
2.  确认 `date_time` 与 `1_data_prepare.py` 中的设置一致。
3.  设置 `date_time_final` 来定义预报的**结束时间**。
4.  在 `while` 循环中，选择您希望使用的模型（例如 `model_1` 代表1小时步长）。
5.  运行脚本:
    ```bash
    python 2_inference.py
    ```

**输出:**
脚本会在 `results/` 目录下生成一系列 `.npy` 文件，每个文件代表一个时间点的预报结果，例如 `output_surface_1997-08-16-03-00.npy`。

---

### 步骤 3: 解码推理结果 (`3_forecast_decode.py`)

**作用:**
模型输出的 `.npy` 文件是原始的数组数据，缺少地理坐标等元信息。此脚本负责将这些 `.npy` 文件解码，转换回带有完整元数据的、独立的 `.nc` 文件。

**操作:**
1.  打开 `3_forecast_decode.py` 文件。
2.  确保 `date_time` 和 `date_time_final` 与 `2_inference.py` 中的设置完全一致。
3.  运行脚本:
    ```bash
    python 3_forecast_decode.py
    ```

**输出:**
脚本会在 `outputs/` 目录下生成与 `results/` 中 `.npy` 文件相对应的 `.nc` 文件，例如 `output_surface_1997-08-16-03-00.nc`。

---

### 步骤 4: 合并为时间序列文件 (`4_combine_netcdf.py`)

**作用:**
将上一步生成的所有离散的、单时间点的 `.nc` 文件合并成一个包含完整时间序列的 NetCDF 文件，以便在 Panoply 等软件中进行可视化和分析。

**操作:**
1.  打开 `4_combine_netcdf.py` 文件。
2.  修改 `input_dir` 变量，使其指向 `3_forecast_decode.py` 生成的 `outputs` 目录。
3.  设置 `file_type_to_process` 变量，选择是处理 `upper` (高空) 数据还是 `surface` (地面) 数据。
4.  运行脚本:
    ```bash
    python 4_combine_netcdf.py
    ```

**输出:**
在 `input_dir` 目录中生成一个最终的合并文件，例如 `combined_upper_timeseries.nc`。

---

## 辅助工具

### 数据格式检查 (`5_数据格式检查.yaml`)

**作用:**
这不是一个可执行脚本，而是一个包含检查命令的示例文件。您可以用它来快速查看任何 `.nc` 文件的内部数据结构。

**操作:**
复制文件中的命令，并根据您要检查的文件路径进行修改，然后在终端中执行。
```bash
python -c "import xarray as xr; ds = xr.open_dataset('你的文件路径.nc'); print(ds)"
```

- Dimensions (维度) :

- time: 126 : 这是最关键的变化 。您的数据现在有了一个时间维度，包含了126个时间点。这正是我们通过合并文件想要达到的效果。
- level: 13 : 数据包含13个垂直气压层。
- latitude: 721 : 纬度方向有721个格点。
- longitude: 1440 : 经度方向有1440个格点。
- Coordinates (坐标) :

- time (time) datetime64[ns] : time 维度现在有关联的坐标值，这些值是标准的日期时间格式（从 1997-08-16T03:00:00 开始）。Panoply 会自动识别这个坐标并用它来创建时间轴。
- longitude (longitude) float32 : 经度坐标值。
- latitude (latitude) float32 : 纬度坐标值。
- Data variables (数据变量) :

- 文件包含了 geopotential (位势)、 specific_humidity (比湿)、 temperature (温度)、 u_component_of_wind (U风分量) 和 v_component_of_wind (V风分量) 这五个变量。
- 最重要的是，现在每个变量都是一个四维数组，其维度是 (time, level, latitude, longitude) 。这意味着每个变量都包含了所有126个时间步的数据。

## 注意事项

1.  **时间一致性:** 在 `1_data_prepare.py`, `2_inference.py`, `3_forecast_decode.py` 这三个脚本中，起始时间 `date_time` **必须保持严格一致**，否则会导致流程中断。
2.  **路径依赖:** 整个流程是强依赖于目录结构的。请不要随意更改 `forecasts`, `results`, `outputs` 等目录的名称。
3.  **模型选择:** 在 `2_inference.py` 中，您一次只能选择一种预报步长（1h, 3h, 6h, 24h）。请确保只取消注释一个模型块。
4.  **文件覆盖:** 如果您使用相同的起止时间重复运行流程，旧的输出文件可能会被覆盖。
5.  **资源消耗:** 天气预报是计算密集型任务。推理过程（特别是长序列预报）可能会消耗大量的时间和计算资源。


用panoply可视化 不要用python库
安装包在E:\PanoplyWin-5.8.1.zip
需要下载java 安装包在E:\jdk-25_windows-x64_bin.exe
