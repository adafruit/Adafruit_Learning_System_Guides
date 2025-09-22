# SPDX-FileCopyrightText: 2025 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
from datetime import datetime
from sqlalchemy import Column, Integer, Float, String, DateTime, create_engine
from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()


class SensorReading(Base):
    """
    Database model for environmental sensor readings.
    """

    __tablename__ = "sensor_readings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    datetime = Column(DateTime, nullable=False, default=datetime.utcnow)
    room_name = Column(String(100), nullable=False)
    temperature_c = Column(Float, nullable=True)
    temperature_f = Column(Float, nullable=True)
    humidity = Column(Float, nullable=True)  # Percentage
    pm25 = Column(Float, nullable=True)  # PM2.5 in µg/m³
    voc_index = Column(Float, nullable=True)  # VOC index
    nox_index = Column(Float, nullable=True)  # NOx index
    co2 = Column(Float, nullable=True)  # CO2 in ppm

    def __repr__(self):
        return (
            f"<SensorReading(room='{self.room_name}', "
            f"datetime='{self.datetime}', "
            f"temp_c={self.temperature_c}, "
            f"humidity={self.humidity})>"
        )


if __name__ == "__main__":

    def create_database(db_url="sqlite:///sensor_data.db"):
        """Create the database and all tables."""
        engine = create_engine(db_url, echo=True)

        # Create all tables
        Base.metadata.create_all(engine)

        print(f"Database created successfully at: {db_url}")
        return engine

    # Create the database when script is run directly
    create_database()
