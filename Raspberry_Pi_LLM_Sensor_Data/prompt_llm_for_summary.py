# SPDX-FileCopyrightText: 2025 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
import csv
from datetime import datetime, timedelta, UTC
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from ollama import chat
from db_models import SensorReading

# pylint: disable=too-many-locals

# Database connection configuration
DATABASE_URL = "sqlite:///sensor_data.db"

MODEL = "gemma3:1b"

# Room name to pull data for. Update to match one of your rooms.
ROOM = "Basement"

# Specify a Custom Date Range
# QUERY_START = datetime(2025, 9, 16, 0, 0, 0, tzinfo=UTC)
# QUERY_END = datetime(2025, 9, 18, 19, 0, 0, tzinfo=UTC)

# Defaults to last 24 hours if start and end are None
QUERY_START = None
QUERY_END = None

# Time interval in minutes to export data with i.e. one data point every 30 minutes.
SAMPLE_RATE = 30  # minutes


PROMPT = """Analyze the following environmental sensor data. Provide a summary of its content,
 identify key patterns or insights, and suggest potential further analysis or questions based on this data.

Data:
---
%%_DATA_PLACEHOLDER_%%
---

The data fields are:
- UTC Datetime
- Temperature in degrees F
- Humidity percent
- pm2.5 in µg/m³
- VOC index 
- NOx index
- CO2 in ppm

Please summarize the data, identify key patterns, insights, or trends.
"""


def fetch_data(
    room, start_datetime=None, end_datetime=None, output_file=None, sample_rate=30
):
    """
    Fetch all SensorReading records from a specified time range for RoomC
    and save them to a CSV file

    Args:
        room (str): Room name
        start_datetime (Optional[datetime]): Start of the time range (default: 24 hours ago)
        end_datetime (Optional[datetime]): End of the time range (default: now)
        output_file (str): Name of the CSV file to create
        sample_rate (int): Sampling interval in minutes (e.g., 5 for every 5 minutes)
    """
    # Create database engine and session
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Set default values if not provided
        if end_datetime is None:
            end_datetime = datetime.now(UTC)
        if start_datetime is None:
            start_datetime = end_datetime - timedelta(hours=24)

        # Ensure start_datetime is before end_datetime
        if start_datetime >= end_datetime:
            raise ValueError("start_datetime must be before end_datetime")

        print(f"Fetching data for {room} from {start_datetime} to {end_datetime}")

        # Query for RoomC records within the specified time range
        query = (
            session.query(SensorReading)
            .filter(
                SensorReading.room_name == room,
                SensorReading.datetime >= start_datetime,
                SensorReading.datetime <= end_datetime,
            )
            .order_by(SensorReading.datetime.desc())
        )

        # Execute the query
        results = query.all()

        # Apply sampling if sample_rate > 1
        if sample_rate > 1:
            sampled_results = []
            if results:
                # Start from the most recent record (first in desc order)
                base_time = results[0].datetime

                for reading in results:
                    # Calculate minutes difference from the base time
                    time_diff = abs((base_time - reading.datetime).total_seconds() / 60)

                    # Include reading if it falls on a sample interval
                    if time_diff % sample_rate < 1:  # Allow 1 minute tolerance
                        sampled_results.append(reading)

            results = sampled_results
            print(
                f"Applied {sample_rate}-minute sampling: {len(results)} records selected"
            )

        if output_file is not None:
            # Write results to CSV file
            with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
                fieldnames = [
                    "datetime",
                    "temperature_f",
                    "humidity",
                    "pm25",
                    "voc_index",
                    "nox_index",
                    "co2",
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                # Write header
                writer.writeheader()

                # Write data rows
                for reading in results:
                    writer.writerow(
                        {
                            "datetime": (
                                reading.datetime.isoformat()
                                if reading.datetime
                                else None
                            ),
                            "temperature_f": reading.temperature_f,
                            "humidity": reading.humidity,
                            "pm25": reading.pm25,
                            "voc_index": reading.voc_index,
                            "nox_index": reading.nox_index,
                            "co2": reading.co2,
                        }
                    )

            time_range = end_datetime - start_datetime
            print(
                f"Successfully saved {len(results)} records for RoomC to '{output_file}'"
                + f" (time range: {time_range})"
                + (f" (sampled every {sample_rate} minutes)" if sample_rate > 1 else "")
            )
        return results

    except Exception as e:
        print(f"Error fetching data: {e}")
        return []

    finally:
        # Always close the session
        session.close()


if __name__ == "__main__":

    records = fetch_data(
        room=ROOM,
        start_datetime=QUERY_START,
        end_datetime=QUERY_END,
        sample_rate=30,
        output_file="sensor_data.csv",
    )

    with open("sensor_data.csv", "r") as f:
        csv_data = f.read()

    stream = chat(
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": PROMPT.replace("%%_DATA_PLACEHOLDER_%%", csv_data),
            },
        ],
        stream=True,
    )

    for chunk in stream:
        print(chunk["message"]["content"], end="", flush=True)
