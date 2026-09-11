#!/usr/bin/env python3
import asyncio
from mavsdk import System
from roverservo import roverServo
import simplekml
from utilities import Utilities
import time

#from button_handler import ButtonHandler
# Set the GPIO pin for the servo motor
servo_pin = 19

# Create an instance of the ButtonHandler class
#button_handler = ButtonHandler()

# Call the setup_buttons method to initialize the button interrupts
#button_handler.setup_buttons()

# Initialize servo parameters.
pantaleonRv =  roverServo(Spin=servo_pin, minA=0, maxA=360, minP=0.5, maxP=2.5, frq=50)
relay_status = 0
    
starting_position = None
trigger_distance = 10 # Set the desired distance in meters for the event
kml = simplekml.Kml()
    
async def track_telemetry_and_save_log(drone):
    global relay_status
    
    # Free the serial port before starting
    port = "/dev/ttyACM0"
    Utilities.free_serial_port(port)
    
    # Init the drone.
    await drone.connect(system_address="serial:///dev/ttyACM0:19200")
      # Init the drone.
    
    # Wait for the drone to have a GPS fix
    async for is_fixed in drone.telemetry.gps_info():
        print(f"GPS info: {is_fixed.num_satellites},{is_fixed.fix_type}")
        if is_fixed.num_satellites >= 3 and is_fixed.fix_type.value > 2:
            break
        
    async for health in drone.telemetry.health():
        print(f"Health: {health}")
        if health.is_armable:
            break
    
    # Wait for the drone to have a GPS fix
    async for is_fixed in drone.telemetry.gps_info():
        print(f"GPS info: {is_fixed.num_satellites},{is_fixed.fix_type}")
        if is_fixed.num_satellites >= 3 and is_fixed.fix_type.value > 2:
            break
        
    async for health in drone.telemetry.health():
        print(f"Health: {health}")
        if health.is_armable:
            break
    print("arming...")
    await drone.action.arm()
    
    print("servo test...") 
    pantaleonRv.center()
    time.sleep(1)
    pantaleonRv.left()
    time.sleep(1)
    pantaleonRv.right()
    time.sleep(1)
    

    # Get the initial position
    async for position  in drone.telemetry.position():
        initial_position = position
        break
    
    print(f"Connected to drone at latitude: {initial_position.latitude_deg}, longitude: {initial_position.longitude_deg}")

    global starting_position
     
    # Start telemetry reading.
    print("start position monitor")
    cumulative_distance = 0.0

    async for position in drone.telemetry.position():
        if starting_position is None:
            starting_position = position
            continue
                
        distance = Utilities.calculate_distance(starting_position, position)
        #print(distance)
        
        if distance >= trigger_distance:
            if relay_status == 0:
                relay_status = 1
                pantaleonRv.left()
                time.sleep(1)
                direction = "izquierdo"
            else:
                relay_status = 0
                pantaleonRv.right()
                time.sleep(1)
                direction = "derecho"
            
            # Log ground speed, heading, and geo position
            async for position_velocity_ned in drone.telemetry.position_velocity_ned():
                ground_speed = Utilities.calculate_ground_speed(position_velocity_ned)
                break
            async for heading in drone.telemetry.heading():
                break
            print(f"dosificacion cada:{trigger_distance}, ubicacion: {position}, velocidad: {ground_speed}, rumbo: {heading}, direction: {direction}")

            # Create a point in the KML file
            point = kml.newpoint(
                name=f"6g cada {distance:.2f} metros",
                coords=[(position.longitude_deg, position.latitude_deg)]
            )
            point.description = f"velocidad: {ground_speed}\nrumbo: {heading}\lado: {direction}"
            kml.save("telemetry_20mts_log.kml")
            # Reset the starting position for the next event
            starting_position = position

if __name__ == "__main__":
    drone = System()
    
    try:
        # Start the main function.
        asyncio.run(track_telemetry_and_save_log(drone))
    except Exception as e:
        print(f"An error occurred: {e}")
    except KeyboardInterrupt:
        print("Shutting down gracefully...")
    finally:    
        # Save the KML file
        kml.save("telemetry_20mts_log.kml")
           
    
