import asyncio
from mavsdk import System
from roverservo import roverServo
import simplekml
from utilities import Utilities
import time
import datetime
import re
import os
import glob
from pykml import parser
from zipfile import ZipFile
from shapely.geometry import Point, Polygon


def extract_kml_from_kmz(kmz_filepath):
    with ZipFile(kmz_filepath, 'r') as kmz:
        kml_filename = kmz.namelist()[0]
        kml_content = kmz.read(kml_filename)
    return parser.fromstring(kml_content)


def get_geofence_coordinates_from_kml(kml_content):
    geofence_coordinates = []
    for element in kml_content.Document.Folder.Placemark.Polygon.outerBoundaryIs.LinearRing.coordinates:
        coords = element.text.split(',')
        geofence_coordinates.append((float(coords[1]), float(coords[0])))  # lat, lon
    return geofence_coordinates


def is_point_within_geofence(lat, lon, geofence_coordinates):
    point = Point(lon, lat)  # Note the order: (lon, lat)
    polygon = Polygon(geofence_coordinates)
    return point.within(polygon)


class DroneTelemetry:

    def __init__(self):
        # Set the GPIO pin for the servo motor
        # Search for any .kmz files in the current directory
        kmz_files = glob.glob("*.kmz")
        self.servo_pin = 19
        self.pantaleonRv = roverServo(Spin=self.servo_pin, minA=0, maxA=360, minP=0.5, maxP=2.5, frq=50)
        self.relay_status = 0
        self.starting_position = None
        # If a .kmz file is found, extract the trigger distance from its name
        if kmz_files:
            self.trigger_distance = DroneTelemetry.extract_distance_from_filename(kmz_files[0])
            kml_content = extract_kml_from_kmz(kmz_files[0])
            self.geofence_coordinates = get_geofence_coordinates_from_kml(kml_content)
        # If no .kmz file is found, set the default trigger distance to 20
        else:
            self.trigger_distance = 20
            self.geofence_coordinates = []
        
        self.kml = simplekml.Kml()
        # Generate unique telemetry filename based on current date and time
        current_time = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        self.kml_filename = f"telemetry_log_{current_time}.kml"
        
    @staticmethod
    def extract_distance_from_filename(filename):
        # Use a regular expression to find a number followed by "_mts" in the filename
        match = re.search(r'(\d+)_mts', filename)
        if match:
            return int(match.group(1))  # Return the number as an integer
        return None  # Return None if no match is found
    
    async def wait_for_gps_and_health(self, drone):
        # Wait for the drone to have a GPS fix and to be armable
        gps_ready = False
        health_ready = False
        while not (gps_ready and health_ready):
            async for is_fixed in drone.telemetry.gps_info():
                print(f"GPS info: {is_fixed.num_satellites},{is_fixed.fix_type}")
                if is_fixed.num_satellites >= 3 and is_fixed.fix_type.value > 2:
                    gps_ready = True
                    break

            async for health in drone.telemetry.health():
                if health.is_armable:
                    health_ready = True
                    break

    async def track_telemetry_and_save_log(self, drone):
        # Free the serial port before starting
        port = "/dev/ttyACM0"
        Utilities.free_serial_port(port)
    
        # Init the drone
        await drone.connect(system_address="serial:///dev/ttyACM0:19200")
        await self.wait_for_gps_and_health(drone)
        await drone.action.arm()
    
        # Servo test
        self.pantaleonRv.center()
        time.sleep(1)
        self.pantaleonRv.left()
        time.sleep(1)
        self.pantaleonRv.right()
        time.sleep(1)
    
        # Get the initial position
        async for position in drone.telemetry.position():
            if not is_point_within_geofence(position.latitude_deg, position.longitude_deg, self.geofence_coordinates):
                continue
            initial_position = position
            break
    
        print(f"Connected to drone at latitude: {initial_position.latitude_deg}, longitude: {initial_position.longitude_deg}")

        cumulative_distance = 0.0
        async for position in drone.telemetry.position():
            if self.starting_position is None:
                self.starting_position = position
                continue

            distance = Utilities.calculate_distance(self.starting_position, position)
            if distance >= self.trigger_distance and is_point_within_geofence(position.latitude_deg, position.longitude_deg, self.geofence_coordinates):
                if self.relay_status == 0:
                    self.relay_status = 1
                    self.pantaleonRv.left()
                    direction = "izquierdo"
                else:
                    self.relay_status = 0
                    self.pantaleonRv.right()
                    direction = "derecho"
                
                time.sleep(1)
                async for position_velocity_ned in drone.telemetry.position_velocity_ned():
                    ground_speed = Utilities.calculate_ground_speed(position_velocity_ned)
                    break
                async for heading in drone.telemetry.heading():
                    break
                print(f"dosificacion cada:{self.trigger_distance}, ubicacion: {position}, velocidad: {ground_speed}, rumbo: {heading}, direction: {direction}")

                # Create a point in the KML file
                point = self.kml.newpoint(
                    name=f"6g cada {distance:.2f} metros",
                    coords=[(position.longitude_deg, position.latitude_deg)]
                )
                point.description = f"velocidad: {ground_speed}\nrumbo: {heading}\lado: {direction}"
                self.save_kml()
                # Reset the starting position for the next event
                self.starting_position = position
                
    def save_kml(self):
        """Save the KML file using the unique filename."""
        self.kml.save(self.kml_filename)
                

if __name__ == "__main__":
    # Replace 'florida_10_mts.kmz' with the actual KMZ file you're using
    drone = System()
    telemetry = DroneTelemetry()
    
    try:
        # Start the main function
        asyncio.run(telemetry.track_telemetry_and_save_log(drone))
    except Exception as e:
        print(f"An error occurred: {e}")
    except KeyboardInterrupt:
        print("Shutting down gracefully...")
    finally:    
        # Save the KML file
        telemetry.save_kml()