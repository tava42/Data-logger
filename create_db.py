# -*- coding: utf-8 -*-
import sqlite3

conn = sqlite3.connect("G:\\Programming\\Python\\Projects\\Larmlogg.db")
c = conn.cursor()

c.execute("CREATE TABLE Larm(Datum TEXT, Modell TEXT, Larm TEXT, Stopptid INTEGER, Antal INTEGER)")

c.execute("CREATE TABLE Tid(Datum TEXT, Modell TEXT, Drifttid INTEGER, Stopptid INTEGER, Cykelstopp INTEGER,"
          " Omställning INTEGER, Beslag INTEGER, Antal INTEGER, Kass_höger INTEGER, Kass_vänster INTEGER)")

c.execute("CREATE TABLE BeslagPerTimme(Datum TEXT, kl_0 INTEGER, kl_1 INTEGER, kl_2 INTEGER, kl_3 INTEGER, kl_4 INTEGER"
          ", kl_5 INTEGER, kl_6 INTEGER, kl_7 INTEGER, kl_8 INTEGER, kl_9 INTEGER, kl_10 INTEGER, kl_11 INTEGER,"
          " kl_12 INTEGER, kl_13 INTEGER, kl_14 INTEGER, kl_15 INTEGER, kl_16 INTEGER, kl_17 INTEGER, kl_18 INTEGER,"
          " kl_19 INTEGER, kl_20 INTEGER, kl_21 INTEGER, kl_22 INTEGER, kl_23 INTEGER)")

c.execute("CREATE TABLE Larm_cykelstopp(Datum TEXT, Modell TEXT, Larm TEXT, Cykelstopp INTEGER)")

conn.commit()
c.close()
conn.close()

conn = sqlite3.connect("G:\\Programming\\Python\\Projects\\temp.db")
c = conn.cursor()

c.execute("CREATE TABLE Modell(Modell TEXT)")

c.execute("CREATE TABLE Larm(Datum TEXT)")

c.execute("CREATE TABLE Temp(id INTEGER, Larm TEXT, Tid INTEGER, PRIMARY KEY(id))")

conn.commit()
c.close()
conn.close()
