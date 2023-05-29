#include <SoftwareSerial.h>
#include <stdint.h>

#define MAX485_DE_RE 3
#define MODBUS_GENERATOR 0xA001
#define RESPONSE_TIMEOUT 5000 // Timeout in milliseconds

SoftwareSerial LoRaSerial(6, 7); // RX, TX
SoftwareSerial RS485Serial(10, 11); // RX, TX

unsigned long ResponseTime;

void ModbusCalcCRC(unsigned char* Frame, unsigned char LenFrame, unsigned int &CRC)
{
  unsigned char CntByte;
  unsigned char j;
  unsigned char bitVal;
  CRC = 0xFFFF;
  for (CntByte = 0; CntByte < LenFrame; CntByte++)
  {
    CRC ^= Frame[CntByte];
    for (j = 0; j < 8; j++)
    {
      bitVal = CRC & 0x0001;
      CRC = CRC >> 1;
      if (bitVal == 1)
        CRC ^= MODBUS_GENERATOR;
    }
  }
}

void setup()
{
  pinMode(MAX485_DE_RE, OUTPUT);
  digitalWrite(MAX485_DE_RE, 0);
  
  Serial.begin(9600);
  LoRaSerial.begin(9600);
  RS485Serial.begin(9600);
  RS485Serial.stopListening();
  LoRaSerial.listen();
}

void loop()
{
  if (LoRaSerial.isListening())
  {
    while (LoRaSerial.available())
    {
      uint8_t command[256];
      uint8_t commandLen;
      uint16_t commandCRC;
      commandLen = LoRaSerial.readBytes(command, 256);
      Serial.print("Received from master: ");
      for (uint8_t i = 0; i < commandLen; i++)
      {
        Serial.print(command[i], HEX);
      }
      Serial.println();
      if (commandLen >= 8)
      {
        ModbusCalcCRC(command, commandLen - 2, commandCRC);
        if (commandCRC == ((command[commandLen - 1] << 8) | command[commandLen - 2]))
        {
          LoRaSerial.stopListening();
          RS485Serial.listen();
          digitalWrite(MAX485_DE_RE, 1);
          delay(100);
          for (uint8_t i = 0; i < commandLen; i++)
          {
            RS485Serial.write(command[i]);
          }
          delay(10);
          digitalWrite(MAX485_DE_RE, 0);
        }
        else
        {
          LoRaSerial.println("CRC error in the command from the master");
        }
      }
    }
  }

  if (RS485Serial.isListening())
  {
    
    while (RS485Serial.available())
    {
      uint8_t response[256];
      uint8_t responseLen;
      uint16_t responseCRC;
      responseLen = RS485Serial.readBytes(response, 256);
      ModbusCalcCRC(response, responseLen - 2, responseCRC);
      if (responseCRC == ((response[responseLen - 1] << 8) | response[responseLen - 2]))
      {
        RS485Serial.stopListening();
        LoRaSerial.listen();
        delay(100);
        Serial.print("Received from Dixell: ");
        for (uint8_t i = 0; i < responseLen; i++)
        {
          LoRaSerial.write(response[i]);
          Serial.print(response[i], HEX);
        }
        Serial.println();
      }
      else
      {
        RS485Serial.stopListening();
        LoRaSerial.listen();
        LoRaSerial.println("CRC error from the Dixell");
      }
    }
  }
}