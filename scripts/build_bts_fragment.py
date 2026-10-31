"""Build the ATL fragment of BTS On-Time Performance for the flight-delay project.

usage: build_bts_fragment.py OUT.csv ZIP [ZIP ...]
Keeps flights that departed from ATL and were neither cancelled nor diverted.
"""

import sys
import zipfile

import pandas as pd

COLS = [
    "FlightDate",
    "Reporting_Airline",
    "Flight_Number_Reporting_Airline",
    "Origin",
    "CRSDepTime",
    "DayOfWeek",
    "ArrDelay",
    "Cancelled",
    "Diverted",
]
frames = []
for path in sys.argv[2:]:
    with zipfile.ZipFile(path) as archive:
        name = next(n for n in archive.namelist() if n.endswith(".csv"))
        frame = pd.read_csv(archive.open(name), usecols=COLS)
    frame = frame[(frame.Origin == "ATL") & (frame.Cancelled == 0) & (frame.Diverted == 0)]
    frames.append(frame.dropna(subset=["ArrDelay"]))
data = pd.concat(frames)
out = pd.DataFrame(
    {
        "FlightDate": data.FlightDate,
        "Carrier": data.Reporting_Airline,
        "FlightNumber": data.Flight_Number_Reporting_Airline.astype(int),
        "DepHour": (data.CRSDepTime // 100).astype(int) % 24,
        "IsWeekend": data.DayOfWeek.isin([6, 7]).astype(int),
        "ArrDelay": data.ArrDelay.astype(int),
    }
)
out = out.sort_values(["FlightDate", "DepHour", "Carrier", "FlightNumber"], kind="stable")
out.to_csv(sys.argv[1], index=False)
print(
    len(out),
    out.FlightDate.min(),
    out.FlightDate.max(),
    int(out.duplicated().sum()),
    round(float((out.ArrDelay >= 15).mean()), 4),
)
