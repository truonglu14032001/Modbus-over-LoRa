import serial
import time

ser = serial.Serial('/dev/ttyAMA0', 9600)  # The LoRa module is connected to UART port '/dev/ttyAMA0'

def ModbusCalcCRC(command):
    MODBUS_GENERATOR = 0xA001
    CRC = 0xFFFF
    for byte in command:
        CRC ^= byte
        for _ in range(8):
            bitVal = CRC & 0x0001
            CRC = CRC >> 1
            if bitVal == 1:
                CRC ^= MODBUS_GENERATOR
    return CRC

def send_command(command):
    CRC = ModbusCalcCRC(command)
    command.extend([CRC & 0xFF, (CRC >> 8) & 0xFF])
    ser.write(bytearray(command))
    time.sleep(3)  # Wait for a response
    #if ser.inWaiting() == 0:
    #    print("No response from Slave")
    #    return
    #else:
    response = list(ser.read(ser.inWaiting()))
    response_hex = [f"{byte:02X}" for byte in response]
    print("Received response from Slave: ", response_hex)
    return response

def read_register256():
    command = [0x01, 0x03, 0x01, 0x00, 0x00, 0x01]  # Read register 256 (0x0100) from slave 1
    response = send_command(command)
    received_crc = (response[-2] | (response[-1] << 8))
    
    if received_crc != ModbusCalcCRC(response[:-2]): # Check the CRC first
        print("Invalid CRC")
    elif response[1] >= 0x80:  # Check for an exception response
        print("Received exception from slave.")
        print("Exception code: ", response[2])
    else:
        value = ((response[3] << 8) | response[4])/10
        print(f"Data: {value} \u00b0C")

def read_coils_and_discrete_inputs():
    while True:
        slave_id = int(input("Enter slave ID: "))
        if slave_id < 0 or slave_id > 255:
            print("Invalid slave address. Please enter a value between 0 and 255.")
            continue
        function_code = int(input("Enter function code (1 for coils, 2 for discrete inputs): "), 16)
        if function_code != 1 and function_code != 2:
            print("Invalid function code. Please enter 3 or 4.")
            continue
        start_address = int(input("Enter starting address: "))
        quantity = int(input("Enter quantity to read: "))

        # Create the command frame
        command = [slave_id, function_code, (start_address >> 8) & 0xFF, start_address & 0xFF,
                   (quantity >> 8) & 0xFF, quantity & 0xFF]

        # Send the command and read the response
        response = send_command(command)
        received_crc = (response[-2] | (response[-1] << 8))

        if received_crc != ModbusCalcCRC(response[:-2]): # Check the CRC first
            print("Invalid CRC")
        elif response[1] >= 0x80:  # Check for an exception response
            print("Received exception from slave.")
            print("Exception code: ", response[2])
        else:
            # Print out the read data
            print("Read data:")
            data = response[3:-2]  # Exclude the slave id, function code, byte count and crc
            for byte in data:
                print(f"{byte:08b}")
        break

def read_registers():
    while True:
        slave_id = int(input("Enter slave address (in decimal): "))
        if slave_id < 0 or slave_id > 255:
            print("Invalid slave address. Please enter a value between 0 and 255.")
            continue
        function_code = int(input("Enter function code (3 or 4): "), 16)
        if function_code != 3 and function_code != 4:
            print("Invalid function code. Please enter 3 or 4.")
            continue
        register_start_address = int(input("Enter start register address (in decimal): "))
        register_quantity = int(input("Enter quantity of registers (in decimal): "))
        
        command = [slave_id, function_code, 
                   (register_start_address >> 8) & 0xFF, register_start_address & 0xFF,
                   (register_quantity >> 8) & 0xFF, register_quantity & 0xFF]
        
        response = send_command(command)
        received_crc = (response[-2] | (response[-1] << 8))
        
        if received_crc != ModbusCalcCRC(response[:-2]): # Check the CRC first
            print("Invalid CRC")
        elif response[1] >= 0x80:  # Then check for an exception response
            print("Received exception from slave.")
            print("Exception code: ", response[2])
        else:
            print("Data: ", response[3:-2]) # Exclude the CRC and the first 3 bytes (slave address, function code and byte count)
        break

def write_single():
    while True:
        slave_id = int(input("Enter slave ID: "))
        if slave_id < 0 or slave_id > 255:
            print("Invalid slave address. Please enter a value between 0 and 255.")
            continue
        function_code = int(input("Enter function code (5 for coil, 6 for register): "), 16)
        if function_code != 5 and function_code != 6:
            print("Invalid function code. Please enter 5 or 6.")
            continue
        address = int(input("Enter address: "))
        value = int(input("Enter value to write: "))

        # Create the command frame
        command = [slave_id, function_code, (address >> 8) & 0xFF, address & 0xFF,
                   (value >> 8) & 0xFF, value & 0xFF]

        # Send the command and read the response
        response = send_command(command)
        received_crc = (response[-2] | (response[-1] << 8))
        if received_crc != ModbusCalcCRC(response[:-2]): # Check the CRC first
            print("Invalid CRC")
        elif response[1] >= 0x80:  # Then check for an exception response
            print("Received exception from slave.")
            print("Exception code: ", response[2])
        else:
            print("Data: ", response[2:-2])
        break

def write_multiple_coils():
    while True:
        slave_id = int(input("Enter slave ID: "))
        if slave_id < 0 or slave_id > 255:
            print("Invalid slave address. Please enter a value between 0 and 255.")
            continue
        start_address = int(input("Enter start address: "))
        quantity = int(input("Enter quantity of coils: "))
        byte_count = (quantity + 7) // 8 #Calculate the number of bytes required to store coils
        
        #Enter all value for coil
        coils = []
        for i in range(quantity):
            coil_value = int(input(f"Enter value for coil {start_address + i}: "), 16)
            coils.append(coil_value)

        #Create frame write multiple coils
        command = [slave_id, 0x0F, (start_address >> 8) & 0xFF, start_address & 0xFF,
                   (quantity >> 8) & 0xFF, quantity & 0xFF, byte_count]
        # Add coils values to frame
        for i in range(byte_count):
            byte = 0
            for j in range(8):
                if i*8 + j < quantity:
                    byte |= coils[i*8 + j] << j
            command.append(byte)

        # Send commands and read the response
        response = send_command(command)
        received_crc = (response[-2] | (response[-1] << 8))
        if received_crc != ModbusCalcCRC(response[:-2]): # Check the CRC first
            print("Invalid CRC")
        elif response[1] >= 0x80:  # Then check for an exception response
            print("Received exception from slave.")
            print("Exception code: ", response[2])
        else:
            print("Data: ", response[2:-2])
        break

def write_multiple_registers():
    while True:
        slave_id = int(input("Enter slave ID: "))
        if slave_id < 0 or slave_id > 255:
            print("Invalid slave address. Please enter a value between 0 and 255.")
            continue
        function_code = 0x10
        start_address = int(input("Enter starting register address: "))
        num_registers = int(input("Enter the number of registers to write: "))
        byte_count = num_registers * 2

        # Get register values from user input
        register_values = []
        for i in range(num_registers):
            register_values.append(int(input(f"Enter value for register {start_address + i}: ")))

        # Create the command frame
        command = [slave_id, function_code, (start_address >> 8) & 0xFF, start_address & 0xFF,
                   (num_registers >> 8) & 0xFF, num_registers & 0xFF,
                   byte_count]

        for value in register_values:
            command.append((value >> 8) & 0xFF)
            command.append(value & 0xFF)

        # Send the command and read the response
        response = send_command(command)
        received_crc = (response[-2] | (response[-1] << 8))
        if received_crc != ModbusCalcCRC(response[:-2]): # Check the CRC first
            print("Invalid CRC")
        elif response[1] >= 0x80:  # Then check for an exception response
            print("Received exception from slave.")
            print("Exception code: ", response[2])
        else:
            print("Data: ", response[2:-2])
        break

def mask_write_register():
    while True:
        slave_id = int(input("Enter slave ID: "))
        if slave_id < 0 or slave_id > 255:
            print("Invalid slave address. Please enter a value between 0 and 255.")
            continue
        start_address = int(input("Enter register address: "))
        and_mask = int(input("Enter AND mask: "))
        or_mask = int(input("Enter OR mask: "))

        # Create the command frame
        command = [slave_id, 0x16, (start_address >> 8) & 0xFF, start_address & 0xFF,
                   (and_mask >> 8) & 0xFF, and_mask & 0xFF, 
                   (or_mask >> 8) & 0xFF, or_mask & 0xFF]

        # Send the command and read the response
        response = send_command(command)
        received_crc = (response[-2] | (response[-1] << 8))
        if received_crc != ModbusCalcCRC(response[:-2]): # Check the CRC first
            print("Invalid CRC")
        elif response[1] >= 0x80:  # Then check for an exception response
            print("Received exception from slave.")
            print("Exception code: ", response[2])
        else:
            print("Data: ", response[2:-2])
        break

def read_write_multiple_registers():
    while True:
        slave_id = int(input("Enter slave ID: "))
        read_start_address = int(input("Enter the start address of registers to read: "))
        quantity_to_read = int(input("Enter the quantity of registers to read: "))
        write_start_address = int(input("Enter the start address of registers to write: "))
        quantity_to_write = int(input("Enter the quantity of registers to write: "))
        write_register_values = [int(input(f"Enter value for register {i+1}: ")) for i in range(quantity_to_write)]

        # Create the command frame
        command = [slave_id, 0x17, (read_start_address >> 8) & 0xFF, read_start_address & 0xFF,
                   (quantity_to_read >> 8) & 0xFF, quantity_to_read & 0xFF, 
                   (write_start_address >> 8) & 0xFF, write_start_address & 0xFF,
                   (quantity_to_write >> 8) & 0xFF, quantity_to_write & 0xFF,
                   len(write_register_values)]
        
        for value in write_register_values:
            command.extend([(value >> 8) & 0xFF, value & 0xFF])

        # Send the command and read the response
        response = send_command(command)
        received_crc = (response[-2] | (response[-1] << 8))
        if received_crc != ModbusCalcCRC(response[:-2]): # Check the CRC first
            print("Invalid CRC")
        elif response[1] >= 0x80:  # Then check for an exception response
            print("Received exception from slave.")
            print("Exception code: ", response[2])
        else:
            print("Data: ", response[3:-2]) # Exclude the CRC and the first 3 bytes (slave address, function code and byte count)

print("Menu:")
print("1. Read register 256")
print("2. Read coils and discrete inputs")
print("3. Read registers")
print("4. Write single")
print("5. Write multiper coils")
print("6. Write multiper register")
print("7. Mask write register")
print("8. Read write multiple registers")

while True:
    choice = input("Choose an option: ")
    if choice == '1':
        read_register256()
    elif choice == '2':
        read_coils_and_discrete_inputs()
    elif choice == '3':
        read_registers()
    elif choice == '4':
        write_single()
    elif choice == '5':
        write_multiple_coils()
    elif choice == '6':
        write_multiple_registers()
    elif choice == '7':
        mask_write_register()
    elif choice == '8':
        read_write_multiple_registers()
    else:
        print("Invalid option. Please enter a number between 1 and 8.")
