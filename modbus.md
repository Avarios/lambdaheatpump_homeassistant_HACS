











LAMBDA Wärmepumpen





## Datum:
## 13.02.2025











## MODBUS BESCHREIBUNG UND
## PROTOKOLL

## 13.02.2025


## 1
## 1 Inhaltsverzeichnis
2 Kommunikations-Eigenschaften .......................................................................................... 2
3 Modbus Protokoll TCP & RTU ............................................................................................ 2
3.1 Index ...................................................................................................................... 2
3.2 Subindex ................................................................................................................ 2
3.3 Number .................................................................................................................. 4
4 Modbus Client als Datenquelle definieren ........................................................................... 5
5 Modbus TCP/IP Einstellungen ............................................................................................ 6
5.1 Kommunikation Einstellungen................................................................................. 7
5.2 Freigegebene Functioncodes ................................................................................. 7
6 Modbus RTU Einstellungen ................................................................................................ 7
6.1 Kommunikationseinstellungen ................................................................................ 8
6.2 Freigegebene Functioncodes ................................................................................. 8


Abbildung 1: Konfiguration Module Seite 1................................................................................. 3
Abbildung 2: Konfiguration Module Seite 2................................................................................. 3
Abbildung 3: Modbusclient als Datenquelle für Außentemperatur definieren .............................. 5
Abbildung 4: Modbus Client als Datenquelle für PV-Überschuss definieren ............................... 5
Abbildung 5: Modbus Client als Datenquelle für Heizkreis definieren ......................................... 6
Abbildung 6: Netzwerkeinstellungen .......................................................................................... 6
Abbildung 7: Darstellung Display und RS485 Anschluss ............................................................ 7
Abbildung 8: Konfiguration Modbus RTU ................................................................................... 8

Tabelle 1: Beispiel für Index-Vergabe ........................................................................................ 4


## 13.02.2025


## 2

2 Kommunikations-Eigenschaften
Es können eine Reihe von Parameter und Istwerte von der Steuerzentrale der Wärmepumpe ausgelesen
bzw. beschrieben werden. Die Steuerzentrale fungiert dabei als Server (Slave).
Die Zeit eines Kommunikationstimeout beträgt 1min. Erfolgt in dieser Zeit kein Abruf wird die
Verbindung geschlossen und muss neu aufgebaut werden.
Die Lesefunktion erfolgt über die Modbus Funktionscode 0x03 (read multiple holding register)
Die Schreibfunktion erfolgt über die Modbus Funktionscode 0x10 (write multiple writing register)
ACHTUNG: Steuerzentrale kann nur als Server (Slave) agieren!

3 Modbus Protokoll TCP & RTU
Die Register Adresse ist wie folgt strukturiert.
X _ _ _ ->  Erste Stelle:   Index (wird von Modultyp vorgegeben)
_ X _ _ -> Zweite Stelle:  Subindex (wird von Modulnummer vorgegeben)
_ _ X X -> Letzten 2 Stellen: Number (wird von Datenpunkt vorgegeben)

## 3.1 Index
Der Index wird über das Modul vorgegeben.
## • General  = 0
## • Heatpump  = 1
## • Boiler  = 2
## • Buffer  = 3
## • Solar  = 4
- Heating circuit = 5

## 3.2 Subindex
Die Modulnummer ergibt sich aus der Reihenfolge wie gleichartige Modultypen im Konfigurationsmodul
angelegt wurden. Hiervon ausgenommen ist Modultyp General => Subindex fix vergeben.
Module, die weiter oben gereiht sind (niedrigerer Nr.) werden über den niedrigeren Subindex
angesprochen.


## 13.02.2025


## 3
## Beispiel:

## Abbildung 1: Konfiguration Module Seite 1

## Abbildung 2: Konfiguration Module Seite 2



## 13.02.2025


## 4
In diesem Fall besitzt:
Tabelle 1: Beispiel für Index-Vergabe
## Nr Modulname Subindexname Subindex
Nr. 1 WP Heizen M Heat pump 1 0
Nr. 9 WP Heizen + WW S Heat pump 2 1
## Nr. 2 Brauchwasser Boiler 1 0
## Nr. 3 Puffer Buffer 1 0
## Nr. 10 Pool Buffer 2 1
## Nr. 4 Heizkreis 1 Circuit 1 0
## Nr. 5 Heizkreis 2 Circuit 2 1
## Nr. 6 Heizkreis 3 Circuit 3 2
## Nr. 7 Heizkreis 4 Circuit 4 3
## Nr. 8 Poolkreis Circuit 5 4

Z.B. Register zum Auslesen der Vorlauftemperatur (flowline temperature) der Wärmepumpe
„Heizen+WW S“:
## 1  1  04  = 1104
## Index  Subindex Number

## 3.3 Number
Die Number ist dem spezifischen Datenpunkt der ausgelesen oder beschrieben werden soll zugeordnet
(siehe Modbusprotokoll). Wenn Datenpunkte zwischen 00-49 die beschrieben werden sollen, muss der
Wert regelmäßig aktualisiert werden (Timeout nach 5min). Ansonsten wird der Wert als ungültig
betrachtet und eine Defaultwert wird zugewiesen. Datenpunkte über 50 können einmalig beschrieben
werden. Der Wert wird dauerhaft gespeichert.


## 13.02.2025


## 5
4 Modbus Client als Datenquelle definieren
Folgende Datenpunkte, die separat in der Bedienoberfläche aktiviert werden müssen, definieren den
Modbus Client als Datenquelle
## Außentemperatur

Abbildung 3: Modbusclient als Datenquelle für Außentemperatur definieren
Überschussenergie (PV Überschuss)

Abbildung 4: Modbus Client als Datenquelle für PV-Überschuss definieren

## 13.02.2025


## 6

## Raumfühler

Abbildung 5: Modbus Client als Datenquelle für Heizkreis definieren

5 Modbus TCP/IP Einstellungen
Die Kommunikation erfolgt über den Netzwerkanschluss des Displays. Stellen Sie sicher, dass die
Verbindung zum Netzwerk funktioniert, und richten Sie das Gerät im Netzwerk im Menüpunkt
Netzwerkeinstellungen ein (Suche einer freien IP Adresse mittel DHCP oder manuelle Vergabe).

## Abbildung 6: Netzwerkeinstellungen


## 13.02.2025


## 7
## 5.1 Kommunikation Einstellungen
- Unit ID ist 1
- Kommunikation erfolgt über Port 502
- Es können bis zu 16 Kommunikationskanäle (16 Master) bedient werden.
- Die Server IP Adresse wird in der Steuerung auf der Seite „Netzwerkeinstellungen“ angezeigt.
## • ACHTUNG!!!:
Die Verbindung darf nicht bei jeder Modbusanforderung aufgebaut und wieder geschlossen
werden. Ansonsten kann es zu schweren Störungen kommen.

## 5.2 Freigegebene Functioncodes
- Read: Functionscode 0x03 (read multiple holding register)
- Write: Functionscode 0x10 (write multiple writing register)

6 Modbus RTU Einstellungen
Die Kommunikation erfolgt über den RS485 Anschluss auf der Rückseite des Bedienteils. Es müssen zwei
Abschlusswiderstände mit je 120 Ohm an den Endgeräten des Bussystems vorhanden sein.

Abbildung 7: Darstellung Display und RS485 Anschluss

## 13.02.2025


## 8
## 6.1 Kommunikationseinstellungen

Abbildung 8: Konfiguration Modbus RTU

## 6.2 Freigegebene Functioncodes
- Read: Functionscode 0x03 (read multiple holding register)
- Write: Functionscode 0x10 (write multiple writing register)




ModulIndexSubintexNumberRegister nameRead / WriteData formatUnitRegister desciption
00Hp Error stateROUINT16[Nr]
## 0 = NONE,
## 1 = MESSAGE,
## 2 = WARNING,
## 3 = ALARM,
## 4 = FAULT
01Hp Error numberROINT16[Nr]  Scrolling through all active error numbers (Nr.1 - Nr.99)
02Hp StateROUINT16[Nr]
## 0 = INIT,
## 1 = REFERENCE,
## 2 = RESTART-BLOCK,
## 3 = READY,
## 4 = START PUMPS,
## 5 = START COMPRESSOR,
## 6 = PRE-REGULATION,
## 7 = REGULATION,
## 8 = Not Used,
## 9 = COOLING,
## 10 = DEFROSTING,
## 20 = STOPPING,
## 30 = FAULT-LOCK,
## 31 = ALARM-BLOCK,
## 40 = ERROR-RESET
03Operating stateROUINT16[Nr]
## 0 = STBY,
## 1 = CH,
## 2 = DHW,
## 3 = CC,
## 4 = CIRCULATE,
## 5 = DEFROST,
## 6 = OFF,
## 7 = FROST,
## 8 = STBY-FROST,
9 = Not used,
## 10 = SUMMER,
## 11 = HOLIDAY,
## 12 = ERROR,
## 13 = WARNING,
## 14 = INFO-MESSAGE,
## 15 = TIME-BLOCK,
## 16 = RELEASE-BLOCK,
## 17 = MINTEMP-BLOCK,
## 18 = FIRMWARE-DOWNLOAD
04T-flowROINT16     [0.01°C] Flow line temperature
05T-returnROINT16     [0.01°C] Return line temperature
06Vol. sinkROINT16    [0.01l/min] Volume flow heat sink
07T-EQinROINT16     [0.01°C] Energy source inlet temperature
08T-EQoutROINT16     [0.01°C] Energy sorurce outlet temperature
09Vol. sourceROINT16    [0.01l/min] Volume flow energy source
10Compressor-RatingROUINT16    [0.01%]  Compressor unit  rating
11Qp heatingROINT16[0.1kW] Actual heating capacity
12FI power consumptionROINT16[Watt]  Frequency inverter  actual power consumption
13COPROINT16[0.01%]  Coefficient of performance
14Modbus request release passwordRWUINT16[Nr]  Password register to release modbus request registers (maximum 10 retries are possieble)
15Request typeRWINT16[Nr]
## 0 = NO REQUEST,
## 1 = FLOW PUMP CIRCULATION,
## 2 = CENTRAL HEATING,
## 3 = CENTRAL COOLING,
## 4 = DOMESTIC HOT WATER
16Request flow line tempRWINT16[0.1°C]  Requested flow line temperature. (min = 0.0°C, max = 70.0°C)
17Request return line tempRWINT16[0.1°C]  Requested return line temperature. (min = 0.0°C, max = 65.0°C)
18Request heat sink temp. diffRWINT16[0.1K]  Requested temperature difference between flow line and return line. (min = 0.0K, max = 35.0K)
19Relais state for 2nd heating stageROINT160/1  1 = NO-Relais for 2nd heating stage is activated
## 20
## 21
## 22
## 23
Statistic VdA E since last reset
Statistic VdA Q since last reset
## RO
## RO
Heat pump (ModulNr. 1-5)1
heat pump 1 = 0
heat pump 2 = 1
heat pump 3 = 2
heat pump 4 = 3
heat pump 5 = 4
## INT32
## INT32
[Wh]
[Wh]
Accumulated electrical energy consumption of compressor unit since last statistic reset
Accumulated thermal energy output of compressor unit since last statistic reset



