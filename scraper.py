import json
import csv
import requests
import zipfile
import os
import threading
from queue import Queue
from concurrent.futures import ThreadPoolExecutor, as_completed

# API Endpoints
STATION_API = "https://api-partner.krl.co.id/krl-webs/v1/krl-station"
SCHEDULE_API = "https://api-partner.krl.co.id/krl-webs/v1/schedule"

# Authorization Token (Static)
AUTH_TOKEN = "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiIzIiwianRpIjoiMDYzNWIyOGMzYzg3YTY3ZTRjYWE4YTI0MjYxZGYwYzIxNjYzODA4NWM2NWU4ZjhiYzQ4OGNlM2JiZThmYWNmODU4YzY0YmI0MjgyM2EwOTUiLCJpYXQiOjE3MjI2MTc1MTQsIm5iZiI6MTcyMjYxNzUxNCwiZXhwIjoxNzU0MTUzNTE0LCJzdWIiOiI1Iiwic2NvcGVzIjpbXX0.Jz_sedcMtaZJ4dj0eWVc4_pr_wUQ3s1-UgpopFGhEmJt_iGzj6BdnOEEhcDDdIz-gydQL5ek0S_36v5h6P_X3OQyII3JmHp1SEDJMwrcy4FCY63-jGnhPBb4sprqUFruDRFSEIs1cNQ-3rv3qRDzJtGYc_bAkl2MfgZj85bvt2DDwBWPraZuCCkwz2fJvox-6qz6P7iK9YdQq8AjJfuNdl7t_1hMHixmtDG0KooVnfBV7PoChxvcWvs8FOmtYRdqD7RSEIoOXym2kcwqK-rmbWf9VuPQCN5gjLPimL4t2TbifBg5RWNIAAuHLcYzea48i3okbhkqGGlYTk3iVMU6Hf_Jruns1WJr3A961bd4rny62lNXyGPgNLRJJKedCs5lmtUTr4gZRec4Pz_MqDzlEYC3QzRAOZv0Ergp8-W1Vrv5gYyYNr-YQNdZ01mc7JH72N2dpU9G00K5kYxlcXDNVh8520-R-MrxYbmiFGVlNF2BzEH8qq6Ko9m0jT0NiKEOjetwegrbNdNq_oN4KmHvw2sHkGWY06rUeciYJMhBF1JZuRjj3JTwBUBVXcYZMFtwUAoikVByzKuaZZeTo1AtCiSjejSHNdpLxyKk_SFUzog5MOkUN1ktAhFnBFoz6SlWAJBJIS-lHYsdFLSug2YNiaNllkOUsDbYkiDtmPc9XWc"

# Headers
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Authorization": AUTH_TOKEN,
    "Origin": "https://commuterline.id",
    "Referer": "https://commuterline.id/",
}

# Predefined Routes
ROUTES = {
    "Bogor Line": "COMMUTER LINE BOGOR",
    "Cikarang Line": "COMMUTER LINE CIKARANG",
    "Tanjung Priuk Line": "COMMUTER LINE TANJUNGPRIUK",
    "Rangkasbitung Line": "COMMUTER LINE RANGKASBITUNG",
    "Tangerang Line": "COMMUTER LINE TANGERANG",
    "KA Bandara": "BANDARASOEKARNOHATTA"
}

# Fetch all stations
def fetch_stations():
    response = requests.get(STATION_API, headers=HEADERS)
    if response.status_code == 200:
        return response.json().get("data", [])
    else:
        print("Error fetching stations:", response.status_code)
        return []

# Fetch schedules dynamically
def fetch_schedule(station_id):
    print(f"Fetching schedule for {station_id}")       
    params = {"stationid": station_id, "timefrom": "00:00", "timeto": "23:59"}
    response = requests.get(SCHEDULE_API, headers=HEADERS, params=params)
    if response.status_code == 200:
        print(f"Fetched schedule for {station_id}")        
        return station_id, response.json().get("data", [])
    else:
        print(f"Error fetching schedule for {station_id}: {response.status_code}")
        return station_id, []

# Add new API endpoint near the top with other endpoints
TRAIN_SCHEDULE_API = "https://api-partner.krl.co.id/krl-webs/v1/schedule-train"

# Add new function to fetch train schedule
def fetch_train_schedule(train_id):
        print(f"Fetching train schedule for {train_id}")
        params = {"trainid": train_id}
        response = requests.get(TRAIN_SCHEDULE_API, headers=HEADERS, params=params)
        if response.status_code == 200:
            return response.json().get("data", [])
        else:
            print(f"Error fetching train schedule for {train_id}: {response.status_code}")
            return []

if __name__ == "__main__":
    print("Fetching live station data...")
    stations = fetch_stations()

    print("Fetching live train schedules...")
    all_schedules = []
    train_routes = {}  # Store complete routes for each train
    unique_train_ids = set()  # Keep track of unique train IDs
    
    # First pass: collect all train IDs
    with ThreadPoolExecutor(max_workers=25) as executor:
        future_to_station = {
            executor.submit(fetch_schedule, station["sta_id"]): station 
            for station in stations
        }
        
        for future in as_completed(future_to_station):
            station = future_to_station[future]
            try:
                station_id, schedules = future.result()
                for s in schedules:
                    unique_train_ids.add(s["train_id"])
                    all_schedules.append({
                        "station_id": station_id,
                        "station_name": station["sta_name"],
                        "train_id": s["train_id"],
                        "route_id": s["ka_name"],
                        "destination": s["dest"],
                        "arrival_time": s["time_est"]
                    })
            except Exception as e:
                print(f"Error processing station {station['sta_id']}: {e}")

    # Second pass: fetch train schedules concurrently
    print("Fetching individual train schedules...")
    with ThreadPoolExecutor(max_workers=25) as executor:
        future_to_train = {
            executor.submit(fetch_train_schedule, train_id): train_id 
            for train_id in unique_train_ids
        }
        
        for future in as_completed(future_to_train):
            train_id = future_to_train[future]
            try:
                train_routes[train_id] = future.result()
            except Exception as e:
                print(f"Error fetching train schedule for {train_id}: {e}")
                train_routes[train_id] = []

    # Modify stop_times.txt creation to use the complete route
    with open("gtfs/stop_times.txt", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence"])
        for train_id, route in train_routes.items():
            for idx, stop in enumerate(route):
                writer.writerow([
                    f"{train_id}_trip",
                    stop["time_est"],
                    stop["time_est"],
                    stop["station_id"],
                    idx + 1
                ])

    print("Generating GTFS files...")

    os.makedirs("gtfs", exist_ok=True)

    # 1️⃣ Create stops.txt
    with open("gtfs/stops.txt", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["stop_id", "stop_name", "stop_lat", "stop_lon"])
        for station in stations:
            writer.writerow([station["sta_id"], station["sta_name"], "", ""])  # No lat/lon

    # 2️⃣ Create routes.txt (Using unique routes from API data)
    unique_routes = {s["route_id"] for s in all_schedules}
    # with open("gtfs/routes.txt", "w", newline="") as f:
    #     writer = csv.writer(f)
    #     writer.writerow(["route_id", "route_short_name", "route_long_name", "route_type"])
    #     for route_id in unique_routes:
    #         writer.writerow([route_id, route_id, route_id, 2])  # 2 = Rail

    # 3️⃣ Create trips.txt
    with open("gtfs/trips.txt", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["route_id", "service_id", "trip_id"])
        for t in all_schedules:
            writer.writerow([t["route_id"], "1", f"{t['train_id']}_trip"])

    # 4️⃣ Create stop_times.txt
    with open("gtfs/stop_times.txt", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence"])
        for idx, t in enumerate(all_schedules):
            writer.writerow([f"{t['train_id']}_trip", t["arrival_time"], t["arrival_time"], t["station_id"], idx + 1])

    # 5️⃣ Create GTFS.zip
    with zipfile.ZipFile("GTFS.zip", "w") as zipf:
        for filename in ["stops.txt", "routes.txt", "trips.txt", "stop_times.txt"]:
            zipf.write(f"gtfs/{filename}", arcname=filename)

    print("✅ GTFS.zip created successfully!")
